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


def _vehicle_fields():
    return [
        "vehicle_type",
        "vehicle_make",
        "vehicle_model",
        "model_year",
        "license_plate",
        "plate_number",
        "registration_no",
        "chassis_no",
        "engine_no",
        "base_company",
        "branch",
        "assigned_driver",
        "ownership_type",
        "status",
        "is_active",
        "passenger_capacity",
        "luggage_capacity",
        "luggage_capacity_unit",
        "fuel_type",
        "transmission_type",
        "color",
        "odometer_reading",
        "odometer_unit",
        "seat_configuration",
        "purchase_date",
        "service_start_date",
        "insurance_expiry_date",
        "registration_expiry_date",
        "vehicle_image",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicles(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    branch=None,
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
    if branch:
        filters["branch"] = branch
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
            ["Vehicle", "license_plate", "like", f"%{search}%"],
            ["Vehicle", "plate_number", "like", f"%{search}%"],
            ["Vehicle", "registration_no", "like", f"%{search}%"],
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
            "vehicle_type",
            "vehicle_make",
            "vehicle_model",
            "license_plate",
            "base_company",
            "branch",
            "assigned_driver",
            "status",
            "is_active",
            "odometer_reading",
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
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_vehicle(payload=None):
    _require_auth()

    data = _parse_payload(payload)

    doc_data = {
        "doctype": "Vehicle",
        "naming_series": data.get("naming_series") or "VEH-.YYYY.-.#####",
        "documents": data.get("documents") or [],
    }

    for fieldname in _vehicle_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Vehicle created successfully.",
        "data": doc.as_api_dict(),
    }


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

    return {
        "message": "Vehicle updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Vehicle", name)

    return {"message": "Vehicle deleted successfully."}


@frappe.whitelist(methods=["POST"])
def activate_vehicle(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "write")
    doc.activate()

    return {
        "message": "Vehicle activated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def deactivate_vehicle(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle", name)
    _check_permission(doc, "write")
    doc.deactivate()

    return {
        "message": "Vehicle deactivated successfully.",
        "data": doc.as_api_dict(),
    }