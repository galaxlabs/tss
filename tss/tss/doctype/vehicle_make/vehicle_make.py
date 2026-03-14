from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from tss.utils.transport_naming import clean_long_text, clean_text, make_readable_code


class VehicleMake(Document):
    def before_insert(self):
        if not self.make_code:
            self.make_code = make_readable_code(self.doctype, self.make_name, "make_code", fallback="MAKE")

    def validate(self):
        self.make_name = clean_text(self.make_name)
        self.make_name_ar = clean_text(self.make_name_ar)
        self.country_of_origin = clean_text(self.country_of_origin)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Active")
        self.is_active = 1 if self.status == "Active" else 0

        if not self.make_name:
            frappe.throw(_("Vehicle Make Name is required."))
        if not self.make_code:
            self.make_code = make_readable_code(self.doctype, self.make_name, "make_code", fallback="MAKE")
