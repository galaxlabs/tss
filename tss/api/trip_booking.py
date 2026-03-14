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


def _trip_booking_fields():
    return [
        "booking_code",
        "base_company",
        "trip",
        "route",
        "booking_date",
        "booking_datetime",
        "passenger_name",
        "passenger_name_ar",
        "mobile_no",
        "alternate_mobile",
        "seat_count",
        "fare_amount",
        "payment_status",
        "booking_status",
        "source_channel",
        "pickup_point",
        "drop_point",
        "pricing_rule",
        "notes",
    ]


@frappe.whitelist(methods=["GET"])
def list_trip_bookings(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    trip=None,
    route=None,
    booking_status=None,
    payment_status=None,
    source_channel=None,
    booking_date=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if trip:
        filters["trip"] = trip
    if route:
        filters["route"] = route
    if booking_status:
        filters["booking_status"] = booking_status
    if payment_status:
        filters["payment_status"] = payment_status
    if source_channel:
        filters["source_channel"] = source_channel
    if booking_date:
        filters["booking_date"] = booking_date

    or_filters = None
    if search:
        or_filters = [
            ["Trip Booking", "name", "like", f"%{search}%"],
            ["Trip Booking", "booking_code", "like", f"%{search}%"],
            ["Trip Booking", "booking_title", "like", f"%{search}%"],
            ["Trip Booking", "passenger_name", "like", f"%{search}%"],
            ["Trip Booking", "mobile_no", "like", f"%{search}%"],
            ["Trip Booking", "trip", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Trip Booking",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "booking_code",
            "booking_title",
            "base_company",
            "trip",
            "route",
            "booking_date",
            "passenger_name",
            "mobile_no",
            "seat_count",
            "fare_amount",
            "payment_status",
            "booking_status",
            "source_channel",
            "pricing_rule",
        ],
        order_by="booking_datetime desc, modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_trip_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "read")
    return {"data": _as_api_dict(doc)}


@frappe.whitelist(methods=["POST"])
def create_trip_booking(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {"doctype": "Trip Booking", "booking_passenger": data.get("booking_passenger") or []}

    for fieldname in _trip_booking_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {"message": "Trip Booking created successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["PUT", "POST"])
def update_trip_booking(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "write")

    for fieldname in _trip_booking_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "booking_passenger" in data:
        doc.set("booking_passenger", [])
        for row in data.get("booking_passenger") or []:
            doc.append("booking_passenger", row)

    doc.save()
    return {"message": "Trip Booking updated successfully.", "data": _as_api_dict(doc)}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_trip_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "delete")
    frappe.delete_doc("Trip Booking", name)
    return {"message": "Trip Booking deleted successfully."}


@frappe.whitelist(methods=["POST"])
def set_trip_booking_status(name, booking_status):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "write")
    doc.booking_status = booking_status
    doc.save()
    return {"message": "Trip Booking status updated successfully.", "data": _as_api_dict(doc)}
