from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from tss.utils.transport_naming import clean_long_text, clean_text, make_code


class TripPricingRule(Document):
    def before_insert(self):
        if not self.rule_code:
            self.rule_code = make_code(self.doctype)

    def validate(self):
        self.service_type = clean_text(self.service_type)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Active")
        self.is_active = 1 if self.status == "Active" else 0
        self.rule_title = " | ".join(value for value in [self.base_company, self.route, self.vehicle_type, self.trip_type] if value)

        if not self.base_company:
            frappe.throw(_("Base Company is required."))
        if not self.currency:
            frappe.throw(_("Currency is required."))
        if not self.effective_from:
            frappe.throw(_("Effective From is required."))
        if flt(self.amount) <= 0:
            frappe.throw(_("Amount must be greater than zero."))
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw(_("Effective To cannot be before Effective From."))
