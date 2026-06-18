from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from gbase.gbase.doctype.entity_document.entity_document import calculate_document_status
from tss.utils.transport_naming import clean_long_text, clean_text, make_code
from tss.utils.transport_validation import (
    ensure_company_is_active,
    ensure_same_company,
    ensure_staff_is_driver,
    normalize_identifier,
    normalize_plate,
    sync_verification_fields,
    validate_child_row_uniqueness,
)


class Vehicle(Document):
    def before_insert(self):
        if not self.vehicle_code:
            self.vehicle_code = make_code(self.doctype)

    def validate(self):
        self.chassis_no = normalize_identifier(self.chassis_no)
        self.engine_no = normalize_identifier(self.engine_no)
        self.plate_no = normalize_plate(self.plate_no)
        self.plate_no_ar = clean_text(self.plate_no_ar)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Draft")
        self.is_active = 1 if self.status == "Active" else 0

        self.sync_model_defaults()
        self.validate_required_fields()
        self.validate_numeric_fields()
        self.validate_links()
        self.validate_uniqueness()
        self.validate_documents()
        self.sync_display_fields()

    def sync_model_defaults(self):
        if not self.vehicle_model:
            return

        model_doc = frappe.get_doc("Vehicle Model", self.vehicle_model)
        self.vehicle_make = model_doc.vehicle_make
        self.vehicle_type = model_doc.vehicle_type
        self.vehicle_category = model_doc.vehicle_category or frappe.db.get_value(
            "Vehicle Type", model_doc.vehicle_type, "category"
        )

        if not self.seat_capacity and model_doc.seat_capacity:
            self.seat_capacity = model_doc.seat_capacity
        if not self.fuel_type and model_doc.fuel_type:
            self.fuel_type = model_doc.fuel_type

    def sync_display_fields(self):
        self.display_title = self.plate_no or self.vehicle_code

    def validate_required_fields(self):
        for label, value in {
            "Base Company": self.base_company,
            "Vehicle Model": self.vehicle_model,
            "Plate No": self.plate_no,
        }.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))

    def validate_numeric_fields(self):
        for label, value in {
            "Model Year": self.model_year,
            "Seating Capacity": self.seat_capacity,
            "Odometer": self.odometer,
        }.items():
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

    def validate_links(self):
        if self.status == "Active":
            ensure_company_is_active(self.base_company)

        if self.assigned_driver:
            ensure_staff_is_driver(self.assigned_driver, self.base_company)

        if self.default_route:
            if not frappe.db.exists("Route", self.default_route):
                frappe.throw(_("Default Route must exist."))

        if self.vehicle_model:
            model_doc = frappe.get_doc("Vehicle Model", self.vehicle_model)
            if model_doc.vehicle_make and self.vehicle_make != model_doc.vehicle_make:
                frappe.throw(_("Vehicle Make is derived from the selected Vehicle Model."))
            if model_doc.vehicle_type and self.vehicle_type != model_doc.vehicle_type:
                frappe.throw(_("Vehicle Type is derived from the selected Vehicle Model."))

    def validate_uniqueness(self):
        for fieldname in ("chassis_no", "engine_no", "plate_no"):
            value = self.get(fieldname)
            if not value:
                continue
            existing = frappe.db.exists("Vehicle", {"name": ["!=", self.name], fieldname: value})
            if existing:
                frappe.throw(_("{0} already exists in Vehicle {1}.").format(self.meta.get_label(fieldname), existing))

    def validate_documents(self):
        rows = self.get("documents") or []
        validate_child_row_uniqueness(
            rows,
            lambda row: (clean_text(row.document_type), clean_text(row.document_no)),
            "vehicle document",
        )
        for row in rows:
            row.document_no = clean_text(row.document_no)
            row.issuing_authority = clean_text(row.issuing_authority)
            row.notes = clean_long_text(row.notes)
            if row.issue_date and row.expiry_date and row.expiry_date < row.issue_date:
                frappe.throw(_("Row {0}: Expiry Date cannot be before Issue Date.").format(row.idx))
            row.status = calculate_document_status(row)
            sync_verification_fields(row)
