from __future__ import annotations

import json
import os
import re
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import frappe
import pymysql
from frappe.utils import cint, flt

from tss.utils.transport_validation import normalize_plate


SOURCE_SITE_PATH = "/home/dg/dg-b/sites/tms.galaxylabs.online"
DEFAULT_VEHICLE_CATEGORY = "Van"
DEFAULT_VEHICLE_TYPE = "Passenger Van"


@dataclass
class MigrationStats:
    dry_run: bool
    created: Counter = field(default_factory=Counter)
    updated: Counter = field(default_factory=Counter)
    skipped: Counter = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "created": dict(self.created),
            "updated": dict(self.updated),
            "skipped": dict(self.skipped),
            "warnings": self.warnings,
        }


def run(source_site_path: str = SOURCE_SITE_PATH, dry_run: int | bool = 1) -> dict[str, Any]:
    """Clone old TMS Route, Staff, and Vehicle records into the current TSS site.

    This function is intentionally idempotent. It uses stable legacy keys where
    possible and updates existing imported rows instead of creating duplicates.
    """

    stats = MigrationStats(dry_run=bool(cint(dry_run)))
    source = SourceDB(source_site_path)

    base_company = _get_default_base_company()
    source_routes = source.fetchall("select * from tabRoute order by creation, name")
    source_staff = source.fetchall("select * from tabStaff order by creation, name")
    source_vehicles = source.fetchall("select * from tabVehicle order by creation, name")
    source_documents = source.fetchall(
        """
        select *
        from tabDocuments
        where parenttype in ('Vehicle', 'Staff')
        order by parenttype, parent, idx, name
        """
    )

    documents_by_parent = _group_documents(source_documents)
    chassis_counts = Counter(_clean(row.get("chassis_no")) for row in source_vehicles if _clean(row.get("chassis_no")))
    used_chassis: set[str] = set()

    _ensure_vehicle_classification(stats, base_company)
    _clone_routes(stats, source_routes, base_company)
    _clone_staff(stats, source_staff, documents_by_parent, base_company)
    _clone_vehicle_masters(stats, source_vehicles, base_company)
    _clone_vehicles(stats, source_vehicles, documents_by_parent, chassis_counts, used_chassis, base_company)
    _sync_staff_vehicle_assignments(stats, source_staff)

    if not stats.dry_run:
        frappe.db.commit()

    return stats.as_dict()


def cleanup_imported_labels(dry_run: int | bool = 1) -> dict[str, Any]:
    """Remove temporary import labels from visible Route, Vehicle, and Staff data."""

    stats = MigrationStats(dry_run=bool(cint(dry_run)))
    _cleanup_imported_routes(stats)
    _cleanup_imported_vehicles(stats)
    _cleanup_imported_staff(stats)
    _cleanup_import_notes(stats)

    if not stats.dry_run:
        frappe.db.commit()

    return stats.as_dict()


def resave_vehicle(name: str) -> dict[str, Any]:
    doc = frappe.get_doc("Vehicle", name)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        "name": doc.name,
        "vehicle_code": doc.vehicle_code,
        "plate_no": doc.plate_no,
        "display_title": doc.display_title,
    }


