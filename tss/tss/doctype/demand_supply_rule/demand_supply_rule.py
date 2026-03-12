# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class DemandSupplyRule(Document):
    def before_insert(self):
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.build_rule_title()
        self.validate_required_fields()
        self.validate_values()
        self.sync_status_flags()

    def set_default_values(self):
        if not self.status:
            self.status = "Draft"
        if self.is_active is None:
            self.is_active = 1
        if not self.priority:
            self.priority = 100
        if not self.multiplier:
            self.multiplier = 1.0

    def normalize_fields(self):
        self.rule_code = (self.rule_code or "").strip().upper()
        self.description = (self.description or "").strip()
        self.remarks = (self.remarks or "").strip()

    def build_rule_title(self):
        parts = [self.base_company, self.route, self.vehicle_type, self.trip_type]
        self.rule_title = " | ".join([p for p in parts if p])

    def validate_required_fields(self):
        if not self.rule_code:
            frappe.throw(_("Rule Code is required."))
        if not self.base_company:
            frappe.throw(_("Base Company is required."))

    def validate_values(self):
        for label, value in {
            "Priority": self.priority,
            "Booking Threshold": self.booking_threshold,
            "Available Vehicle Threshold": self.available_vehicle_threshold,
            "Multiplier": self.multiplier,
            "Fixed Surcharge": self.fixed_surcharge,
        }.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status == "Inactive":
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

    def as_api_dict(self):
        return {
            "name": self.name,
            "rule_code": self.rule_code,
            "rule_title": self.rule_title,
            "status": self.status,
            "priority": self.priority,
            "base_company": self.base_company,
            "is_active": self.is_active,
            "route": self.route,
            "vehicle_type": self.vehicle_type,
            "trip_type": self.trip_type,
            "booking_threshold": self.booking_threshold,
            "available_vehicle_threshold": self.available_vehicle_threshold,
            "multiplier": self.multiplier,
            "fixed_surcharge": self.fixed_surcharge,
            "description": self.description,
            "remarks": self.remarks,
        }