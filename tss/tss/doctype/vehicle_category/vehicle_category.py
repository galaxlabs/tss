from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from tss.utils.transport_naming import clean_long_text, clean_text, make_readable_code


class VehicleCategory(Document):
    def before_insert(self):
        if not self.category_code:
            self.category_code = make_readable_code(
                self.doctype, self.category_name, "category_code", fallback="CAT"
            )

    def validate(self):
        self.category_name = clean_text(self.category_name)
        self.category_name_ar = clean_text(self.category_name_ar)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Active")
        self.is_active = 1 if self.status == "Active" else 0

        if not self.category_name:
            frappe.throw(_("Category Name is required."))
        if not self.category_code:
            self.category_code = make_readable_code(
                self.doctype, self.category_name, "category_code", fallback="CAT"
            )
