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


def _trip_fields():
    return [
        "trip_status",
        "created_from_booking",
        "trip_booking",
        "base_company",
        "customer",
        "customer_name",
        "mobile_no",
        "number_of_passengers",
        "per_passenger_value",
        "currency",
        "trip_date",
        "trip_time",
        "departure",
        "arrival",
        "trip_type",
        "route",
        "from_location",
        "to_location",
        "vehicle_type",
        "assigned_vehicle",
        "assigned_driver",
        "co_driver",
        "kashf_sent",
        "is_return_trip",
        "travel_agency",
        "is_referral",
        "distance",
        "distance_unit",
        "duration_minutes",
        "avg_speed_kmph",
        "odometer_start",
        "odometer_end",
        "booking_amount",
        "trip_value",
        "driver_share",
        "company_share",
        "referral_commission_type",
        "referral_commission_value",
        "sales_invoice",
        "special_instructions",
        "remarks",
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
    assigned_vehicle=None,
    assigned_driver=None,
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
    if assigned_vehicle:
        filters["assigned_vehicle"] = assigned_vehicle
    if assigned_driver:
        filters["assigned_driver"] = assigned_driver

    or_filters = None
    if search:
        or_filters = [
            ["Trip", "name", "like", f"%{search}%"],
            ["Trip", "trip_code", "like", f"%{search}%"],
            ["Trip", "trip_title", "like", f"%{search}%"],
            ["Trip", "customer_name", "like", f"%{search}%"],
            ["Trip", "mobile_no", "like", f"%{search}%"],
            ["Trip", "route", "like", f"%{search}%"],
            ["Trip", "trip_booking", "like", f"%{search}%"],
            ["Trip", "assigned_vehicle", "like", f"%{search}%"],
        ]

    data = frappe.get_list(
        "Trip",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "trip_code",
            "trip_title",
            "trip_status",
            "base_company",
            "customer_name",
            "mobile_no",
            "trip_date",
            "route",
            "assigned_vehicle",
            "assigned_driver",
            "number_of_passengers",
            "trip_value",
            "qr_code",
        ],
        order_by="modified desc",
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
    doc_data = {
        "doctype": "Trip",
        "naming_series": data.get("naming_series") or "TRP-.YYYY.-.#####",
        "passengers": data.get("passengers") or [],
    }

    for fieldname in _trip_fields():
        doc_data[fieldname] = data.get(fieldname)

    doc = frappe.get_doc(doc_data)
    doc.insert()

    return {
        "message": "Trip created successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_trip(name, payload=None):
    _require_auth()

    data = _parse_payload(payload)
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")

    for fieldname in _trip_fields():
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))

    if "passengers" in data:
        doc.set("passengers", [])
        for row in data.get("passengers") or []:
            doc.append("passengers", row)

    doc.save()

    return {
        "message": "Trip updated successfully.",
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_trip(name):
    _require_auth()

    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "delete")

    frappe.delete_doc("Trip", name)

    return {"message": "Trip deleted successfully."}


@frappe.whitelist(methods=["POST"])
def mark_trip_confirmed(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.mark_confirmed()
    return {"message": "Trip confirmed successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def mark_trip_departed(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.mark_departed()
    return {"message": "Trip departed successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def mark_trip_arrived(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.mark_arrived()
    return {"message": "Trip arrived successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def mark_trip_completed(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.mark_completed()
    return {"message": "Trip completed successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def mark_trip_cancelled(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    doc.mark_cancelled()
    return {"message": "Trip cancelled successfully.", "data": doc.as_api_dict()}


@frappe.whitelist(methods=["POST"])
def generate_trip_qr(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    qr_code = doc.generate_qr_code()
    return {
        "message": "Trip QR generated successfully.",
        "qr_code": qr_code,
        "data": doc.as_api_dict(),
    }


@frappe.whitelist(methods=["POST"])
def pull_trip_passengers_from_booking(name):
    _require_auth()
    doc = frappe.get_doc("Trip", name)
    _check_permission(doc, "write")
    count = doc.pull_passengers_from_booking()
    return {
        "message": "Passengers pulled successfully.",
        "count": count,
        "data": doc.as_api_dict(),
    }