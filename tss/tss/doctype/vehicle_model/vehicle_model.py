# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class VehicleModel(Document):
    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_years()
        self.validate_numeric_values()
        self.validate_link_status()

    def normalize_fields(self):
        self.model_name = (self.model_name or "").strip()
        self.model_name_ar = (self.model_name_ar or "").strip()
        self.model_code = (self.model_code or "").strip().upper()
        self.description = (self.description or "").strip()
        self.description_ar = (self.description_ar or "").strip()

    def validate_required_fields(self):
        if not self.model_name:
            frappe.throw(_("Vehicle Model Name is required."))
        if not self.vehicle_make:
            frappe.throw(_("Vehicle Make is required."))
        if not self.vehicle_type:
            frappe.throw(_("Vehicle Type is required."))

    def validate_years(self):
        if self.model_year_from and self.model_year_to and cint(self.model_year_to) < cint(self.model_year_from):
            frappe.throw(_("Model Year To cannot be before Model Year From."))

    def validate_numeric_values(self):
        numeric_fields = {
            "passenger_capacity": self.passenger_capacity,
            "luggage_capacity": self.luggage_capacity,
        }

        for label, value in numeric_fields.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label.replace("_", " ").title()))

    def validate_link_status(self):
        if self.vehicle_make and frappe.db.exists("Vehicle Make", self.vehicle_make):
            make_status = frappe.db.get_value("Vehicle Make", self.vehicle_make, "status")
            if make_status == "Inactive":
                frappe.throw(_("Inactive Vehicle Make cannot be used."))

        if self.vehicle_type and frappe.db.exists("Vehicle Type", self.vehicle_type):
            type_status = frappe.db.get_value("Vehicle Type", self.vehicle_type, "status")
            if type_status == "Inactive":
                frappe.throw(_("Inactive Vehicle Type cannot be used."))

    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "model_name": self.model_name,
            "model_name_ar": self.model_name_ar,
            "model_code": self.model_code,
            "vehicle_make": self.vehicle_make,
            "vehicle_type": self.vehicle_type,
            "status": self.status,
            "model_year_from": self.model_year_from,
            "model_year_to": self.model_year_to,
            "passenger_capacity": self.passenger_capacity,
            "fuel_type": self.fuel_type,
            "transmission_type": self.transmission_type,
            "is_ac": self.is_ac,
            "luggage_capacity": self.luggage_capacity,
            "luggage_capacity_unit": self.luggage_capacity_unit,
            "image": self.image,
            "show_on_website": self.show_on_website,
            "description": self.description,
            "description_ar": self.description_ar,
            "remarks": self.remarks,
        }