class SourceDB:
    def __init__(self, site_path: str):
        self.site_path = site_path
        self.site_config = _read_json(os.path.join(site_path, "site_config.json"))
        self.common_config = _read_json(os.path.join(os.path.dirname(site_path), "common_site_config.json"))

    def connect(self):
        db_name = self.site_config["db_name"]
        kwargs: dict[str, Any] = {
            "user": self.site_config.get("db_user") or db_name,
            "password": self.site_config["db_password"],
            "database": db_name,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }

        socket_path = (
            self.site_config.get("db_socket")
            or self.common_config.get("db_socket")
            or self.common_config.get("mysql_socket")
        )
        if socket_path:
            kwargs["unix_socket"] = socket_path
        else:
            kwargs["host"] = self.site_config.get("db_host") or self.common_config.get("db_host") or "127.0.0.1"
            if self.site_config.get("db_port") or self.common_config.get("db_port"):
                kwargs["port"] = cint(self.site_config.get("db_port") or self.common_config.get("db_port"))

        return pymysql.connect(**kwargs)

    def fetchall(self, query: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return list(cursor.fetchall())


def _clone_routes(stats: MigrationStats, rows: list[dict[str, Any]], base_company: str) -> None:
    for row in rows:
        source = _clean(row.get("from_city"))
        destination = _clean(row.get("to_city"))
        if not source or not destination or source == destination:
            stats.skipped["Route"] += 1
            stats.warnings.append(f"Skipped route {row.get('name')}: missing or same source/destination.")
            continue

        route_code = _route_code(row)
        existing_route = _find_imported_route(row)
        values = {
            "route_code": route_code,
            "route_name": f"{source} -> {destination}",
            "source": source,
            "destination": destination,
            "route_type": "Intercity",
            "status": "Active",
            "base_company": base_company,
            "distance_km": flt(row.get("distance")),
            "estimated_duration_minutes": cint(row.get("duration_minutes")),
            "notes": _join_notes(
                f"Imported from legacy TMS Route: {row.get('name')}",
                f"Legacy duration: {_clean(row.get('duration'))}" if _clean(row.get("duration")) else "",
                f"Legacy from place: {_clean(row.get('from_place_full'))}" if _clean(row.get("from_place_full")) else "",
                f"Legacy to place: {_clean(row.get('to_place_full'))}" if _clean(row.get("to_place_full")) else "",
            ),
        }
        stops = [
            {
                "stop_name": source,
                "sequence_no": 1,
                "stop_type": "Origin",
                "distance_from_origin_km": 0,
                "estimated_offset_minutes": 0,
            },
            {
                "stop_name": destination,
                "sequence_no": 2,
                "stop_type": "Destination",
                "distance_from_origin_km": flt(row.get("distance")),
                "estimated_offset_minutes": cint(row.get("duration_minutes")),
            },
        ]
        lookup = {"name": existing_route} if existing_route else {"route_code": route_code}
        _upsert_doc(stats, "Route", lookup, values, {"route_stops": stops})


def _clone_staff(
    stats: MigrationStats,
    rows: list[dict[str, Any]],
    documents_by_parent: dict[tuple[str, str], list[dict[str, Any]]],
    base_company: str,
) -> None:
    for row in rows:
        full_name = _clean(row.get("full_name") or row.get("name1") or row.get("name"))
        if not full_name:
            stats.skipped["Staff"] += 1
            stats.warnings.append(f"Skipped staff {row.get('name')}: missing full name.")
            continue

        legacy_documents = documents_by_parent.get(("Staff", row.get("name")), [])
        driving_license = _find_complete_driving_license(legacy_documents)
        legacy_is_driver = cint(row.get("is_driver"))
        staff_id = _legacy_code("IMP-STF", row.get("name"))
        staff_type = "Driver" if legacy_is_driver and driving_license else "Operations"
        status = "Active" if cint(row.get("enabled")) or legacy_is_driver else "Draft"
        driver_note = ""
        if legacy_is_driver and not driving_license:
            driver_note = "Legacy record marked this staff as a driver, but no complete Driver Card/Driving License number and expiry was available in source."
            stats.warnings.append(f"Imported legacy driver {row.get('name')} as Operations: missing complete driving license document.")

        designation = _ensure_designation(stats, row.get("designation"))
        department = _get_existing_department(stats, row.get("department"))
        values = {
            "staff_id": staff_id,
            "full_name": full_name,
            "base_company": base_company,
            "staff_type": staff_type,
            "mobile_no": _clean(row.get("mobile_no") or row.get("phone")),
            "email": _clean(row.get("email")).lower(),
            "national_id": _clean(row.get("id_no")),
            "license_no": _clean(driving_license.get("document_no")) if driving_license else "",
            "license_expiry_date": driving_license.get("expiry_date") if driving_license else None,
            "designation_name": designation,
            "department_name": department,
            "linked_employee": _clean(row.get("employee")),
            "status": status,
            "can_login": cint(row.get("can_login")),
            "notes": _join_notes(
                f"Imported from previous Staff: {row.get('name')}",
                f"Legacy assigned vehicle: {_clean(row.get('vehicle_assigned'))}" if _clean(row.get("vehicle_assigned")) else "",
                f"Legacy nationality: {_clean(row.get('nationality'))}" if _clean(row.get("nationality")) else "",
                f"Legacy blood group: {_clean(row.get('blood_group'))}" if _clean(row.get("blood_group")) else "",
                driver_note,
            ),
        }
        child_rows = _document_rows(stats, legacy_documents, "Staff")
        _upsert_doc(stats, "Staff", {"staff_id": staff_id}, values, {"documents": child_rows})


def _clone_vehicle_masters(stats: MigrationStats, vehicle_rows: list[dict[str, Any]], base_company: str) -> None:
    for make_name in sorted({_clean(row.get("make")) for row in vehicle_rows if _clean(row.get("make"))}):
        values = {
            "make_name": make_name,
            "base_company": base_company,
            "status": "Active",
            "notes": "Imported from previous vehicle records.",
        }
        _upsert_doc(stats, "Vehicle Make", {"make_name": make_name}, values)

    for row in vehicle_rows:
        model_name = _clean(row.get("model"))
        make_name = _clean(row.get("make")) or _fallback_make(stats, base_company)
        if not model_name:
            continue
        _ensure_vehicle_make(stats, make_name, base_company)
        values = {
            "model_name": model_name,
            "vehicle_make": make_name,
            "vehicle_type": _get_default_vehicle_type(stats, base_company),
            "status": "Active",
            "fuel_type": _map_fuel_type(row.get("fuel_type")),
            "notes": f"Imported from previous vehicle record: {row.get('name')}",
        }
        _upsert_doc(stats, "Vehicle Model", {"model_name": model_name}, values)


def _clone_vehicles(
    stats: MigrationStats,
    rows: list[dict[str, Any]],
    documents_by_parent: dict[tuple[str, str], list[dict[str, Any]]],
    chassis_counts: Counter,
    used_chassis: set[str],
    base_company: str,
) -> None:
    for row in rows:
        legacy_plate = _clean(row.get("license_plate") or row.get("name"))
        plate_no = normalize_plate(legacy_plate)
        if not plate_no:
            stats.skipped["Vehicle"] += 1
            stats.warnings.append(f"Skipped vehicle {row.get('name')}: missing plate number.")
            continue

        make_name = _clean(row.get("make")) or _fallback_make(stats, base_company)
        model_name = _clean(row.get("model")) or _fallback_model(stats, make_name, base_company)
        _ensure_vehicle_make(stats, make_name, base_company)
        _ensure_vehicle_model(stats, model_name, make_name, base_company)

        chassis_no = _clean(row.get("chassis_no"))
        chassis_note = ""
        if chassis_no:
            if chassis_counts[chassis_no] > 1 or chassis_no in used_chassis or _unique_value_taken("Vehicle", "chassis_no", chassis_no, plate_no):
                chassis_note = f"Legacy chassis not set because it is duplicate in source/target: {chassis_no}"
                chassis_no = ""
            else:
                used_chassis.add(chassis_no)

        values = {
            "vehicle_code": _format_plate_for_display(plate_no),
            "plate_no": plate_no,
            "registration_no": _clean(row.get("registration_no")),
            "vehicle_name": legacy_plate,
            "base_company": base_company,
            "vehicle_model": model_name,
            "model_year": _model_year(row),
            "chassis_no": chassis_no,
            "fuel_type": _map_fuel_type(row.get("fuel_type")),
            "color": _clean(row.get("color")),
            "odometer": flt(row.get("last_odometer")),
            "status": "Active",
            "ownership_type": "Owned",
            "notes": _join_notes(
                f"Imported from previous Vehicle: {row.get('name')}",
                f"Legacy plate: {legacy_plate}",
                f"Legacy location: {_clean(row.get('location'))}" if _clean(row.get("location")) else "",
                f"Legacy vehicle value: {row.get('vehicle_value')}" if flt(row.get("vehicle_value")) else "",
                f"Legacy insurance company: {_clean(row.get('insurance_company'))}" if _clean(row.get("insurance_company")) else "",
                f"Legacy policy no: {_clean(row.get('policy_no'))}" if _clean(row.get("policy_no")) else "",
                chassis_note,
            ),
        }
        child_rows = _document_rows(stats, documents_by_parent.get(("Vehicle", row.get("name")), []), "Vehicle")
        _upsert_doc(stats, "Vehicle", {"plate_no": plate_no}, values, {"documents": child_rows})


def _sync_staff_vehicle_assignments(stats: MigrationStats, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        assigned_plate = normalize_plate(_clean(row.get("vehicle_assigned")))
        if not assigned_plate:
            continue

        staff_name = _existing_name("Staff", {"staff_id": _legacy_code("IMP-STF", row.get("name"))})
        vehicle_name = _existing_name("Vehicle", {"plate_no": assigned_plate})
        if not staff_name or not vehicle_name:
            stats.warnings.append(
                f"Could not link legacy staff vehicle assignment: staff={row.get('name')} vehicle={row.get('vehicle_assigned')}"
            )
            continue

        staff_type = frappe.db.get_value("Staff", staff_name, "staff_type")
        if staff_type != "Driver":
            stats.warnings.append(
                f"Skipped vehicle assignment for {row.get('name')}: target staff type is {staff_type}, not Driver."
            )
            continue

        if stats.dry_run:
            stats.updated["Staff Assignment"] += 1
            stats.updated["Vehicle Assignment"] += 1
            continue

        staff = frappe.get_doc("Staff", staff_name)
        if staff.assigned_vehicle != vehicle_name:
            staff.assigned_vehicle = vehicle_name
            staff.save(ignore_permissions=True)
            stats.updated["Staff Assignment"] += 1

        vehicle = frappe.get_doc("Vehicle", vehicle_name)
        if not vehicle.assigned_driver:
            vehicle.assigned_driver = staff_name
            vehicle.save(ignore_permissions=True)
            stats.updated["Vehicle Assignment"] += 1


def _upsert_doc(
    stats: MigrationStats,
    doctype: str,
    lookup: dict[str, Any],
    values: dict[str, Any],
    child_tables: dict[str, list[dict[str, Any]]] | None = None,
) -> str | None:
    existing = _existing_name(doctype, lookup)
    action = "updated" if existing else "created"
    if stats.dry_run:
        stats.created[doctype] += 0 if existing else 1
        stats.updated[doctype] += 1 if existing else 0
        return existing or values.get(next(iter(lookup), "name"))

    if existing:
        doc = frappe.get_doc(doctype, existing)
        for fieldname, value in values.items():
            if fieldname != "name":
                doc.set(fieldname, value)
        if child_tables:
            for fieldname, rows in child_tables.items():
                doc.set(fieldname, [])
                for row in rows:
                    doc.append(fieldname, row)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc(doctype)
        for fieldname, value in values.items():
            doc.set(fieldname, value)
        if child_tables:
            for fieldname, rows in child_tables.items():
                for row in rows:
                    doc.append(fieldname, row)
        doc.insert(ignore_permissions=True)

    getattr(stats, action)[doctype] += 1
    return doc.name


def _ensure_vehicle_classification(stats: MigrationStats, base_company: str) -> None:
    _upsert_doc(
        stats,
        "Vehicle Category",
        {"category_name": DEFAULT_VEHICLE_CATEGORY},
        {
            "category_name": DEFAULT_VEHICLE_CATEGORY,
            "category_code": _code(DEFAULT_VEHICLE_CATEGORY),
            "base_company": base_company,
            "status": "Active",
        },
    )
    _upsert_doc(
        stats,
        "Vehicle Type",
        {"type_name": DEFAULT_VEHICLE_TYPE},
        {
            "type_name": DEFAULT_VEHICLE_TYPE,
            "type_code": _code(DEFAULT_VEHICLE_TYPE),
            "base_company": base_company,
            "category": DEFAULT_VEHICLE_CATEGORY,
            "status": "Active",
            "default_seating_capacity": 7,
        },
    )


def _ensure_vehicle_make(stats: MigrationStats, make_name: str, base_company: str) -> str:
    _upsert_doc(
        stats,
        "Vehicle Make",
        {"make_name": make_name},
        {"make_name": make_name, "base_company": base_company, "status": "Active"},
    )
    return make_name


def _ensure_vehicle_model(stats: MigrationStats, model_name: str, make_name: str, base_company: str) -> str:
    _upsert_doc(
        stats,
        "Vehicle Model",
        {"model_name": model_name},
        {
            "model_name": model_name,
            "vehicle_make": make_name,
            "vehicle_type": _get_default_vehicle_type(stats, base_company),
            "status": "Active",
        },
    )
    return model_name


def _document_rows(stats: MigrationStats, rows: list[dict[str, Any]], entity_kind: str) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for row in rows:
        document_type = _map_document_type(row.get("document_type"), entity_kind)
        if not document_type:
            continue
        _ensure_document_type(stats, document_type, entity_kind, bool(row.get("expiry_date")))
        key = (document_type, _clean(row.get("document_no")))
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "document_type": document_type,
                "document_no": _clean(row.get("document_no")),
                "issue_date": row.get("issue_date"),
                "expiry_date": row.get("expiry_date"),
                "status": _map_document_status(row.get("status")),
                "notes": f"Imported from previous document row: {row.get('name')}",
            }
        )
    return result


