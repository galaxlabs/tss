# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


class PeakHourRule(Document):
    def before_insert(self):
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.build_rule_title()
        self.validate_required_fields()
        self.validate_values()
        self.validate_dates()
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
        self.days_of_week = (self.days_of_week or "").strip()
        self.description = (self.description or "").strip()
        self.remarks = (self.remarks or "").strip()

    def build_rule_title(self):
        self.rule_title = f"{self.base_company or ''} | {self.from_time or ''} - {self.to_time or ''}".strip(" |")

    def validate_required_fields(self):
        if not self.rule_code:
            frappe.throw(_("Rule Code is required."))
        if not self.base_company:
            frappe.throw(_("Base Company is required."))
        if not self.from_time or not self.to_time:
            frappe.throw(_("From Time and To Time are required."))

    def validate_values(self):
        if flt(self.multiplier) < 0:
            frappe.throw(_("Multiplier cannot be negative."))
        if self.fixed_surcharge is not None and flt(self.fixed_surcharge) < 0:
            frappe.throw(_("Fixed Surcharge cannot be negative."))

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

    def as_api_dict(self):
        return {
            "name": self.name,
            "rule_code": self.rule_code,
            "rule_title": self.rule_title,
            "status": self.status,
            "priority": self.priority,
            "base_company": self.base_company,
            "is_active": self.is_active,
            "from_time": self.from_time,
            "to_time": self.to_time,
            "days_of_week": self.days_of_week,
            "multiplier": self.multiplier,
            "fixed_surcharge": self.fixed_surcharge,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "description": self.description,
            "remarks": self.remarks,
        }