# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleInspectionChecklistItem(Document):
    def validate(self):
        self.item_code = (self.item_code or "").strip().upper()
        self.item_name = (self.item_name or "").strip()
        self.item_name_ar = (self.item_name_ar or "").strip()
        self.description = (self.description or "").strip()

        if not self.item_code:
            frappe.throw(_("Item Code is required."))

        if not self.item_name:
            frappe.throw(_("Item Name is required."))