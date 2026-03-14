from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from tss.utils.pdf_engine import generate_pdf, save_pdf


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


def _trip_fields():
    return [
        "trip_code",
        "base_company",
        "trip_date",
        "trip_status",
        "route",
        "departure_datetime",
        "arrival_datetime",
        "actual_departure_datetime",
        "actual_arrival_datetime",
        "vehicle",
        "driver",
        "conductor",
        "pricing_rule",
        "seat_capacity",
        "available_seats",
        "notes",
    ]


@frappe.whitelist(methods=["GET"])
def list_trips(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    trip_status=None,
    trip_date=None,
    route=None,
    vehicle=None,
    driver=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if trip_status:
        filters["trip_status"] = trip_status
    if trip_date:
        filters["trip_date"] = trip_date
    if route:
        filters["route"] = route
    if vehicle:
        filters["vehicle"] = vehicle
    if driver:
        filters["driver"] = driver

    or_filters = None
    if search:
        or_filters = [
            ["Trip", "name", "like", f"%{search}%"],
            ["Trip", "trip_code", "like", f"%{search}%"],
            ["Trip", "trip_title", "like", f"%{search}%"],
            ["Trip", "route", "like", f"%{search}%"],
            ["Trip", "vehicle", "like", f"%{search}%"],
            ["Trip", "driver", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Trip",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "trip_code",
            "trip_title",
            "base_company",
            "trip_date",
            "trip_status",
            "route",
            "departure_datetime",
            "arrival_datetime",
            "vehicle",
            "driver",
            "seat_capacity",
            "available_seats",
            "pricing_rule",
            "qr_code",
        ],
        order_by="departure_datetime desc, modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_trip(name):
    _require_auth()

    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "read")
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_trip(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Trip", "trip_staff": data.get("trip_staff") or []}

    for fieldname in _trip_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()
    return {"message": "Trip created successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["PUT", "POST"])
def update_trip(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")

    for fieldname in _trip_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "trip_staff" in data:
        doc.set("trip_staff", [])
        for row in data.get("trip_staff") or []:
            doc.append("trip_staff", row)

    doc.save()
    return {"message": "Trip updated successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_trip(name):
    _require_auth()

    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "delete")
    frappe.delete_doc("Trip", name)
    return {"message": "Trip deleted successfully."}


@frappe.whitelist(methods=["POST"])
def set_trip_status(name, trip_status):
    _require_auth()

    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.trip_status = trip_status
    doc.save()
    return {"message": "Trip status updated successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def generate_trip_pdf(name, public=1):
    _require_auth()

    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "read")

    pdf_bytes = generate_pdf("Trip", doc.name, print_format="Trip Manifest")
    file_url, file_name, file_id = save_pdf(
        pdf_bytes,
        "Trip",
        doc.name,
        folder="Home/Trip PDFs",
        public=cint(public),
    )
    return {
        "message": "Trip PDF generated successfully.",
        "data": {
            "file_url": file_url,
            "file_name": file_name,
            "file_id": file_id,
        },
    }
