# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


SECTION_ORDER = [
    "Dashboard Indicators",
    "External Inspection",
    "Safety And Security Tools",
]


def get_active_checklist_rows():
    rows = frappe.get_all(
        "Vehicle Inspection Checklist Item",
        filters={"is_active": 1},
        fields=["name", "item_code", "item_name", "item_name_ar", "section_name", "sort_order"],
        order_by="sort_order asc, creation asc",
    )
    return rows


class VehicleInspectionLog(Document):
    def before_insert(self):
        self.set_inspection_log_no()
        self.prepare_revision_metadata()
        self.auto_fill_items_if_needed()

    def validate(self):
        self.set_default_values()
        self.sync_display_fields()
        self.validate_required_fields()
        self.validate_duplicate_policy()
        self.validate_values()
        self.sync_overall_result()
        self.sync_print_ready()

    def set_default_values(self):
        if not self.naming_series:
            self.naming_series = "VIL-.YYYY.-.#####"

        if not self.revision_no:
            self.revision_no = 1

        if self.is_latest_revision is None:
            self.is_latest_revision = 1

        if self.print_ready is None:
            self.print_ready = 1

        if not self.declaration:
            self.declaration = "I confirm the above inspection is correct."

    def set_inspection_log_no(self):
        if not self.inspection_log_no:
            self.inspection_log_no = frappe.model.naming.make_autoname(self.naming_series or "VIL-.YYYY.-.#####")

    def sync_display_fields(self):
        if self.driver and not self.driver_name_text:
            self.driver_name_text = self.driver

        if self.supervisor and not self.supervisor_name_text:
            self.supervisor_name_text = self.supervisor

        if self.vehicle and not self.vehicle_type:
            vehicle_type = frappe.db.get_value("Vehicle", self.vehicle, "vehicle_type")
            if vehicle_type:
                self.vehicle_type = vehicle_type

    def validate_required_fields(self):
        if not self.base_company:
            frappe.throw(_("Base Company is required."))

        if not self.inspection_date:
            frappe.throw(_("Inspection Date is required."))

        if not self.driver:
            frappe.throw(_("Driver is required."))

        if not self.vehicle:
            frappe.throw(_("Vehicle is required."))

        if not self.items:
            frappe.throw(_("Checklist Items are required."))

    def validate_duplicate_policy(self):
        if self.previous_revision:
            return

        existing_latest = frappe.db.get_value(
            "Vehicle Inspection Log",
            {
                "vehicle": self.vehicle,
                "inspection_date": self.inspection_date,
                "is_latest_revision": 1,
                "name": ["!=", self.name or ""],
            },
            ["name", "revision_no"],
            as_dict=1,
        )

        if existing_latest:
            frappe.throw(
                _("A latest inspection log already exists for this vehicle and date. Please create a revision from the existing log: {0}").format(existing_latest.name)
            )

    def validate_values(self):
        if self.odometer_reading is not None and flt(self.odometer_reading) < 0:
            frappe.throw(_("Odometer Reading cannot be negative."))

        allowed = {"Fit", "Needs Attention", "Not Fit"}
        for row in self.items:
            if row.status not in allowed:
                frappe.throw(_("Invalid item status in checklist row."))

    def sync_overall_result(self):
        statuses = [row.status for row in self.items if row.status]

        if "Not Fit" in statuses:
            self.overall_result = "Not Fit"
        elif "Needs Attention" in statuses:
            self.overall_result = "Needs Attention"
        else:
            self.overall_result = "Fit"

    def sync_print_ready(self):
        self.print_ready = 1

    def auto_fill_items_if_needed(self):
        if self.items:
            return

        if cint(self.auto_fill_checklist or 0) != 1:
            return

        for row in get_active_checklist_rows():
            self.append(
                "items",
                {
                    "section_name": row.section_name,
                    "checklist_item": row.name,
                    "item_name": row.item_name,
                    "item_name_ar": row.item_name_ar,
                    "status": "Fit",
                    "sort_order": row.sort_order or 0,
                },
            )

    def prepare_revision_metadata(self):
        if not self.previous_revision:
            self.revision_no = self.revision_no or 1
            self.is_latest_revision = 1
            return

        previous_doc = frappe.get_doc("Vehicle Inspection Log", self.previous_revision)

        if previous_doc.vehicle != self.vehicle:
            frappe.throw(_("Revision vehicle must match previous revision vehicle."))

        if str(previous_doc.inspection_date) != str(self.inspection_date):
            frappe.throw(_("Revision date must match previous revision date."))

        self.revision_no = cint(previous_doc.revision_no) + 1
        self.base_company = self.base_company or previous_doc.base_company
        self.driver = self.driver or previous_doc.driver
        self.vehicle = self.vehicle or previous_doc.vehicle
        self.vehicle_type = self.vehicle_type or previous_doc.vehicle_type

    def on_update_after_submit(self):
        self.mark_previous_revisions_not_latest()

    def after_insert(self):
        self.mark_previous_revisions_not_latest()

    def mark_previous_revisions_not_latest(self):
        if not self.vehicle or not self.inspection_date:
            return

        frappe.db.sql(
            """
            update `tabVehicle Inspection Log`
            set is_latest_revision = 0
            where vehicle = %s
              and inspection_date = %s
              and name != %s
            """,
            (self.vehicle, self.inspection_date, self.name),
        )

        frappe.db.set_value("Vehicle Inspection Log", self.name, "is_latest_revision", 1, update_modified=False)

    def make_revision(self):
        new_doc = frappe.copy_doc(self)
        new_doc.previous_revision = self.name
        new_doc.revision_no = cint(self.revision_no) + 1
        new_doc.is_latest_revision = 1
        new_doc.inspection_log_no = None
        return new_doc

    def as_api_dict(self):
        return {
            "name": self.name,
            "inspection_log_no": self.inspection_log_no,
            "revision_no": self.revision_no,
            "base_company": self.base_company,
            "inspection_date": self.inspection_date,
            "is_latest_revision": self.is_latest_revision,
            "driver": self.driver,
            "driver_name_text": self.driver_name_text,
            "vehicle": self.vehicle,
            "vehicle_type": self.vehicle_type,
            "supervisor": self.supervisor,
            "supervisor_name_text": self.supervisor_name_text,
            "trip": self.trip,
            "odometer_reading": self.odometer_reading,
            "overall_result": self.overall_result,
            "print_ready": self.print_ready,
            "previous_revision": self.previous_revision,
            "revision_reason": self.revision_reason,
            "overall_notes": self.overall_notes,
            "declaration": self.declaration,
            "driver_signature": self.driver_signature,
            "supervisor_signature": self.supervisor_signature,
            "items": [
                {
                    "section_name": row.section_name,
                    "checklist_item": row.checklist_item,
                    "item_name": row.item_name,
                    "item_name_ar": row.item_name_ar,
                    "status": row.status,
                    "notes": row.notes,
                    "sort_order": row.sort_order,
                }
                for row in self.items
            ],
        }


@frappe.whitelist()
def get_default_vehicle_inspection_checklist():
    return get_active_checklist_rows()


@frappe.whitelist()
def make_vehicle_inspection_log_revision(source_name: str):
    source = frappe.get_doc("Vehicle Inspection Log", source_name)
    revised = source.make_revision()
    return revised.as_dict()