def _find_complete_driving_license(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        document_type = _map_document_type(row.get("document_type"), "Staff")
        if document_type != "Driving License":
            continue
        if _clean(row.get("document_no")) and row.get("expiry_date"):
            return row
    return None


def _map_document_type(value: Any, entity_kind: str) -> str:
    document_type = _clean(value)
    if entity_kind == "Staff":
        aliases = {
            "Driver Card": "Driving License",
            "Driver License": "Driving License",
            "Driving License No": "Driving License",
            "Iqama No": "Iqama",
            "ID No": "National ID",
        }
        return aliases.get(document_type, document_type)
    return document_type


def _ensure_document_type(stats: MigrationStats, document_type: str, entity_kind: str, has_expiry: bool) -> None:
    _upsert_doc(
        stats,
        "Document Type",
        {"document_type_name": document_type},
        {
            "document_type_name": document_type,
            "entity_kind": entity_kind if entity_kind in {"Base Company", "Staff", "Vehicle", "Trip"} else "Other",
            "has_expiry": 1 if has_expiry else 0,
            "requires_attachment": 0,
            "requires_document_number": 0,
            "is_active": 1,
            "notes": "Imported from previous child document rows.",
        },
    )


def _ensure_designation(stats: MigrationStats, value: Any) -> str:
    designation = _clean(value)
    if not designation or not frappe.db.exists("DocType", "Designation"):
        return ""
    _upsert_doc(
        stats,
        "Designation",
        {"designation_name": designation},
        {
            "designation_name": designation,
            "description": "Imported from previous Staff records.",
        },
    )
    return designation


def _get_existing_department(stats: MigrationStats, value: Any) -> str:
    department = _clean(value)
    if not department or not frappe.db.exists("DocType", "Department"):
        return ""
    if frappe.db.exists("Department", department):
        return department
    stats.warnings.append(f"Skipped missing Department link for legacy staff import: {department}")
    return ""


def _get_default_base_company() -> str:
    company = frappe.db.get_value("Base Company", {"status": "Active"}, "name", order_by="creation asc")
    company = company or frappe.db.get_value("Base Company", {}, "name", order_by="creation asc")
    if not company:
        frappe.throw("No Base Company exists in target site.")
    return company


def _get_default_vehicle_type(stats: MigrationStats, base_company: str) -> str:
    _ensure_vehicle_classification(stats, base_company)
    return DEFAULT_VEHICLE_TYPE


def _fallback_make(stats: MigrationStats, base_company: str) -> str:
    make_name = "Legacy Unknown"
    _ensure_vehicle_make(stats, make_name, base_company)
    return make_name


def _fallback_model(stats: MigrationStats, make_name: str, base_company: str) -> str:
    model_name = "Legacy Unknown"
    _ensure_vehicle_model(stats, model_name, make_name, base_company)
    return model_name


def _existing_name(doctype: str, lookup: dict[str, Any]) -> str | None:
    return frappe.db.get_value(doctype, lookup, "name")


def _unique_value_taken(doctype: str, fieldname: str, value: str, plate_no: str) -> bool:
    existing = frappe.db.get_value(doctype, {fieldname: value}, ["name", "plate_no"], as_dict=True)
    return bool(existing and existing.get("plate_no") != plate_no)


def _group_documents(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row.get("parenttype"), row.get("parent")), []).append(row)
    return grouped


