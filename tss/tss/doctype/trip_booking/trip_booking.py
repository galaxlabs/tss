from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime, nowdate

from tss.utils.transport_naming import clean_long_text, clean_text, make_code
from tss.utils.transport_validation import ensure_positive, ensure_same_company, validate_child_row_uniqueness


class TripBooking(Document):
    def before_insert(self):
        if not self.booking_code:
            self.booking_code = make_code(self.doctype)

    def validate(self):
        self.passenger_name = clean_text(self.passenger_name)
        self.passenger_name_ar = clean_text(self.passenger_name_ar)
        self.mobile_no = clean_text(self.mobile_no)
        self.alternate_mobile = clean_text(self.alternate_mobile)
        self.notes = clean_long_text(self.notes)
        self.booking_date = self.booking_date or nowdate()
        self.booking_datetime = self.booking_datetime or now_datetime()
        self.booking_status = clean_text(self.booking_status or "Draft")
        self.payment_status = clean_text(self.payment_status or "Unpaid")
        self.source_channel = clean_text(self.source_channel or "Desk")

        self.validate_required_fields()
        self.sync_passengers()
        self.validate_trip()
        if self.trip:
            self.validate_seat_availability()
        ensure_positive(self.fare_amount, "Fare Amount")
        self.booking_title = " - ".join(str(value) for value in [self.passenger_name, self.trip, self.booking_date] if value)

    def validate_required_fields(self):
        for label, value in {
            "Base Company": self.base_company,
            "Passenger Name": self.passenger_name,
            "Route": self.route,
        }.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))

    def sync_passengers(self):
        rows = self.get("booking_passenger") or []
        validate_child_row_uniqueness(rows, lambda row: (clean_text(row.document_number),), "booking passenger document")
        validate_child_row_uniqueness(rows, lambda row: (clean_text(row.seat_no),), "booking passenger seat")
        for row in rows:
            row.passenger_name = clean_text(row.passenger_name)
            row.passenger_name_ar = clean_text(row.passenger_name_ar)
            row.document_number = clean_text(row.document_number)
            row.mobile_no = clean_text(row.mobile_no)
            row.notes = clean_long_text(row.notes)
        self.seat_count = cint(self.seat_count or len(rows) or 1)

    def validate_trip(self):
        if not self.trip:
            return
        ensure_same_company(self.base_company, "Trip", self.trip)
        trip = frappe.get_doc("Trip", self.trip)
        self.route = trip.route
        self.pricing_rule = self.pricing_rule or trip.pricing_rule
        if trip.trip_status not in ("Scheduled", "Open", "In Progress", "Draft"):
            frappe.throw(_("Trip is not available for booking."))

    def validate_seat_availability(self):
        trip = frappe.get_doc("Trip", self.trip)
        booked = frappe.db.sql(
            """
            select ifnull(sum(seat_count), 0)
            from `tabTrip Booking`
            where trip=%s and name!=%s and booking_status not in ('Cancelled', 'Closed')
            """,
            (self.trip, self.name),
        )[0][0]
        available = cint(trip.seat_capacity or 0) - cint(booked or 0)
        if cint(self.seat_count) > available:
            frappe.throw(_("Seat count exceeds available seats."))

    def on_update(self):
        if self.trip and frappe.db.exists("Trip", self.trip):
            frappe.db.set_value("Trip", self.trip, "trip_booking", self.name, update_modified=False)


@frappe.whitelist()
def create_trip_from_booking(booking_name: str) -> str:
    booking = frappe.get_doc("Trip Booking", booking_name)
    booking.check_permission("read")
    if booking.trip:
        return booking.trip

    trip = frappe.get_doc(
        {
            "doctype": "Trip",
            "base_company": booking.base_company,
            "trip_booking": booking.name,
            "route": booking.route,
            "pricing_rule": booking.pricing_rule,
            "customer_name": booking.passenger_name,
            "mobile_no": booking.mobile_no,
            "passenger_count": cint(booking.seat_count or len(booking.get("booking_passenger") or []) or 1),
            "trip_status": "Draft",
            "notes": booking.notes,
        }
    )
    trip.insert()
    frappe.db.set_value("Trip Booking", booking.name, "trip", trip.name, update_modified=False)
    return trip.name
