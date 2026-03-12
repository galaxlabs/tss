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


def _vehicle_type_fields():
    return [
        "type_name",
        "type_name_ar",
        "type_code",
        "category",
        "status",
        "is_active",
        "passenger_capacity",
        "luggage_capacity",
        "luggage_capacity_unit",
        "seat_configuration",
        "default_service_unit",
        "minimum_booking_hours",
        "minimum_distance_km",
        "allow_route_pricing",
        "allow_distance_pricing",
        "allow_hourly_pricing",
        "allow_daily_pricing",
        "allow_dynamic_pricing",
        "base_fare",
        "base_currency",
        "sort_order",
        "description",
        "description_ar",
        "icon",
        "image",
        "website_label",
        "website_label_ar",
        "show_on_website",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicle_types(
    limit_start=0,
    limit_page_length=20,
    search=None,
    category=None,
    status=None,
    is_active=None,
    show_on_website=None,
):
    _require_auth()

    filters = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if is_active not in (None, ""):
        filters["is_active"] = cint(is_active)
    if show_on_website not in (None, ""):
        filters["show_on_website"] = cint(show_on_website)

    or_filters = None
    if search:
        or_filters = [
            ["Vehicle Type", "name", "like", f"%{search}%"],
            ["Vehicle Type", "type_name", "like", f"%{search}%"],
            ["Vehicle Type", "type_name_ar", "like", f"%{search}%"],
            ["Vehicle Type", "type_code", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Vehicle Type",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "type_name",
            "type_name_ar",
            "type_code",
            "category",
            "status",
            "is_active",
            "default_service_unit",
            "passenger_capacity",
            "base_fare",
            "base_currency",
            "show_on_website",
            "sort_order",
        ],
        order_by="sort_order asc, modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_vehicle_type(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "read")

    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_vehicle_type(payload=None):
    _require_auth()

    data = _parse_payload(payload)

    doc_data = {"doctype": "Vehicle Type"}
    for fieldname in _vehicle_type_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Vehicle Type created successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_vehicle_type(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "write")

    for fieldname in _vehicle_type_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    doc.save()

    return {
        "message": "Vehicle Type updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle_type(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Vehicle Type", name)

    return {
        "message": "Vehicle Type deleted successfully."
    }


@frappe.whitelist(methods=["POST"])
def set_vehicle_type_status(name, status):
    _require_auth()

    allowed = {"Draft", "Active", "Inactive"}
    if status not in allowed:
        frappe.throw(_("Invalid status."))

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "write")

    doc.status = status
    doc.save()

    return {
        "message": "Vehicle Type status updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def activate_vehicle_type(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "write")
    doc.activate()

    return {
        "message": "Vehicle Type activated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def deactivate_vehicle_type(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Type", name)
    _check_permission(doc, "write")
    doc.deactivate()

    return {
        "message": "Vehicle Type deactivated successfully.",
        "data": doc.as_api_dict(),
    }