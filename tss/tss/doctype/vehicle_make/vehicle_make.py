# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, validate_url


class VehicleMake(Document):
    def before_insert(self):
        self.set_default_values()

    def validate(self):
        self.normalize_fields()
        self.validate_required_fields()
        self.validate_code()
        self.validate_website()
        self.sync_status_flags()

    def set_default_values(self):
        if not self.status:
            self.status = "Draft"

        if self.is_active is None:
            self.is_active = 1

    def normalize_fields(self):
        self.make_name = (self.make_name or "").strip()
        self.make_name_ar = (self.make_name_ar or "").strip()
        self.make_code = (self.make_code or "").strip().upper()
        self.country_of_origin = (self.country_of_origin or "").strip()
        self.website = (self.website or "").strip()
        self.website_label = (self.website_label or "").strip()
        self.website_label_ar = (self.website_label_ar or "").strip()
        self.description = (self.description or "").strip()
        self.description_ar = (self.description_ar or "").strip()

    def validate_required_fields(self):
        if not self.make_name:
            frappe.throw(_("Vehicle Make Name is required."))

    def validate_code(self):
        if self.make_code and " " in self.make_code:
            frappe.throw(_("Vehicle Make Code cannot contain spaces."))

    def validate_website(self):
        if self.website:
            validate_url(self.website, throw=True)

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status == "Inactive":
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

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

    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "make_name": self.make_name,
            "make_name_ar": self.make_name_ar,
            "make_code": self.make_code,
            "status": self.status,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "country_of_origin": self.country_of_origin,
            "website": self.website,
            "logo": self.logo,
            "show_on_website": self.show_on_website,
            "website_label": self.website_label,
            "website_label_ar": self.website_label_ar,
            "description": self.description,
            "description_ar": self.description_ar,
            "remarks": self.remarks,
        }