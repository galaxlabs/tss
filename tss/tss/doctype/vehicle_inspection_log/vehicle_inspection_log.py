from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from tss.utils.transport_naming import clean_long_text, clean_text, make_code
from tss.utils.transport_validation import ensure_same_company, ensure_staff_same_company, validate_child_row_uniqueness


def get_active_checklist_rows(vehicle_type: str | None = None):
    filters = {"is_active": 1}
    if vehicle_type:
        filters["vehicle_type"] = ["in", [vehicle_type, ""]]
    return frappe.get_all(
        "Vehicle Inspection Checklist Item",
        filters=filters,
        fields=["name", "item_name", "item_name_ar", "section_name", "sort_order"],
        order_by="sort_order asc, creation asc",
    )


class VehicleInspectionLog(Document):
    def before_insert(self):
        if not self.inspection_log_no:
            self.inspection_log_no = make_code(self.doctype)
        if not self.items:
            self.auto_fill_items_if_needed()

    def validate(self):
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Draft")
        self.validate_required_fields()
        self.validate_links()
        self.validate_values()
        self.sync_result_fields()

    def validate_required_fields(self):
        for label, value in {
            "Base Company": self.base_company,
            "Vehicle": self.vehicle,
            "Inspection Date": self.inspection_date,
        }.items():
            if not value:
                frappe.throw(_("{0} is required.").format(label))
        if not self.items:
            frappe.throw(_("Inspection Items are required."))

    def validate_links(self):
        ensure_same_company(self.base_company, "Vehicle", self.vehicle)
        if self.inspector:
            ensure_staff_same_company(self.inspector, self.base_company)
        if self.trip:
            ensure_same_company(self.base_company, "Trip", self.trip)
            trip_vehicle = frappe.db.get_value("Trip", self.trip, "vehicle")
            if trip_vehicle and trip_vehicle != self.vehicle:
                frappe.throw(_("Trip vehicle must match inspection vehicle."))
        if not self.vehicle_type:
            self.vehicle_type = frappe.db.get_value("Vehicle", self.vehicle, "vehicle_type")

    def validate_values(self):
        if self.odometer_reading is not None and flt(self.odometer_reading) < 0:
            frappe.throw(_("Odometer Reading cannot be negative."))
        validate_child_row_uniqueness(self.items or [], lambda row: (clean_text(row.item_name).lower(),), "inspection item")
        for row in self.items or []:
            row.category = clean_text(row.category)
            row.item_name = clean_text(row.item_name)
            row.item_name_ar = clean_text(row.item_name_ar)
            row.remarks = clean_long_text(row.remarks)

    def sync_result_fields(self):
        results = {row.result for row in self.items or []}
        if "Not OK" in results:
            self.overall_result = "Failed"
        elif "Needs Attention" in results:
            self.overall_result = "Attention Required"
        else:
            self.overall_result = "Passed"

    def auto_fill_items_if_needed(self):
        if not frappe.db.exists("DocType", "Vehicle Inspection Checklist Item"):
            return
        for row in get_active_checklist_rows(self.vehicle_type):
            self.append(
                "items",
                {
                    "category": row.section_name,
                    "checklist_item": row.name,
                    "item_name": row.item_name,
                    "item_name_ar": row.item_name_ar,
                    "result": "OK",
                    "sort_order": row.sort_order,
                },
            )
