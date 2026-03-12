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


def _trip_booking_fields():
    return [
        "status",
        "booking_source",
        "reference_no",
        "base_company",
        "branch",
        "booking_date",
        "customer_name",
        "customer_name_ar",
        "mobile_no",
        "email",
        "nationality",
        "number_of_passengers",
        "trip_date",
        "trip_time",
        "trip_type",
        "route",
        "pickup_location",
        "dropoff_location",
        "pickup_city",
        "dropoff_city",
        "vehicle_type",
        "vehicle",
        "assigned_driver",
        "currency",
        "estimated_amount",
        "final_amount",
        "pricing_status",
        "created_by_staff",
        "special_instructions",
        "remarks",
    ]


@frappe.whitelist(methods=["GET"])
def list_trip_bookings(
    limit_start=0,
    limit_page_length=20,
    search=None,
    base_company=None,
    branch=None,
    status=None,
    booking_source=None,
    trip_date=None,
    route=None,
    vehicle_type=None,
    created_by_staff=None,
):
    _require_auth()

    filters = {}
    if base_company:
        filters["base_company"] = base_company
    if branch:
        filters["branch"] = branch
    if status:
        filters["status"] = status
    if booking_source:
        filters["booking_source"] = booking_source
    if trip_date:
        filters["trip_date"] = trip_date
    if route:
        filters["route"] = route
    if vehicle_type:
        filters["vehicle_type"] = vehicle_type
    if created_by_staff:
        filters["created_by_staff"] = created_by_staff

    or_filters = None
    if search:
        or_filters = [
            ["Trip Booking", "name", "like", f"%{search}%"],
            ["Trip Booking", "booking_code", "like", f"%{search}%"],
            ["Trip Booking", "booking_title", "like", f"%{search}%"],
            ["Trip Booking", "customer_name", "like", f"%{search}%"],
            ["Trip Booking", "mobile_no", "like", f"%{search}%"],
            ["Trip Booking", "reference_no", "like", f"%{search}%"],
            ["Trip Booking", "pickup_location", "like", f"%{search}%"],
            ["Trip Booking", "dropoff_location", "like", f"%{search}%"],
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
            "branch",
            "status",
            "booking_source",
            "customer_name",
            "mobile_no",
            "trip_date",
            "route",
            "vehicle_type",
            "vehicle",
            "assigned_driver",
            "number_of_passengers",
            "estimated_amount",
            "final_amount",
            "trip",
        ],
        order_by="modified desc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length),
    )

    return {"data": data}


@frappe.whitelist(methods=["GET"])
def get_trip_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "read")
    return {"data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def create_trip_booking(payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc_data = {
        "doctype": "Trip Booking",
        "naming_series": data.get("naming_series") or "TBK-.YYYY.-.#####",
        "booking_passenger": data.get("booking_passenger") or [],
    }

    for fieldname in _trip_booking_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Trip Booking created successfully.",
        "data": doc.as_api_dict(),
    }


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

    return {
        "message": "Trip Booking updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_trip_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Trip Booking", name)

    return {"message": "Trip Booking deleted successfully."}


@frappe.whitelist(methods=["POST"])
def confirm_trip_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "write")

    result = doc.confirm_booking()

    return {
        "message": "Trip Booking confirmed successfully.",
        "result": result,
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def create_trip_from_booking(name):
    _require_auth()

    doc = frappe.get_doc("Trip Booking", name)
    _check_permission(doc, "write")

    trip = doc.create_trip()

    return {
        "message": "Trip created successfully.",
        "trip": trip,
        "data": doc.as_api_dict(),
    }