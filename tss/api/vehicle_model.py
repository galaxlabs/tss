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


def _vehicle_model_fields():
    return [
        "model_name",
        "model_name_ar",
        "model_code",
        "vehicle_make",
        "vehicle_type",
        "status",
        "model_year_from",
        "model_year_to",
        "passenger_capacity",
        "fuel_type",
        "transmission_type",
        "is_ac",
        "luggage_capacity",
        "luggage_capacity_unit",
        "image",
        "show_on_website",
        "description",
        "description_ar",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicle_models(
    limit_start=0,
    limit_page_length=20,
    search=None,
    vehicle_make=None,
    vehicle_type=None,
    status=None,
    show_on_website=None,
):
    _require_auth()

    filters = {}
    if vehicle_make:
        filters["vehicle_make"] = vehicle_make
    if vehicle_type:
        filters["vehicle_type"] = vehicle_type
    if status:
        filters["status"] = status
    if show_on_website not in (None, ""):
        filters["show_on_website"] = cint(show_on_website)

    or_filters = None
    if search:
        or_filters = [
            ["Vehicle Model", "name", "like", f"%{search}%"],
            ["Vehicle Model", "model_name", "like", f"%{search}%"],
            ["Vehicle Model", "model_name_ar", "like", f"%{search}%"],
            ["Vehicle Model", "model_code", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Vehicle Model",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "model_name",
            "model_name_ar",
            "model_code",
            "vehicle_make",
            "vehicle_type",
            "status",
            "passenger_capacity",
            "fuel_type",
            "transmission_type",
            "show_on_website",
        ],
        order_by="modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_vehicle_model(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Model", name)
    _check_permission(doc, "read")
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_vehicle_model(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Vehicle Model"}

    for fieldname in _vehicle_model_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Vehicle Model created successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_vehicle_model(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Vehicle Model", name)
    _check_permission(doc, "write")

    for fieldname in _vehicle_model_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    doc.save()

    return {
        "message": "Vehicle Model updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle_model(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Model", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Vehicle Model", name)

    return {"message": "Vehicle Model deleted successfully."}