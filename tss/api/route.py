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


def _route_fields():
    return [
        "base_company",
        "route_name",
        "route_name_ar",
        "route_code",
        "source",
        "destination",
        "route_type",
        "distance_km",
        "estimated_duration_minutes",
        "default_vehicle_type",
        "status",
        "is_active",
        "notes",
    ]


@frappe.whitelist(methods=["GET"])
def list_routes(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    source=None,
    destination=None,
    route_type=None,
    status=None,
    is_active=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if source:
        filters["source"] = source
    if destination:
        filters["destination"] = destination
    if route_type:
        filters["route_type"] = route_type
    if status:
        filters["status"] = status
    if is_active not in (None, ""):
        filters["is_active"] = cint(is_active)

    or_filters = None
    if search:
        or_filters = [
            ["Route", "name", "like", f"%{search}%"],
            ["Route", "route_code", "like", f"%{search}%"],
            ["Route", "route_name", "like", f"%{search}%"],
            ["Route", "source", "like", f"%{search}%"],
            ["Route", "destination", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Route",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "route_code",
            "route_name",
            "base_company",
            "source",
            "destination",
            "route_type",
            "distance_km",
            "estimated_duration_minutes",
            "status",
            "is_active",
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
    return {"data": _as_api_dict(doc)}


@frappe.whitelist(methods=["POST"])
def create_route(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Route", "route_stops": data.get("route_stops") or []}

    for fieldname in _route_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {"message": "Route created successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["PUT", "POST"])
def update_route(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")

    for fieldname in _route_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "route_stops" in data:
        doc.set("route_stops", [])
        for row in data.get("route_stops") or []:
            doc.append("route_stops", row)

    doc.save()
    return {"message": "Route updated successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_route(name):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "delete")
    frappe.delete_doc("Route", name)
    return {"message": "Route deleted successfully."}


@frappe.whitelist(methods=["POST"])
def set_route_status(name, status):
    _require_auth()

    doc = frappe.get_doc("Route", name)
    _check_permission(doc, "write")
    doc.status = status
    doc.save()
    return {"message": "Route status updated successfully.", "data": _as_api_dict(doc)}
