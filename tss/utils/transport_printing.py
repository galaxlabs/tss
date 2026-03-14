from __future__ import annotations

import json

import frappe
from frappe.utils import format_datetime, formatdate

from tss.utils.transport_validation import build_hijri_date, build_public_url, build_qr_data_uri


def build_trip_print_context(doc) -> dict:
    company = frappe.get_cached_doc("Base Company", doc.base_company) if doc.base_company else None
    vehicle = frappe.get_cached_doc("Vehicle", doc.vehicle) if doc.vehicle else None
    route = frappe.get_cached_doc("Route", doc.route) if doc.route else None
    booking = frappe.get_cached_doc("Trip Booking", doc.trip_booking) if getattr(doc, "trip_booking", None) else None
    public_path = f"tss/trip/{doc.name}" if doc.name else None
    payload = {
        "trip": doc.name,
        "trip_code": doc.trip_code,
        "trip_status": doc.trip_status,
        "trip_date": str(doc.trip_date) if doc.trip_date else "",
        "hijri_date": doc.hijri_date or build_hijri_date(doc.trip_date),
        "vehicle": doc.vehicle,
        "route": doc.route,
        "driver": doc.driver,
        "customer_name": getattr(doc, "customer_name", ""),
        "mobile_no": getattr(doc, "mobile_no", ""),
        "passenger_count": getattr(doc, "passenger_count", 0),
    }
    return {
        "company": company,
        "vehicle": vehicle,
        "route": route,
        "booking": booking,
        "passengers": (doc.get("passengers") or []) or ((booking.get("booking_passenger") or []) if booking else []),
        "payload_json": json.dumps(payload, sort_keys=True),
        "qr_code": doc.qr_code or build_qr_data_uri(build_public_url(public_path)),
        "public_url": build_public_url(public_path),
        "trip_date_label": formatdate(doc.trip_date) if doc.trip_date else "",
        "departure_label": format_datetime(doc.departure_datetime) if doc.departure_datetime else "",
        "arrival_label": format_datetime(doc.arrival_datetime) if doc.arrival_datetime else "",
    }