def _read_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _code(value: str) -> str:
    return (re.sub(r"[^A-Za-z0-9]", "", value).upper() or "LEGACY")[:20]


def _legacy_code(prefix: str, value: Any) -> str:
    return f"{prefix}-{_code(_clean(value))}"[:140]


def _route_code(row: dict[str, Any]) -> str:
    base = f"{_city_code(row.get('from_city'))}-TO-{_city_code(row.get('to_city'))}"
    return _unique_field_value("Route", "route_code", base, "")


def _find_imported_route(row: dict[str, Any]) -> str | None:
    source_name = _clean(row.get("name"))
    if not source_name:
        return None
    return frappe.db.get_value(
        "Route",
        {
            "notes": [
                "like",
                f"%{source_name}%",
            ]
        },
        "name",
    )


def _cleanup_imported_routes(stats: MigrationStats) -> None:
    routes = frappe.get_all(
        "Route",
        or_filters=[
            ["Route", "route_code", "like", "TMS-RTE-%"],
            ["Route", "route_code", "like", "IMP-RTE-%"],
            ["Route", "notes", "like", "%legacy TMS Route%"],
            ["Route", "notes", "like", "%previous Route%"],
        ],
        pluck="name",
    )

    for name in routes:
        doc = frappe.get_doc("Route", name)
        new_code = _unique_route_code_for_cleanup(doc.source, doc.destination, doc.name)
        if stats.dry_run:
            stats.updated["Route"] += 1
            continue

        doc.route_code = new_code
        doc.route_name = f"{doc.source} - {doc.destination}"
        doc.notes = _clean_import_note(doc.notes)
        doc.save(ignore_permissions=True)
        if doc.name != new_code and not frappe.db.exists("Route", new_code):
            frappe.rename_doc("Route", doc.name, new_code, force=True)


