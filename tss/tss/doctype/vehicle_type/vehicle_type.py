# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt
# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class VehicleType(Document):
    def before_insert(self):
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_numeric_values()
        self.sync_status_flags()
        self.validate_pricing_rules()

    # -------------------------
    # Setup
    # -------------------------
    def set_default_values(self):
        if not self.status:
            self.status = "Draft"

        if self.is_active is None:
            self.is_active = 1

    def normalize_fields(self):
        self.type_name = (self.type_name or "").strip()
        self.type_name_ar = (self.type_name_ar or "").strip()
        self.type_code = (self.type_code or "").strip().upper()
        self.category = (self.category or "").strip()
        self.default_service_unit = (self.default_service_unit or "").strip()
        self.description = (self.description or "").strip()
        self.description_ar = (self.description_ar or "").strip()
        self.website_label = (self.website_label or "").strip()
        self.website_label_ar = (self.website_label_ar or "").strip()

    # -------------------------
    # Validation
    # -------------------------
    def validate_required_fields(self):
        if not self.type_name:
            frappe.throw(_("Vehicle Type Name is required."))

        if not self.category:
            frappe.throw(_("Category is required."))

    def validate_numeric_values(self):
        numeric_fields = {
            "passenger_capacity": self.passenger_capacity,
            "luggage_capacity": self.luggage_capacity,
            "minimum_booking_hours": self.minimum_booking_hours,
            "minimum_distance_km": self.minimum_distance_km,
            "base_fare": self.base_fare,
            "sort_order": self.sort_order,
        }

        for label, value in numeric_fields.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label.replace("_", " ").title()))

        if cint(self.passenger_capacity) == 0 and self.category == "Passenger":
            # optional strict rule, keep if useful
            pass

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status == "Inactive":
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

    def validate_pricing_rules(self):
        if not any([
            cint(self.allow_route_pricing),
            cint(self.allow_distance_pricing),
            cint(self.allow_hourly_pricing),
            cint(self.allow_daily_pricing),
        ]):
            frappe.throw(_("At least one pricing mode must be enabled."))

        if self.base_fare and not self.base_currency and frappe.db.exists("DocType", "Currency"):
            frappe.throw(_("Base Currency is required when Base Fare is set."))

    # -------------------------
    # Actions
    # -------------------------
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

    # -------------------------
    # API helper
    # -------------------------
    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "type_name": self.type_name,
            "type_name_ar": self.type_name_ar,
            "type_code": self.type_code,
            "category": self.category,
            "status": self.status,
            "is_active": self.is_active,
            "passenger_capacity": self.passenger_capacity,
            "luggage_capacity": self.luggage_capacity,
            "luggage_capacity_unit": self.luggage_capacity_unit,
            "seat_configuration": self.seat_configuration,
            "default_service_unit": self.default_service_unit,
            "minimum_booking_hours": self.minimum_booking_hours,
            "minimum_distance_km": self.minimum_distance_km,
            "allow_route_pricing": self.allow_route_pricing,
            "allow_distance_pricing": self.allow_distance_pricing,
            "allow_hourly_pricing": self.allow_hourly_pricing,
            "allow_daily_pricing": self.allow_daily_pricing,
            "allow_dynamic_pricing": self.allow_dynamic_pricing,
            "base_fare": self.base_fare,
            "base_currency": self.base_currency,
            "sort_order": self.sort_order,
            "description": self.description,
            "description_ar": self.description_ar,
            "icon": self.icon,
            "image": self.image,
            "website_label": self.website_label,
            "website_label_ar": self.website_label_ar,
            "show_on_website": self.show_on_website,
            "remarks": self.remarks,
        }