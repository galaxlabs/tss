from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cint, flt, get_datetime, now_datetime, nowdate

from tss.utils.transport_naming import clean_long_text, clean_text, make_trip_code
from tss.tss.doctype.route.route import get_or_create_reverse_route_name
from tss.utils.transport_printing import build_trip_print_context
from tss.utils.transport_validation import (
    build_hijri_date,
    build_public_url,
    build_qr_data_uri,
    ensure_same_company,
    save_qr_image_file,
    ensure_staff_is_driver,
    ensure_staff_same_company,
    validate_child_row_uniqueness,
    validate_datetime_order,
)


class Trip(Document):
    def before_insert(self):
        self._set_if_present("trip_date", self._value("trip_date") or nowdate())
        self._set_if_present("trip_code", self._value("trip_code") or make_trip_code(self._value("trip_date")))
        self.apply_default_schedule()

    def validate(self):
        self._map_legacy_fields()
        self._set_if_present("notes", clean_long_text(self._value("notes")))
        self._set_if_present("trip_status", clean_text(self._value("trip_status") or "Draft"))
        self._set_if_present("customer_name", clean_text(self._value("customer_name")))
        self._set_if_present("mobile_no", clean_text(self._value("mobile_no")))
        self.sync_from_booking()
        self.sync_driver_vehicle()
        self.apply_default_schedule()
        self.sync_route_snapshot()
        self.sync_passengers()
        self.validate_required_fields()
        self.validate_dates()
        self.validate_links()
        self.validate_direction_sequence()
        self.validate_staff_rows()
        self.sync_capacity()
        self._set_if_present("hijri_date", build_hijri_date(self._value("trip_date")))
        self._set_if_present(
            "trip_title",
            " | ".join(str(value) for value in [self._value("trip_code"), self._value("trip_date")] if value),
        )
        self.build_qr_payload()

    def validate_required_fields(self):
        for label, value in {
            "Base Company": self._value("base_company"),
            "Trip Date": self._value("trip_date"),
        }.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))
        if self._value("trip_status") in ("Scheduled", "Open", "In Progress", "Completed", "Closed"):
            for label, value in {
                "Route": self._value("route"),
                "Departure Datetime": self._value("departure_datetime"),
                "Vehicle": self._value("vehicle"),
                "Driver": self._value("driver"),
            }.items():
                if not value:
                    frappe.throw(_("{0} is required when Trip Status is {1}.").format(label, self._value("trip_status")))

    def sync_from_booking(self):
        if not self._value("trip_booking"):
            return

        booking = frappe.get_doc("Trip Booking", self._value("trip_booking"))
        if self._value("base_company") and booking.base_company and booking.base_company != self._value("base_company"):
            frappe.throw(_("Trip Booking must belong to the same Base Company."))
        if booking.trip and booking.trip != self.name:
            frappe.throw(_("Trip Booking {0} is already linked to Trip {1}.").format(booking.name, booking.trip))

        self._set_if_present("base_company", booking.base_company)
        self._set_if_present("route", booking.route or self._value("route"))
        self._set_if_present("pricing_rule", booking.pricing_rule or self._value("pricing_rule"))
        self._set_if_present("customer_name", booking.passenger_name or self._value("customer_name"))
        self._set_if_present("mobile_no", booking.mobile_no or self._value("mobile_no"))
        booking_passengers = booking.get("booking_passenger") or []
        self._set_if_present("passenger_count", cint(booking.seat_count or len(booking_passengers) or 1))
        self._set_if_present("number_of_passengers", cint(booking.seat_count or len(booking_passengers) or 1))
        if self.meta.has_field("passengers") and not (self.get("passengers") or []):
            self.set("passengers", [])
            for row in booking_passengers:
                self.append(
                    "passengers",
                    {
                        "passenger_name": row.passenger_name,
                        "passenger_name_ar": row.passenger_name_ar,
                        "nationality": row.nationality,
                        "document_type": row.document_type,
                        "document_number": row.document_number,
                        "mobile_no": row.mobile_no,
                        "seat_no": row.seat_no,
                        "source": "Booking",
                        "expiry_date": row.expiry_date,
                        "notes": row.notes,
                    },
                )

    def sync_driver_vehicle(self):
        driver = self._value("driver")
        if not driver:
            return

        ensure_staff_is_driver(driver, self._value("base_company"))
        assigned_vehicle = frappe.db.get_value("Staff", driver, "assigned_vehicle")
        if assigned_vehicle and not self._value("vehicle"):
            self._set_if_present("vehicle", assigned_vehicle)
            self._set_if_present("assigned_vehicle", assigned_vehicle)
        elif not self._value("vehicle"):
            vehicle = frappe.db.get_value("Vehicle", {"assigned_driver": driver, "status": "Active"})
            self._set_if_present("vehicle", vehicle)
            self._set_if_present("assigned_vehicle", vehicle)
        if self._value("vehicle") and not self._value("route"):
            self._set_if_present("route", frappe.db.get_value("Vehicle", self._value("vehicle"), "default_route"))

    def apply_default_schedule(self):
        default_departure = self._value("departure_datetime") or now_datetime()
        self._set_if_present("departure_datetime", default_departure)
        route = self._value("route")
        minutes = cint(frappe.db.get_value("Route", route, "estimated_duration_minutes")) if route else 0
        computed_arrival = add_to_date(default_departure, minutes=minutes or 0, as_datetime=True)
        if get_datetime(computed_arrival) < get_datetime(default_departure):
            computed_arrival = default_departure
        self._set_if_present("arrival_datetime", computed_arrival)

    def validate_dates(self):
        self.normalize_schedule_window()
        validate_datetime_order(self._value("departure_datetime"), self._value("arrival_datetime"), "Departure Datetime", "Arrival Datetime")
        validate_datetime_order(
            self._value("actual_departure_datetime"),
            self._value("actual_arrival_datetime"),
            "Actual Departure Datetime",
            "Actual Arrival Datetime",
        )
        if flt(self._value("seat_capacity")) < 0 or flt(self._value("available_seats")) < 0:
            frappe.throw(_("Seat values cannot be negative."))

    def normalize_schedule_window(self):
        departure = self._value("departure_datetime")
        arrival = self._value("arrival_datetime")
        if not departure:
            return
        if not arrival:
            self.apply_default_schedule()
            return
        if get_datetime(arrival) >= get_datetime(departure):
            return

        route = self._value("route")
        minutes = cint(frappe.db.get_value("Route", route, "estimated_duration_minutes")) if route else 0
        corrected_arrival = add_to_date(departure, minutes=minutes or 0, as_datetime=True)
        if get_datetime(corrected_arrival) < get_datetime(departure):
            corrected_arrival = departure
        self._set_if_present("arrival_datetime", corrected_arrival)

    def validate_links(self):
        if self._value("vehicle"):
            ensure_same_company(self._value("base_company"), "Vehicle", self._value("vehicle"))
        if self._value("driver"):
            ensure_staff_is_driver(self._value("driver"), self._value("base_company"))
        if self._value("conductor"):
            ensure_staff_same_company(self._value("conductor"), self._value("base_company"))
        if self._value("co_driver"):
            ensure_staff_is_driver(self._value("co_driver"), self._value("base_company"))
            if self._value("co_driver") == self._value("driver"):
                frappe.throw(_("Co Driver cannot be the same as Driver."))
        if self._value("pricing_rule"):
            ensure_same_company(self._value("base_company"), "Trip Pricing Rule", self._value("pricing_rule"))

        if self._value("vehicle"):
            vehicle_doc = frappe.get_doc("Vehicle", self._value("vehicle"))
            if not cint(vehicle_doc.is_active):
                frappe.throw(_("Vehicle must be active."))
            if self._value("driver") and vehicle_doc.assigned_driver and vehicle_doc.assigned_driver != self._value("driver"):
                frappe.throw(_("Selected vehicle is assigned to a different driver."))
            if not self._value("seat_capacity"):
                self._set_if_present("seat_capacity", cint(vehicle_doc.seat_capacity or 0))

        rows = frappe.get_all(
            "Trip",
            filters={
                "name": ["!=", self.name],
                "base_company": self._value("base_company"),
                "trip_status": ["in", ["Scheduled", "Open", "In Progress"]],
            },
            fields=["name", "vehicle", "driver", "co_driver", "departure_datetime", "arrival_datetime"],
        )
        current_start = get_datetime(self._value("departure_datetime"))
        current_end = get_datetime(self._value("arrival_datetime") or self._value("departure_datetime"))
        for row in rows:
            row_start = get_datetime(row.departure_datetime)
            row_end = get_datetime(row.arrival_datetime or row.departure_datetime)
            if row_start <= current_end and row_end >= current_start:
                if self._value("vehicle") and row.vehicle == self._value("vehicle"):
                    frappe.throw(_("Vehicle conflict with Trip {0}.").format(row.name))
                if self._value("driver") and self._value("driver") in (row.driver, row.co_driver):
                    frappe.throw(_("Driver conflict with Trip {0}.").format(row.name))
                if self._value("co_driver") and self._value("co_driver") in (row.driver, row.co_driver):
                    frappe.throw(_("Co Driver conflict with Trip {0}.").format(row.name))

        if flt(self._value("distance_km_snapshot")) >= 500 and not self._value("co_driver"):
            frappe.throw(_("Co Driver is required for routes with distance 500 KM or more."))

    def validate_direction_sequence(self):
        if not self._value("driver") or not self._value("from_location"):
            return

        current_start = get_datetime(self._value("departure_datetime") or now_datetime())
        last_trip = frappe.db.sql(
            """
            select name, from_location, to_location, route, trip_date, departure_datetime
            from `tabTrip`
            where name != %s
              and driver = %s
              and trip_status not in ('Cancelled', 'Draft')
              and ifnull(departure_datetime, creation) <= %s
            order by ifnull(departure_datetime, creation) desc, modified desc
            limit 1
            """,
            (self.name or "", self._value("driver"), current_start),
            as_dict=True,
        )
        if not last_trip:
            return

        last_trip = last_trip[0]
        previous_destination = clean_text(last_trip.to_location)
        current_source = clean_text(self._value("from_location"))
        if not previous_destination or not current_source or previous_destination == current_source:
            return

        frappe.throw(
            _(
                "Driver {0} last destination was {1}. Next trip must start from that destination, not from {2}."
            ).format(self._value("driver"), previous_destination, current_source)
        )

    def validate_staff_rows(self):
        rows = self.get("trip_staff") or []
        validate_child_row_uniqueness(rows, lambda row: (row.staff,), "trip staff")
        for row in rows:
            ensure_staff_same_company(row.staff, self._value("base_company"))
            row.notes = clean_long_text(row.notes)
        if self._value("driver") and not any(row.staff == self._value("driver") for row in rows):
            self.append("trip_staff", {"staff": self._value("driver"), "role_type": "Driver", "is_primary": 1})

    def sync_capacity(self):
        booked = frappe.db.sql(
            """
            select ifnull(sum(seat_count), 0)
            from `tabTrip Booking`
            where trip=%s and name!=%s and booking_status not in ('Cancelled', 'Closed')
            """,
            (self.name, self.name or ""),
        )[0][0]
        available = max(0, cint(self._value("seat_capacity") or 0) - cint(booked or 0))
        self._set_if_present("available_seats", available)

    def sync_passengers(self):
        if not self.meta.has_field("passengers"):
            return

        rows = self.get("passengers") or []
        validate_child_row_uniqueness(rows, lambda row: (clean_text(row.document_number),), "trip passenger document")
        validate_child_row_uniqueness(rows, lambda row: (clean_text(row.seat_no),), "trip passenger seat")
        for row in rows:
            row.passenger_name = clean_text(row.passenger_name)
            row.passenger_name_ar = clean_text(row.passenger_name_ar)
            row.nationality = clean_text(row.nationality)
            row.document_number = clean_text(row.document_number)
            row.mobile_no = clean_text(row.mobile_no)
            row.source = clean_text(row.source or "Manual")
            row.notes = clean_long_text(row.notes)

        if rows:
            self._set_if_present("passenger_count", len(rows))
            self._set_if_present("number_of_passengers", len(rows))
            if not self._value("customer_name"):
                self._set_if_present("customer_name", rows[0].passenger_name)
            if not self._value("mobile_no"):
                self._set_if_present("mobile_no", rows[0].mobile_no)

    def sync_route_snapshot(self):
        if not self._value("route") or not frappe.db.exists("Route", self._value("route")):
            return
        route_doc = frappe.get_cached_doc("Route", self._value("route"))
        self._set_if_present("route_label", route_doc.route_title or route_doc.route_name or route_doc.name)
        self._set_if_present("from_location", route_doc.source)
        self._set_if_present("to_location", route_doc.destination)
        self._set_if_present("distance_km_snapshot", flt(route_doc.distance_km))
        self._set_if_present("duration_minutes_snapshot", cint(route_doc.estimated_duration_minutes))

    def build_qr_payload(self):
        payload = {
            "trip": self.name or self._value("trip_code"),
            "trip_code": self._value("trip_code"),
            "trip_status": self._value("trip_status"),
            "trip_date": str(self._value("trip_date")) if self._value("trip_date") else "",
            "route": self._value("route"),
            "vehicle": self._value("vehicle"),
            "driver": self._value("driver"),
            "available_seats": self._value("available_seats"),
            "public_url": build_public_url("tss", "trip", self.name or self._value("trip_code")),
        }
        self._set_if_present("qr_payload", json.dumps(payload, sort_keys=True))
        if not self._value("qr_code"):
            self._set_if_present("qr_code", build_qr_data_uri(self._value("qr_payload")))

    def as_api_dict(self) -> dict:
        data = self.as_dict()
        data["print_context"] = build_trip_print_context(self)
        return data

    def on_update(self):
        if self._value("trip_booking"):
            frappe.db.set_value("Trip Booking", self._value("trip_booking"), "trip", self.name, update_modified=False)
        self.attach_qr_code_image()

    def _value(self, fieldname: str, default=None):
        return self.get(fieldname, default)

    def _set_if_present(self, fieldname: str, value):
        if self.meta.has_field(fieldname):
            self.set(fieldname, value)

    def _map_legacy_fields(self):
        legacy_driver = self._value("assigned_driver")
        legacy_vehicle = self._value("assigned_vehicle")

        if legacy_driver and not self._value("driver"):
            self._set_if_present("driver", legacy_driver)
        if legacy_vehicle and not self._value("vehicle"):
            self._set_if_present("vehicle", legacy_vehicle)
        if self._value("driver") and legacy_driver != self._value("driver") and "assigned_driver" in self.as_dict():
            self.set("assigned_driver", self._value("driver"))
        if self._value("vehicle") and legacy_vehicle != self._value("vehicle") and "assigned_vehicle" in self.as_dict():
            self.set("assigned_vehicle", self._value("vehicle"))

    def attach_qr_code_image(self):
        if not self.name or not self._value("qr_payload") or not self.meta.has_field("qr_code"):
            return
        file_url = save_qr_image_file(self._value("qr_payload"), self.doctype, self.name, "qr_code")
        if file_url and self._value("qr_code") != file_url:
            self.db_set("qr_code", file_url, update_modified=False)


