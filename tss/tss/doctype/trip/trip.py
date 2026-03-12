from __future__ import annotations

import io
import json
import uuid

import frappe
import qrcode
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime, nowdate

try:
    from hijri_converter import Gregorian
except Exception:
    Gregorian = None


class Trip(Document):
    def before_insert(self):
        self.set_trip_code()
        self.set_default_values()
        self.set_uuid_and_token()
        self.set_hijri_date()

    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_dates()
        self.validate_numeric_values()
        self.validate_driver_vehicle()
        self.pull_route_defaults()
        self.calculate_duration()
        self.calculate_financials()
        self.sync_passenger_count()
        self.build_trip_title()
        self.build_qr_payload()

    def on_update(self):
        self.sync_booking_reference()

    # -------------------------
    # Setup
    # -------------------------
    def set_trip_code(self):
        if not self.trip_code:
            self.trip_code = frappe.model.naming.make_autoname("TRP-.YYYY.-.#####")

    def set_default_values(self):
        if not self.trip_status:
            self.trip_status = "Scheduled"

        if not self.trip_date:
            self.trip_date = nowdate()

        if not self.number_of_passengers:
            self.number_of_passengers = 1

        if not self.distance_unit:
            self.distance_unit = "KM"

    def set_uuid_and_token(self):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())

        if not self.qr_token:
            self.qr_token = uuid.uuid4().hex

    def set_hijri_date(self):
        if not self.trip_date:
            return

        if Gregorian:
            try:
                y, m, d = [int(x) for x in str(self.trip_date).split("-")]
                hijri = Gregorian(y, m, d).to_hijri()
                self.hijri_date = f"{hijri.day:02d}-{hijri.month:02d}-{hijri.year}"
            except Exception:
                self.hijri_date = ""
        else:
            self.hijri_date = ""

    def normalize_fields(self):
        self.customer_name = (self.customer_name or "").strip()
        self.mobile_no = (self.mobile_no or "").strip()
        self.from_location = (self.from_location or "").strip()
        self.to_location = (self.to_location or "").strip()
        self.travel_agency = (self.travel_agency or "").strip()
        self.special_instructions = (self.special_instructions or "").strip()
        self.remarks = (self.remarks or "").strip()

    # -------------------------
    # Validation
    # -------------------------
    def validate_required_fields(self):
        required = {
            "Base Company": self.base_company,
            "Customer Name": self.customer_name,
            "Trip Date": self.trip_date,
        }

        for label, value in required.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))

    def validate_dates(self):
        if self.departure and self.arrival:
            if get_datetime(self.arrival) < get_datetime(self.departure):
                frappe.throw(_("Arrival cannot be before Departure."))

    def validate_numeric_values(self):
        numeric_fields = {
            "Distance": self.distance,
            "Duration Minutes": self.duration_minutes,
            "Avg Speed": self.avg_speed_kmph,
            "Passenger Count": self.number_of_passengers,
            "Per Passenger Value": self.per_passenger_value,
            "Booking Amount": self.booking_amount,
            "Trip Value": self.trip_value,
            "Driver Share": self.driver_share,
            "Company Share": self.company_share,
            "Referral Commission Value": self.referral_commission_value,
            "Odometer Start": self.odometer_start,
            "Odometer End": self.odometer_end,
        }

        for label, value in numeric_fields.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

        if self.number_of_passengers is not None and cint(self.number_of_passengers) <= 0:
            frappe.throw(_("Passenger Count must be greater than zero."))

        if self.odometer_start and self.odometer_end and flt(self.odometer_end) < flt(self.odometer_start):
            frappe.throw(_("Odometer End cannot be before Odometer Start."))

    def validate_driver_vehicle(self):
        for fieldname in ("assigned_driver", "co_driver"):
            driver = self.get(fieldname)
            if driver and frappe.db.exists("Staff", driver):
                is_driver = frappe.db.get_value("Staff", driver, "is_driver")
                if not cint(is_driver):
                    frappe.throw(_("{0} must be a driver.").format(self.meta.get_label(fieldname)))

        if self.assigned_vehicle and frappe.db.exists("Vehicle", self.assigned_vehicle):
            vehicle_doc = frappe.get_doc("Vehicle", self.assigned_vehicle)

            if self.vehicle_type and vehicle_doc.vehicle_type != self.vehicle_type:
                frappe.throw(_("Assigned Vehicle does not belong to selected Vehicle Type."))

    def pull_route_defaults(self):
        if not self.route or not frappe.db.exists("Route", self.route):
            return

        route_doc = frappe.get_doc("Route", self.route)

        if not self.distance and route_doc.distance:
            self.distance = route_doc.distance
        if not self.duration_minutes and route_doc.duration_minutes:
            self.duration_minutes = route_doc.duration_minutes
        if not self.avg_speed_kmph and route_doc.avg_speed_kmph:
            self.avg_speed_kmph = route_doc.avg_speed_kmph
        if not self.from_location and route_doc.from_place_full:
            self.from_location = route_doc.from_place_full
        if not self.to_location and route_doc.to_place_full:
            self.to_location = route_doc.to_place_full

    def calculate_duration(self):
        if self.departure and self.arrival:
            delta = get_datetime(self.arrival) - get_datetime(self.departure)
            self.duration_minutes = max(0, int(delta.total_seconds() // 60))

        minutes = cint(self.duration_minutes)
        if minutes > 0:
            hours = minutes // 60
            mins = minutes % 60
            if hours and mins:
                self.duration_text = f"{hours}h {mins}m"
            elif hours:
                self.duration_text = f"{hours}h"
            else:
                self.duration_text = f"{mins}m"
        else:
            self.duration_text = ""

    def calculate_financials(self):
        passenger_count = cint(self.number_of_passengers or 0)

        if flt(self.per_passenger_value) and passenger_count and not flt(self.trip_value):
            self.trip_value = flt(self.per_passenger_value) * passenger_count

        if flt(self.booking_amount) and not flt(self.trip_value):
            self.trip_value = flt(self.booking_amount)

        if flt(self.trip_value) and flt(self.driver_share):
            self.company_share = flt(self.trip_value) - flt(self.driver_share)

    def sync_passenger_count(self):
        passenger_rows = self.get("passengers") or []

        if passenger_rows:
            self.number_of_passengers = len(passenger_rows)

        seen_docs = set()
        for row in passenger_rows:
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

    def build_trip_title(self):
        parts = [self.customer_name, self.trip_date]
        if self.route:
            parts.append(self.route)
        self.trip_title = " - ".join([str(p) for p in parts if p])

    def build_qr_payload(self):
        payload = {
            "trip": self.name or self.trip_code,
            "trip_code": self.trip_code,
            "trip_status": self.trip_status,
            "trip_date": str(self.trip_date) if self.trip_date else None,
            "trip_time": str(self.trip_time) if self.trip_time else None,
            "customer_name": self.customer_name,
            "mobile_no": self.mobile_no,
            "route": self.route,
            "from_location": self.from_location,
            "to_location": self.to_location,
            "assigned_vehicle": self.assigned_vehicle,
            "assigned_driver": self.assigned_driver,
            "passenger_count": self.number_of_passengers,
            "qr_token": self.qr_token,
        }
        self.qr_payload = json.dumps(payload, ensure_ascii=False)

    # -------------------------
    # Status actions
    # -------------------------
    def mark_confirmed(self):
        self.check_permission("write")
        self.trip_status = "Confirmed"
        self.save()

    def mark_departed(self):
        self.check_permission("write")
        self.trip_status = "Departed"
        if not self.departure:
            self.departure = now_datetime()
        self.save()

    def mark_arrived(self):
        self.check_permission("write")
        self.trip_status = "Arrived"
        if not self.arrival:
            self.arrival = now_datetime()
        self.save()

    def mark_completed(self):
        self.check_permission("write")
        self.trip_status = "Completed"
        if not self.arrival:
            self.arrival = now_datetime()
        self.save()

    def mark_cancelled(self):
        self.check_permission("write")
        self.trip_status = "Cancelled"
        self.save()

    # -------------------------
    # QR code
    # -------------------------
    def generate_qr_code(self):
        self.check_permission("write")

        if not self.qr_payload:
            self.build_qr_payload()

        img = qrcode.make(self.qr_payload)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        file_name = f"{self.trip_code or self.name}-qr.png"
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": file_name,
                "attached_to_doctype": "Trip",
                "attached_to_name": self.name,
                "is_private": 1,
                "content": buffer.getvalue(),
            }
        )
        file_doc.save(ignore_permissions=True)

        self.qr_code = file_doc.file_url
        self.save()
        return self.qr_code

    # -------------------------
    # Booking sync
    # -------------------------
    def sync_booking_reference(self):
        if self.trip_booking and frappe.db.exists("Trip Booking", self.trip_booking):
            booking_status = "In Progress" if self.trip_status in ("Departed", "Arrived") else None
            if self.trip_status == "Completed":
                booking_status = "Completed"
            elif self.trip_status == "Cancelled":
                booking_status = "Cancelled"
            elif self.trip_status in ("Scheduled", "Confirmed"):
                booking_status = "Assigned"

            values = {"trip": self.name}
            if booking_status:
                values["status"] = booking_status

            frappe.db.set_value("Trip Booking", self.trip_booking, values, update_modified=False)

    # -------------------------
    # Passenger helper from booking
    # -------------------------
    def pull_passengers_from_booking(self):
        self.check_permission("write")

        if not self.trip_booking or not frappe.db.exists("Trip Booking", self.trip_booking):
            return 0

        booking = frappe.get_doc("Trip Booking", self.trip_booking)
        booking_rows = booking.get("booking_passenger") or []

        if not booking_rows:
            return 0

        self.set("passengers", [])
        for row in booking_rows:
            self.append(
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

        self.sync_passenger_count()
        self.save()
        return len(self.passengers)

    # -------------------------
    # API helper
    # -------------------------
    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "trip_code": self.trip_code,
            "trip_title": self.trip_title,
            "trip_status": self.trip_status,
            "created_from_booking": self.created_from_booking,
            "trip_booking": self.trip_booking,
            "base_company": self.base_company,
            "branch": self.branch,
            "uuid": self.uuid,
            "hijri_date": self.hijri_date,
            "customer": self.customer,
            "customer_name": self.customer_name,
            "mobile_no": self.mobile_no,
            "number_of_passengers": self.number_of_passengers,
            "per_passenger_value": self.per_passenger_value,
            "currency": self.currency,
            "trip_date": self.trip_date,
            "trip_time": self.trip_time,
            "departure": self.departure,
            "arrival": self.arrival,
            "trip_type": self.trip_type,
            "route": self.route,
            "from_location": self.from_location,
            "to_location": self.to_location,
            "vehicle_type": self.vehicle_type,
            "assigned_vehicle": self.assigned_vehicle,
            "assigned_driver": self.assigned_driver,
            "co_driver": self.co_driver,
            "kashf_sent": self.kashf_sent,
            "is_return_trip": self.is_return_trip,
            "travel_agency": self.travel_agency,
            "is_referral": self.is_referral,
            "distance": self.distance,
            "distance_unit": self.distance_unit,
            "duration_minutes": self.duration_minutes,
            "duration_text": self.duration_text,
            "avg_speed_kmph": self.avg_speed_kmph,
            "odometer_start": self.odometer_start,
            "odometer_end": self.odometer_end,
            "booking_amount": self.booking_amount,
            "trip_value": self.trip_value,
            "driver_share": self.driver_share,
            "company_share": self.company_share,
            "referral_commission_type": self.referral_commission_type,
            "referral_commission_value": self.referral_commission_value,
            "sales_invoice": self.sales_invoice,
            "qr_token": self.qr_token,
            "qr_payload": self.qr_payload,
            "qr_code": self.qr_code,
            "special_instructions": self.special_instructions,
            "remarks": self.remarks,
            "passengers": [
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
                for d in (self.get("passengers") or [])
            ],
        }