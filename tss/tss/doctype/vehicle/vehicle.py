# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate


class Vehicle(Document):
    def before_insert(self):
        self.set_vehicle_code()
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_numeric_values()
        self.validate_dates()
        self.validate_driver()
        self.validate_model_mapping()
        self.apply_model_defaults()
        self.build_display_title()
        self.sync_status_flags()
        self.validate_documents()

    def set_vehicle_code(self):
        if not self.vehicle_code:
            self.vehicle_code = frappe.model.naming.make_autoname("VEH-.YYYY.-.#####")

    def set_default_values(self):
        if not self.status:
            self.status = "Draft"
        if self.is_active is None:
            self.is_active = 1

    def normalize_fields(self):
        self.license_plate = (self.license_plate or "").strip().upper()
        self.plate_number = (self.plate_number or "").strip().upper()
        self.registration_no = (self.registration_no or "").strip()
        self.chassis_no = (self.chassis_no or "").strip().upper()
        self.engine_no = (self.engine_no or "").strip().upper()
        self.color = (self.color or "").strip()
        self.seat_configuration = (self.seat_configuration or "").strip()
        self.remarks = (self.remarks or "").strip()

    def validate_required_fields(self):
        required = {
            "Vehicle Type": self.vehicle_type,
            "Vehicle Make": self.vehicle_make,
            "Vehicle Model": self.vehicle_model,
            "License Plate": self.license_plate,
            "Base Company": self.base_company,
        }
        for label, value in required.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))

    def validate_numeric_values(self):
        numeric_fields = {
            "Passenger Capacity": self.passenger_capacity,
            "Luggage Capacity": self.luggage_capacity,
            "Odometer Reading": self.odometer_reading,
        }
        for label, value in numeric_fields.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

    def validate_dates(self):
        date_pairs = [
            ("purchase_date", "service_start_date", _("Service Start Date cannot be before Purchase Date.")),
        ]
        for start_field, end_field, message in date_pairs:
            start_value = self.get(start_field)
            end_value = self.get(end_field)
            if start_value and end_value and end_value < start_value:
                frappe.throw(message)

    def validate_driver(self):
        if self.assigned_driver and frappe.db.exists("Staff", self.assigned_driver):
            is_driver = frappe.db.get_value("Staff", self.assigned_driver, "is_driver")
            if not cint(is_driver):
                frappe.throw(_("Assigned Staff must be a driver."))

    def validate_model_mapping(self):
        if not self.vehicle_model or not frappe.db.exists("Vehicle Model", self.vehicle_model):
            return

        model_doc = frappe.get_doc("Vehicle Model", self.vehicle_model)

        if model_doc.vehicle_make != self.vehicle_make:
            frappe.throw(_("Vehicle Model does not belong to selected Vehicle Make."))

        if model_doc.vehicle_type != self.vehicle_type:
            frappe.throw(_("Vehicle Model does not belong to selected Vehicle Type."))

    def apply_model_defaults(self):
        if not self.vehicle_model or not frappe.db.exists("Vehicle Model", self.vehicle_model):
            return

        model_doc = frappe.get_doc("Vehicle Model", self.vehicle_model)

        if not self.passenger_capacity and model_doc.passenger_capacity:
            self.passenger_capacity = model_doc.passenger_capacity
        if not self.fuel_type and model_doc.fuel_type:
            self.fuel_type = model_doc.fuel_type
        if not self.transmission_type and model_doc.transmission_type:
            self.transmission_type = model_doc.transmission_type
        if not self.luggage_capacity and model_doc.luggage_capacity:
            self.luggage_capacity = model_doc.luggage_capacity
        if not self.luggage_capacity_unit and model_doc.luggage_capacity_unit:
            self.luggage_capacity_unit = model_doc.luggage_capacity_unit

    def build_display_title(self):
        parts = [self.vehicle_make, self.vehicle_model, self.license_plate]
        self.display_title = " - ".join([p for p in parts if p])

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status in ("Inactive", "Out of Service", "Sold"):
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

    def validate_documents(self):
        seen = set()

        for row in self.get("documents") or []:
            key = ((row.document_type or "").strip(), (row.document_number or "").strip())
            if key in seen:
                frappe.throw(
                    _("Duplicate document found: {0} / {1}").format(
                        row.document_type, row.document_number
                    )
                )
            seen.add(key)

            if row.issue_date and row.expiry_date and row.expiry_date < row.issue_date:
                frappe.throw(_("Expiry Date cannot be before Issue Date in document row {0}.").format(row.idx))

            if row.expiry_date and str(row.expiry_date) < nowdate():
                row.status = "Expired"

    def activate(self):
        self.check_permission("write")
        self.status = "Active"
        self.is_active = 1
        self.save()

    def deactivate(self):
        self.check_permission("write")
        self.status = "Inactive"
        self.is_active = 0
        self.save()

    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "vehicle_code": self.vehicle_code,
            "display_title": self.display_title,
            "vehicle_type": self.vehicle_type,
            "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model,
            "model_year": self.model_year,
            "license_plate": self.license_plate,
            "plate_number": self.plate_number,
            "registration_no": self.registration_no,
            "chassis_no": self.chassis_no,
            "engine_no": self.engine_no,
            "base_company": self.base_company,
            "branch": self.branch,
            "assigned_driver": self.assigned_driver,
            "ownership_type": self.ownership_type,
            "status": self.status,
            "is_active": self.is_active,
            "passenger_capacity": self.passenger_capacity,
            "luggage_capacity": self.luggage_capacity,
            "luggage_capacity_unit": self.luggage_capacity_unit,
            "fuel_type": self.fuel_type,
            "transmission_type": self.transmission_type,
            "color": self.color,
            "odometer_reading": self.odometer_reading,
            "odometer_unit": self.odometer_unit,
            "seat_configuration": self.seat_configuration,
            "purchase_date": self.purchase_date,
            "service_start_date": self.service_start_date,
            "insurance_expiry_date": self.insurance_expiry_date,
            "registration_expiry_date": self.registration_expiry_date,
            "vehicle_image": self.vehicle_image,
            "remarks": self.remarks,
            "documents": [
                {
                    "document_type": d.document_type,
                    "document_name_label": d.document_name_label,
                    "document_number": d.document_number,
                    "issue_date": d.issue_date,
                    "expiry_date": d.expiry_date,
                    "issued_by": d.issued_by,
                    "attachment": d.attachment,
                    "status": d.status,
                    "is_verified": d.is_verified,
                    "notes": d.notes,
                }
                for d in (self.get("documents") or [])
            ],
        }