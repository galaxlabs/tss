from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime, nowdate


class TripBooking(Document):
    def before_insert(self):
        self.set_booking_code()
        self.set_default_values()
        self.set_booking_datetime()

    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_dates()
        self.validate_numeric_values()
        self.validate_route_and_locations()
        self.validate_driver_and_vehicle()
        self.validate_passengers()
        self.sync_passenger_count()
        self.build_booking_title()
        self.sync_status_dates()

    # -------------------------
    # Setup
    # -------------------------
    def set_booking_code(self):
        if not self.booking_code:
            self.booking_code = frappe.model.naming.make_autoname("TBK-.YYYY.-.#####")

    def set_default_values(self):
        if not self.status:
            self.status = "Draft"

        if not self.booking_source:
            self.booking_source = "Desk"

        if not self.booking_date:
            self.booking_date = nowdate()

        if not self.number_of_passengers:
            self.number_of_passengers = 1

        if not self.pricing_status:
            self.pricing_status = "Not Calculated"

    def set_booking_datetime(self):
        if not self.booking_datetime:
            self.booking_datetime = now_datetime()

    def normalize_fields(self):
        self.customer_name = (self.customer_name or "").strip()
        self.customer_name_ar = (self.customer_name_ar or "").strip()
        self.mobile_no = (self.mobile_no or "").strip()
        self.email = (self.email or "").strip().lower()
        self.reference_no = (self.reference_no or "").strip()
        self.pickup_location = (self.pickup_location or "").strip()
        self.dropoff_location = (self.dropoff_location or "").strip()
        self.pickup_city = (self.pickup_city or "").strip()
        self.dropoff_city = (self.dropoff_city or "").strip()
        self.special_instructions = (self.special_instructions or "").strip()
        self.remarks = (self.remarks or "").strip()

    # -------------------------
    # Validation
    # -------------------------
    def validate_required_fields(self):
        required = {
            "Base Company": self.base_company,
            "Customer Name": self.customer_name,
            "Mobile Number": self.mobile_no,
            "Booking Date": self.booking_date,
            "Trip Date": self.trip_date,
            "Pickup Location": self.pickup_location,
            "Dropoff Location": self.dropoff_location,
        }

        for label, value in required.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))

    def validate_dates(self):
        if self.booking_date and self.trip_date and self.trip_date < self.booking_date:
            pass

    def validate_numeric_values(self):
        if self.number_of_passengers is not None and cint(self.number_of_passengers) <= 0:
            frappe.throw(_("Number of Passengers must be greater than zero."))

        for label, value in {
            "Estimated Amount": self.estimated_amount,
            "Final Amount": self.final_amount,
        }.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

    def validate_route_and_locations(self):
        if self.route and frappe.db.exists("Route", self.route):
            route_doc = frappe.get_doc("Route", self.route)

            if not self.pickup_city:
                self.pickup_city = route_doc.from_city
            if not self.dropoff_city:
                self.dropoff_city = route_doc.to_city

        if self.pickup_location and self.dropoff_location:
            if self.pickup_location.strip().lower() == self.dropoff_location.strip().lower():
                frappe.throw(_("Pickup Location and Dropoff Location cannot be the same."))

    def validate_driver_and_vehicle(self):
        if self.assigned_driver and frappe.db.exists("Staff", self.assigned_driver):
            is_driver = frappe.db.get_value("Staff", self.assigned_driver, "is_driver")
            if not cint(is_driver):
                frappe.throw(_("Assigned Staff must be a driver."))

        if self.vehicle and frappe.db.exists("Vehicle", self.vehicle):
            vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)

            if self.vehicle_type and vehicle_doc.vehicle_type != self.vehicle_type:
                frappe.throw(_("Selected Vehicle does not belong to selected Vehicle Type."))

    def validate_passengers(self):
        seen_docs = set()

        for row in self.get("booking_passenger") or []:
            row.passenger_name = (row.passenger_name or "").strip()
            row.passenger_name_ar = (row.passenger_name_ar or "").strip()
            row.document_number = (row.document_number or "").strip()
            row.contact_no = (row.contact_no or "").strip()
            row.notes = (row.notes or "").strip()

            if row.document_type and row.document_number:
                key = (row.document_type, row.document_number)
                if key in seen_docs:
                    frappe.throw(_("Duplicate passenger document found: {0} / {1}").format(*key))
                seen_docs.add(key)

    def sync_passenger_count(self):
        passenger_rows = self.get("booking_passenger") or []
        if passenger_rows:
            self.number_of_passengers = len(passenger_rows)

    def build_booking_title(self):
        parts = [self.customer_name, self.trip_date]
        if self.route:
            parts.append(self.route)
        elif self.pickup_city or self.dropoff_city:
            parts.append(f"{self.pickup_city} → {self.dropoff_city}".strip())
        self.booking_title = " - ".join([str(p) for p in parts if p])

    def sync_status_dates(self):
        if self.status == "Confirmed" and not self.confirmed_on:
            self.confirmed_on = now_datetime()

        if self.status == "Cancelled" and not self.cancelled_on:
            self.cancelled_on = now_datetime()

    # -------------------------
    # Customer / Trip actions
    # -------------------------
    def create_customer_if_available(self) -> str | None:
        self.check_permission("write")

        if self.customer:
            return self.customer

        if not frappe.db.exists("DocType", "Customer"):
            return None

        customer_name = self.customer_name
        existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
        if existing:
            self.customer = existing
            self.db_set("customer", existing)
            return existing

        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": customer_name,
                "mobile_no": self.mobile_no,
                "email_id": self.email,
            }
        )
        customer.insert(ignore_permissions=True)

        self.customer = customer.name
        self.db_set("customer", customer.name)
        return customer.name

    def confirm_booking(self) -> dict:
        self.check_permission("write")

        if self.status not in ("Draft", "Pending"):
            frappe.throw(_("Only Draft or Pending booking can be confirmed."))

        customer = self.create_customer_if_available()

        self.status = "Confirmed"
        self.confirmed_on = now_datetime()
        self.save()

        return {
            "customer": customer,
            "status": self.status,
        }

    def create_trip(self) -> str:
        self.check_permission("write")

        if self.trip:
            return self.trip

        if not frappe.db.exists("DocType", "Trip"):
            frappe.throw(_("Trip DocType is not available."))

        trip_doc = frappe.get_doc(
            {
                "doctype": "Trip",
                "trip_booking": self.name,
                "base_company": self.base_company,
                "customer": self.customer,
                "customer_name": self.customer_name,
                "mobile_no": self.mobile_no,
                "number_of_passengers": self.number_of_passengers,
                "trip_date": self.trip_date,
                "trip_time": self.trip_time,
                "trip_type": self.trip_type,
                "route": self.route,
                "from_location": self.pickup_location,
                "to_location": self.dropoff_location,
                "vehicle_type": self.vehicle_type,
                "assigned_vehicle": self.vehicle,
                "assigned_driver": self.assigned_driver,
                "currency": self.currency,
                "booking_amount": self.final_amount or self.estimated_amount,
                "created_from_booking": 1,
                "special_instructions": self.special_instructions,
                "remarks": self.remarks,
            }
        )

        for row in self.get("booking_passenger") or []:
            trip_doc.append(
                "passengers",
                {
                    "passenger_name": row.passenger_name,
                    "passenger_name_ar": row.passenger_name_ar,
                    "nationality": row.nationality,
                    "passenger_master": row.passenger_master,
                    "document_type": row.document_type,
                    "document_number": row.document_number,
                    "contact_no": row.contact_no,
                    "source": row.source or "BOOKING",
                    "expiry_date": row.expiry_date,
                    "seat_no": row.seat_no,
                    "notes": row.notes,
                    "is_auto_filled": 1,
                },
            )

        trip_doc.insert(ignore_permissions=True)

        self.trip = trip_doc.name

        if self.status in ("Confirmed", "Pending", "Draft"):
            self.status = "Assigned" if (self.vehicle or self.assigned_driver) else "Confirmed"

        self.save()
        return self.trip

    # -------------------------
    # API helper
    # -------------------------
    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "booking_code": self.booking_code,
            "booking_title": self.booking_title,
            "status": self.status,
            "booking_source": self.booking_source,
            "reference_no": self.reference_no,
            "base_company": self.base_company,
            "booking_date": self.booking_date,
            "booking_datetime": self.booking_datetime,
            "customer_name": self.customer_name,
            "customer_name_ar": self.customer_name_ar,
            "mobile_no": self.mobile_no,
            "email": self.email,
            "customer": self.customer,
            "nationality": self.nationality,
            "number_of_passengers": self.number_of_passengers,
            "trip_date": self.trip_date,
            "trip_time": self.trip_time,
            "trip_type": self.trip_type,
            "route": self.route,
            "pickup_location": self.pickup_location,
            "dropoff_location": self.dropoff_location,
            "pickup_city": self.pickup_city,
            "dropoff_city": self.dropoff_city,
            "vehicle_type": self.vehicle_type,
            "vehicle": self.vehicle,
            "assigned_driver": self.assigned_driver,
            "currency": self.currency,
            "estimated_amount": self.estimated_amount,
            "final_amount": self.final_amount,
            "pricing_status": self.pricing_status,
            "trip": self.trip,
            "sales_invoice": self.sales_invoice,
            "created_by_staff": self.created_by_staff,
            "confirmed_on": self.confirmed_on,
            "cancelled_on": self.cancelled_on,
            "special_instructions": self.special_instructions,
            "remarks": self.remarks,
            "booking_passenger": [
                {
                    "passenger_name": d.passenger_name,
                    "passenger_name_ar": d.passenger_name_ar,
                    "nationality": d.nationality,
                    "passenger_master": d.passenger_master,
                    "document_type": d.document_type,
                    "document_number": d.document_number,
                    "contact_no": d.contact_no,
                    "source": d.source,
                    "expiry_date": d.expiry_date,
                    "seat_no": d.seat_no,
                    "notes": d.notes,
                    "is_auto_filled": d.is_auto_filled,
                }
                for d in (self.get("booking_passenger") or [])
            ],
        }