@frappe.whitelist()
def create_return_trip(source_trip: str) -> str:
    source = frappe.get_doc("Trip", source_trip)
    source.check_permission("read")

    reverse_route = get_or_create_reverse_route_name(source.route) if source.route else None
    new_trip = frappe.get_doc(
        {
            "doctype": "Trip",
            "base_company": source.base_company,
            "route": reverse_route or source.route,
            "driver": source.driver,
            "vehicle": source.vehicle,
            "conductor": source.conductor,
            "pricing_rule": source.pricing_rule,
            "customer_name": source.customer_name,
            "mobile_no": source.mobile_no,
            "passenger_count": source.passenger_count,
            "is_return_trip": 1,
            "notes": _("Return trip generated from {0}.").format(source.name),
            "passengers": [
                {
                    "passenger_name": row.passenger_name,
                    "passenger_name_ar": row.passenger_name_ar,
                    "nationality": row.nationality,
                    "document_type": row.document_type,
                    "document_number": row.document_number,
                    "mobile_no": row.mobile_no,
                    "seat_no": row.seat_no,
                    "source": row.source,
                    "expiry_date": row.expiry_date,
                    "notes": row.notes,
                }
                for row in (source.get("passengers") or [])
            ],
        }
    )
    new_trip.insert()
    return new_trip.name


@frappe.whitelist()
def pull_passengers_from_booking(trip_name: str) -> int:
    trip = frappe.get_doc("Trip", trip_name)
    trip.check_permission("write")
    if not trip.trip_booking:
        frappe.throw(_("Trip Booking is required."))

    booking = frappe.get_doc("Trip Booking", trip.trip_booking)
    trip.set("passengers", [])
    for row in booking.get("booking_passenger") or []:
        trip.append(
            "passengers",
            {
                "passenger_name": row.passenger_name,
                "passenger_name_ar": row.passenger_name_ar,
                "nationality": row.nationality,
                "document_type": row.document_type,
                "document_number": row.document_number,
                "mobile_no": row.mobile_no,
                "seat_no": row.seat_no,
                "source": "Booking",
                "expiry_date": row.expiry_date,
                "notes": row.notes,
            },
        )
    trip.save()
    return len(trip.get("passengers") or [])
