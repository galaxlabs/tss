from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from tss.utils.transport_naming import clean_long_text, clean_text, make_readable_code


class VehicleType(Document):
    def before_insert(self):
        if not self.type_code:
            self.type_code = make_readable_code(self.doctype, self.type_name, "type_code", fallback="TYPE")

    def validate(self):
        self.type_name = clean_text(self.type_name)
        self.type_name_ar = clean_text(self.type_name_ar)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Active")
        self.is_active = 1 if self.status == "Active" else 0

        if not self.type_name:
            frappe.throw(_("Vehicle Type Name is required."))
        if not self.category:
            frappe.throw(_("Vehicle Category is required."))
        if cint(self.default_seating_capacity) < 0:
            frappe.throw(_("Default Seating Capacity cannot be negative."))
        if not self.type_code:
            self.type_code = make_readable_code(self.doctype, self.type_name, "type_code", fallback="TYPE")
