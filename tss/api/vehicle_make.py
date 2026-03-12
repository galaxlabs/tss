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


def _vehicle_make_fields():
    return [
        "make_name",
        "make_name_ar",
        "make_code",
        "status",
        "is_active",
        "sort_order",
        "country_of_origin",
        "website",
        "logo",
        "show_on_website",
        "website_label",
        "website_label_ar",
        "description",
        "description_ar",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_vehicle_makes(
    limit_start=0,
    limit_page_length=20,
    search=None,
    status=None,
    is_active=None,
    show_on_website=None,
):
    _require_auth()

    filters = {}
    if status:
        filters["status"] = status
    if is_active not in (None, ""):
        filters["is_active"] = cint(is_active)
    if show_on_website not in (None, ""):
        filters["show_on_website"] = cint(show_on_website)

    or_filters = None
    if search:
        or_filters = [
            ["Vehicle Make", "name", "like", f"%{search}%"],
            ["Vehicle Make", "make_name", "like", f"%{search}%"],
            ["Vehicle Make", "make_name_ar", "like", f"%{search}%"],
            ["Vehicle Make", "make_code", "like", f"%{search}%"],
            ["Vehicle Make", "country_of_origin", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Vehicle Make",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "make_name",
            "make_name_ar",
            "make_code",
            "status",
            "is_active",
            "country_of_origin",
            "show_on_website",
            "sort_order",
        ],
        order_by="sort_order asc, modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_vehicle_make(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Make", name)
    _check_permission(doc, "read")
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_vehicle_make(payload=None):
    _require_auth()

    data = _parse_payload(payload)

    doc_data = {"doctype": "Vehicle Make"}
    for fieldname in _vehicle_make_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Vehicle Make created successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_vehicle_make(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Vehicle Make", name)
    _check_permission(doc, "write")

    for fieldname in _vehicle_make_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    doc.save()

    return {
        "message": "Vehicle Make updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_vehicle_make(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Make", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Vehicle Make", name)

    return {"message": "Vehicle Make deleted successfully."}


@frappe.whitelist(methods=["POST"])
def activate_vehicle_make(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Make", name)
    _check_permission(doc, "write")
    doc.activate()

    return {
        "message": "Vehicle Make activated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def deactivate_vehicle_make(name):
    _require_auth()

    doc = frappe.get_doc("Vehicle Make", name)
    _check_permission(doc, "write")
    doc.deactivate()

    return {
        "message": "Vehicle Make deactivated successfully.",
        "data": doc.as_api_dict(),
    }