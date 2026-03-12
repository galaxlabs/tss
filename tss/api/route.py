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


def _route_fields():
    return [
        "route_code",
        "status",
        "is_active",
        "base_company",
        "is_system_generated",
        "from_city",
        "from_city_code",
        "from_place_full",
        "to_city",
        "to_city_code",
        "to_place_full",
        "distance",
        "distance_unit",
        "duration_minutes",
        "avg_speed_kmph",
        "distance_source",
        "has_return",
        "return_route",
        "allow_dynamic_pricing",
        "show_on_website",
        "description",
        "description_ar",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_routes(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    from_city=None,
    to_city=None,
    status=None,
    is_active=None,
    show_on_website=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if from_city:
        filters["from_city"] = from_city
    if to_city:
        filters["to_city"] = to_city
    if status:
        filters["status"] = status
    if is_active not in (None, ""):
        filters["is_active"] = cint(is_active)
    if show_on_website not in (None, ""):
        filters["show_on_website"] = cint(show_on_website)

    or_filters = None
    if search:
        or_filters = [
            ["Route", "name", "like", f"%{search}%"],
            ["Route", "route_code", "like", f"%{search}%"],
            ["Route", "route_title", "like", f"%{search}%"],
            ["Route", "from_city", "like", f"%{search}%"],
            ["Route", "to_city", "like", f"%{search}%"],
            ["Route", "from_place_full", "like", f"%{search}%"],
            ["Route", "to_place_full", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Route",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "route_code",
            "route_title",
            "base_company",
            "from_city",
            "to_city",
            "distance",
            "duration_minutes",
            "status",
            "is_active",
            "has_return",
            "return_route",
            "show_on_website",
        ],
        order_by="modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_route(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "read")
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_route(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Route"}

    for fieldname in _route_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Route created successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_route(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")

    for fieldname in _route_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    doc.save()

    return {
        "message": "Route updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_route(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Route", name)

    return {"message": "Route deleted successfully."}


@frappe.whitelist(methods=["POST"])
def activate_route(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")
    doc.activate()

    return {
        "message": "Route activated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def deactivate_route(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")
    doc.deactivate()

    return {
        "message": "Route deactivated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def fetch_route_distance(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")

    result = doc.fetch_distance_and_update()

    return {
        "message": "Route distance updated successfully.",
        "result": result,
        "data": doc.as_api_dict(),
    }