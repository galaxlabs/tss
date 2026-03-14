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


def _fields():
    return [
        "inspection_log_no",
        "base_company",
        "vehicle",
        "vehicle_type",
        "inspection_date",
        "inspection_time",
        "inspector",
        "trip",
        "inspection_type",
        "status",
        "overall_result",
        "odometer_reading",
        "notes",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicle_inspection_logs(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    vehicle=None,
    inspector=None,
    trip=None,
    inspection_date=None,
    inspection_type=None,
    status=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if vehicle:
        filters["vehicle"] = vehicle
    if inspector:
        filters["inspector"] = inspector
    if trip:
        filters["trip"] = trip
    if inspection_date:
        filters["inspection_date"] = inspection_date
    if inspection_type:
        filters["inspection_type"] = inspection_type
    if status:
        filters["status"] = status

    or_filters = None
    if search:
        or_filters = [
            ["Vehicle Inspection Log", "name", "like", f"%{search}%"],
            ["Vehicle Inspection Log", "inspection_log_no", "like", f"%{search}%"],
            ["Vehicle Inspection Log", "vehicle", "like", f"%{search}%"],
            ["Vehicle Inspection Log", "inspector", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Vehicle Inspection Log",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "inspection_log_no",
            "base_company",
            "vehicle",
            "vehicle_type",
            "inspection_date",
            "inspection_time",
            "inspector",
            "trip",
            "inspection_type",
            "status",
            "overall_result",
            "odometer_reading",
        ],
        order_by="inspection_date desc, modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )
    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_vehicle_inspection_log(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Inspection Log", name)
    _check_permission(doc, "read")
    return {"data": _as_api_dict(doc)}


@frappe.whitelist(methods=["POST"])
def create_vehicle_inspection_log(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Vehicle Inspection Log", "items": data.get("items") or []}

    for fieldname in _fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()
    return {"message": "Vehicle Inspection Log created successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["PUT", "POST"])
def update_vehicle_inspection_log(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Vehicle Inspection Log", name)
    _check_permission(doc, "write")

    for fieldname in _fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "items" in data:
        doc.set("items", [])
        for row in data.get("items") or []:
            doc.append("items", row)

    doc.save()
    return {"message": "Vehicle Inspection Log updated successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle_inspection_log(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Inspection Log", name)
    _check_permission(doc, "delete")
    frappe.delete_doc("Vehicle Inspection Log", name)
    return {"message": "Vehicle Inspection Log deleted successfully."}