def _cleanup_imported_vehicles(stats: MigrationStats) -> None:
    vehicles = frappe.get_all(
        "Vehicle",
        or_filters=[
            ["Vehicle", "vehicle_code", "like", "TMS-VEH-%"],
            ["Vehicle", "vehicle_code", "like", "IMP-VEH-%"],
            ["Vehicle", "notes", "like", "%legacy TMS Vehicle%"],
            ["Vehicle", "notes", "like", "%previous Vehicle%"],
        ],
        pluck="name",
    )

    for name in vehicles:
        doc = frappe.get_doc("Vehicle", name)
        plate_no = _format_plate_for_display(doc.plate_no or doc.vehicle_code or doc.name)
        new_name = _unique_docname("Vehicle", plate_no, doc.name)
        if stats.dry_run:
            stats.updated["Vehicle"] += 1
            continue

        doc.plate_no = plate_no
        doc.vehicle_code = new_name
        doc.vehicle_name = doc.vehicle_name or plate_no
        doc.notes = _clean_import_note(doc.notes)
        doc.save(ignore_permissions=True)
        if doc.name != new_name and not frappe.db.exists("Vehicle", new_name):
            frappe.rename_doc("Vehicle", doc.name, new_name, force=True)


def _cleanup_imported_staff(stats: MigrationStats) -> None:
    staff_records = frappe.get_all(
        "Staff",
        or_filters=[
            ["Staff", "staff_id", "like", "TMS-STF-%"],
            ["Staff", "staff_id", "like", "IMP-STF-%"],
            ["Staff", "notes", "like", "%legacy TMS Staff%"],
            ["Staff", "notes", "like", "%previous Staff%"],
        ],
        pluck="name",
    )

    for name in staff_records:
        doc = frappe.get_doc("Staff", name)
        new_staff_id = _legacy_code("IMP-STF", doc.full_name or doc.name)
        if stats.dry_run:
            stats.updated["Staff"] += 1
            continue

        doc.staff_id = _unique_field_value("Staff", "staff_id", new_staff_id, doc.name)
        doc.notes = _clean_import_note(doc.notes)
        doc.save(ignore_permissions=True)


