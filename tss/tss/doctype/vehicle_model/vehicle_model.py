from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from tss.utils.transport_naming import clean_long_text, clean_text, make_readable_code


class VehicleModel(Document):
    def before_insert(self):
        if not self.model_code:
            self.model_code = make_readable_code(self.doctype, self.model_name, "model_code", fallback="MODEL")

    def validate(self):
        self.model_name = clean_text(self.model_name)
        self.model_name_ar = clean_text(self.model_name_ar)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Active")

        if not self.model_name:
            frappe.throw(_("Vehicle Model Name is required."))
        if not self.vehicle_make:
            frappe.throw(_("Vehicle Make is required."))
        if not self.vehicle_type:
            frappe.throw(_("Vehicle Type is required."))
        if not self.model_code:
            self.model_code = make_readable_code(self.doctype, self.model_name, "model_code", fallback="MODEL")
        self.vehicle_category = frappe.db.get_value("Vehicle Type", self.vehicle_type, "category")
        if not self.seat_capacity:
            self.seat_capacity = frappe.db.get_value("Vehicle Type", self.vehicle_type, "default_seating_capacity")
        if self.model_year_from and self.model_year_to and cint(self.model_year_to) < cint(self.model_year_from):
            frappe.throw(_("Model Year To cannot be before Model Year From."))
