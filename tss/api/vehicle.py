from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


def _require_auth():
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required."), frappe.PermissionError)


def _check_permission(doc, ptype="read"):
    if not doc.has_permission(ptype):
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _parse_payload(payload=None):
    if payload:
        return frappe.parse_json(payload)
    return frappe.local.form_dict


def _as_api_dict(doc):
    return doc.as_api_dict() if hasattr(doc, "as_api_dict") else doc.as_dict()


def _vehicle_fields():
    return [
        "vehicle_code",
        "base_company",
        "vehicle_type",
        "vehicle_make",
        "vehicle_model",
        "vehicle_category",
        "model_year",
        "plate_no",
        "plate_no_ar",
        "chassis_no",
        "engine_no",
        "color",
        "seat_capacity",
        "status",
        "is_active",
        "assigned_driver",
        "ownership_type",
        "fuel_type",
        "odometer",
        "default_route",
        "notes",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicles(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    vehicle_type=None,
    vehicle_make=None,
    vehicle_model=None,
    assigned_driver=None,
    status=None,
    is_active=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if vehicle_type:
        filters["vehicle_type"] = vehicle_type
    if vehicle_make:
        filters["vehicle_make"] = vehicle_make
    if vehicle_model:
        filters["vehicle_model"] = vehicle_model
    if assigned_driver:
        filters["assigned_driver"] = assigned_driver
    if status:
        filters["status"] = status
    if is_active not in (None, ""):
        filters["is_active"] = cint(is_active)

    or_filters = None
    if search:
        or_filters = [
            ["Vehicle", "name", "like", f"%{search}%"],
            ["Vehicle", "vehicle_code", "like", f"%{search}%"],
            ["Vehicle", "display_title", "like", f"%{search}%"],
            ["Vehicle", "plate_no", "like", f"%{search}%"],
            ["Vehicle", "chassis_no", "like", f"%{search}%"],
            ["Vehicle", "engine_no", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Vehicle",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "vehicle_code",
            "display_title",
            "base_company",
            "vehicle_type",
            "vehicle_make",
            "vehicle_model",
            "plate_no",
            "assigned_driver",
            "seat_capacity",
            "status",
            "is_active",
            "odometer",
        ],
        order_by="modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_vehicle(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "read")
    return {"data": _as_api_dict(doc)}


@frappe.whitelist(methods=["POST"])
def create_vehicle(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Vehicle", "documents": data.get("documents") or []}

    for fieldname in _vehicle_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()
    return {"message": "Vehicle created successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["PUT", "POST"])
def update_vehicle(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "write")

    for fieldname in _vehicle_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "documents" in data:
        doc.set("documents", [])
        for row in data.get("documents") or []:
            doc.append("documents", row)

    doc.save()
    return {"message": "Vehicle updated successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "delete")
    frappe.delete_doc("Vehicle", name)
    return {"message": "Vehicle deleted successfully."}


@frappe.whitelist(methods=["POST"])
def set_vehicle_status(name, status):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "write")
    doc.status = status
    doc.save()
    return {"message": "Vehicle status updated successfully.", "data": _as_api_dict(doc)}