def _cleanup_import_notes(stats: MigrationStats) -> None:
    updates = [
        ("Entity Document", "notes"),
        ("Vehicle Make", "notes"),
        ("Vehicle Model", "notes"),
        ("Vehicle Category", "notes"),
        ("Vehicle Type", "notes"),
        ("Document Type", "notes"),
        ("Designation", "description"),
    ]

    for doctype, fieldname in updates:
        if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(fieldname):
            continue
        names = frappe.get_all(doctype, filters=[[doctype, fieldname, "like", "%TMS%"]], pluck="name")
        for name in names:
            if stats.dry_run:
                stats.updated[f"{doctype}.{fieldname}"] += 1
                continue
            value = frappe.db.get_value(doctype, name, fieldname)
            frappe.db.set_value(doctype, name, fieldname, _clean_import_note(value), update_modified=False)


def _format_plate_for_display(value: Any) -> str:
    plate = re.sub(r"^(TMS|IMP)-VEH-", "", _clean(value).upper())
    plate = re.sub(r"[^A-Z0-9]+", " ", plate).strip()
    if " " not in plate:
        plate = re.sub(r"^([0-9]+)([A-Z]+)$", r"\1 \2", plate)
        plate = re.sub(r"^([A-Z]+)([0-9]+)$", r"\1 \2", plate)
    return _clean(plate)


