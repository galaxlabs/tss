# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt




	

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate


class TripPricingRule(Document):
    def before_insert(self):
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.build_rule_title()
        self.validate_required_fields()
        self.validate_amounts()
        self.validate_dates()
        self.sync_status_flags()

    def set_default_values(self):
        if not self.status:
            self.status = "Draft"
        if self.is_active is None:
            self.is_active = 1
        if not self.priority:
            self.priority = 100

    def normalize_fields(self):
        self.rule_code = (self.rule_code or "").strip().upper()
        self.description = (self.description or "").strip()
        self.description_ar = (self.description_ar or "").strip()
        self.remarks = (self.remarks or "").strip()

    def build_rule_title(self):
        parts = [
            self.base_company,
            self.route,
            self.vehicle_type,
            self.trip_type,
            self.pricing_method,
        ]
        self.rule_title = " | ".join([p for p in parts if p])

    def validate_required_fields(self):
        if not self.rule_code:
            frappe.throw(_("Rule Code is required."))
        if not self.base_company:
            frappe.throw(_("Base Company is required."))

    def validate_amounts(self):
        for label, value in {
            "Priority": self.priority,
            "Base Amount": self.base_amount,
            "Minimum Amount": self.minimum_amount,
            "Maximum Amount": self.maximum_amount,
            "Per KM Rate": self.per_km_rate,
            "Per Hour Rate": self.per_hour_rate,
            "Per Day Rate": self.per_day_rate,
            "Per Passenger Rate": self.per_passenger_rate,
            "Round To Nearest": self.round_to_nearest,
        }.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

        if self.minimum_amount and self.maximum_amount and flt(self.minimum_amount) > flt(self.maximum_amount):
            frappe.throw(_("Minimum Amount cannot be greater than Maximum Amount."))

    def validate_dates(self):
        if self.effective_from and self.effective_to and getdate(self.effective_from) > getdate(self.effective_to):
            frappe.throw(_("Effective From cannot be after Effective To."))

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status == "Inactive":
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

    def is_effective_today(self) -> bool:
        today = getdate(nowdate())
        if self.effective_from and getdate(self.effective_from) > today:
            return False
        if self.effective_to and getdate(self.effective_to) < today:
            return False
        return cint(self.is_active) == 1 and self.status == "Active"

    def as_api_dict(self):
        return {
            "name": self.name,
            "rule_code": self.rule_code,
            "rule_title": self.rule_title,
            "status": self.status,
            "priority": self.priority,
            "base_company": self.base_company,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "trip_type": self.trip_type,
            "route": self.route,
            "vehicle_type": self.vehicle_type,
            "customer_type": self.customer_type,
            "booking_source": self.booking_source,
            "currency": self.currency,
            "pricing_method": self.pricing_method,
            "base_amount": self.base_amount,
            "minimum_amount": self.minimum_amount,
            "maximum_amount": self.maximum_amount,
            "per_km_rate": self.per_km_rate,
            "per_hour_rate": self.per_hour_rate,
            "per_day_rate": self.per_day_rate,
            "per_passenger_rate": self.per_passenger_rate,
            "allow_peak_hour": self.allow_peak_hour,
            "allow_demand_supply": self.allow_demand_supply,
            "allow_manual_override": self.allow_manual_override,
            "round_to_nearest": self.round_to_nearest,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "description": self.description,
            "description_ar": self.description_ar,
            "remarks": self.remarks,
        }	