def _unique_route_code_for_cleanup(source: str, destination: str, current_name: str) -> str:
    base = f"{_city_code(source)}-TO-{_city_code(destination)}"
    return _unique_field_value("Route", "route_code", base, current_name)


def _city_code(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9 ]", " ", _clean(value))
    words = [word.upper() for word in text.split() if word]
    if not words:
        return "UNK"

    for word in words:
        if len(word) >= 3 and word not in {"THE", "BIN", "AL"}:
            return word[:3]

    joined = "".join(words)
    return (joined + "XXX")[:3]


def _unique_docname(doctype: str, base: str, current_name: str) -> str:
    return _unique_name(base, lambda candidate: frappe.db.exists(doctype, candidate), current_name)


def _unique_field_value(doctype: str, fieldname: str, base: str, current_name: str) -> str:
    def exists(candidate: str) -> str | None:
        return frappe.db.get_value(doctype, {fieldname: candidate}, "name")

    return _unique_name(base, exists, current_name)


def _unique_name(base: str, exists, current_name: str) -> str:
    candidate = base[:140]
    counter = 2
    while True:
        existing = exists(candidate)
        if not existing or existing == current_name:
            return candidate
        suffix = f"-{counter}"
        candidate = f"{base[: 140 - len(suffix)]}{suffix}"
        counter += 1


def _clean_import_note(value: Any) -> str:
    text = _clean(str(value or ""))
    replacements = {
        "Imported from legacy TMS Route": "Imported from previous Route",
        "Imported from legacy TMS Staff": "Imported from previous Staff",
        "Imported from legacy TMS Vehicle": "Imported from previous Vehicle",
        "Imported from legacy TMS vehicle record": "Imported from previous vehicle record",
        "Imported from legacy TMS vehicle records": "Imported from previous vehicle records",
        "Imported from legacy TMS document row": "Imported from previous document row",
        "Imported from legacy TMS child document rows": "Imported from previous child document rows",
        "Imported from legacy TMS Staff records": "Imported from previous Staff records",
        "legacy TMS": "previous",
        "Legacy TMS": "Previous",
        "TMS": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return _clean(text)


def _join_notes(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


def _map_fuel_type(value: Any) -> str:
    fuel_type = _clean(value).title()
    return fuel_type if fuel_type in {"Petrol", "Diesel", "Hybrid", "Electric", "Other"} else "Other"


def _map_document_status(value: Any) -> str:
    status = _clean(value).title()
    return status if status in {"Valid", "Expiring Soon", "Expired", "Pending"} else "Pending"


def _model_year(row: dict[str, Any]) -> int:
    value = _clean(row.get("model_year"))
    return cint(value) if value.isdigit() else 0
