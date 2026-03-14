from __future__ import annotations

import io

import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils import cint, flt, get_datetime, get_url, getdate, now_datetime

from tss.utils.transport_naming import clean_text, normalize_code

try:
    from hijri_converter import Gregorian
except Exception:
    Gregorian = None

try:
    import pyqrcode
except Exception:
    pyqrcode = None


def normalize_identifier(value: str | None) -> str:
    return normalize_code(value, keep_dash=False)


def normalize_plate(value: str | None) -> str:
    return normalize_code(value)


def ensure_positive(value, label: str, allow_zero: bool = False):
    number = flt(value)
    if allow_zero and number < 0:
        frappe.throw(_("{0} cannot be negative.").format(label))
    if not allow_zero and number <= 0:
        frappe.throw(_("{0} must be greater than zero.").format(label))


def ensure_same_company(base_company: str, linked_doctype: str, linked_name: str, fieldname: str = "base_company"):
    if not (base_company and linked_name and frappe.db.exists(linked_doctype, linked_name)):
        return
    linked_company = frappe.db.get_value(linked_doctype, linked_name, fieldname)
    if linked_company and linked_company != base_company:
        frappe.throw(_("{0} must belong to Base Company {1}.").format(linked_doctype, base_company))


def ensure_company_is_active(base_company: str):
    if not base_company or not frappe.db.exists("Base Company", base_company):
        return
    if frappe.db.get_value("Base Company", base_company, "status") != "Active":
        frappe.throw(_("Base Company {0} must be Active.").format(base_company))


def ensure_staff_is_driver(staff_name: str, base_company: str | None = None):
    if not staff_name or not frappe.db.exists("Staff", staff_name):
        return
    staff_type, is_active, staff_company = frappe.db.get_value(
        "Staff", staff_name, ["staff_type", "is_active", "base_company"]
    )
    if clean_text(staff_type) != "Driver":
        frappe.throw(_("Staff {0} must be a Driver.").format(staff_name))
    if not cint(is_active):
        frappe.throw(_("Driver {0} must be active.").format(staff_name))
    if base_company and staff_company and staff_company != base_company:
        frappe.throw(_("Driver {0} must belong to Base Company {1}.").format(staff_name, base_company))


def ensure_staff_same_company(staff_name: str, base_company: str):
    if not staff_name or not frappe.db.exists("Staff", staff_name):
        return
    ensure_same_company(base_company, "Staff", staff_name)
    if not cint(frappe.db.get_value("Staff", staff_name, "is_active")):
        frappe.throw(_("Staff {0} must be active.").format(staff_name))


def validate_datetime_order(start, end, start_label: str, end_label: str):
    if start and end and get_datetime(end) < get_datetime(start):
        frappe.throw(_("{0} cannot be before {1}.").format(end_label, start_label))


def build_hijri_date(value) -> str:
    if not value or not Gregorian:
        return ""
    g = getdate(value)
    hijri = Gregorian(g.year, g.month, g.day).to_hijri()
    return f"{hijri.year:04d}-{hijri.month:02d}-{hijri.day:02d}"


def build_qr_data_uri(payload: str) -> str:
    if not payload or not pyqrcode:
        return ""
    return "data:image/png;base64," + pyqrcode.create(payload).png_as_base64_str(scale=6)


def save_qr_image_file(payload: str, doctype: str, docname: str, fieldname: str = "qr_code") -> str:
    if not payload or not pyqrcode or not doctype or not docname:
        return ""

    png_buffer = io.BytesIO()
    pyqrcode.create(payload).png(png_buffer, scale=6)
    file_doc = save_file(
        f"{doctype.lower().replace(' ', '-')}-{docname}-qr.png",
        png_buffer.getvalue(),
        doctype,
        docname,
        is_private=0,
        df=fieldname,
    )
    return file_doc.file_url


def build_public_url(*parts: str | None) -> str:
    clean_parts = [str(part).strip("/") for part in parts if part]
    return "/".join([get_url().rstrip("/"), *clean_parts])


def validate_child_row_uniqueness(rows, key_builder, label: str):
    seen = set()
    for row in rows or []:
        key = key_builder(row)
        if key in seen and any(key):
            frappe.throw(_("Duplicate {0} found at row {1}.").format(label, row.idx))
        seen.add(key)


def sync_verification_fields(row):
    if getattr(row, "verified", 0):
        if not getattr(row, "verified_by", None):
            row.verified_by = frappe.session.user
        if not getattr(row, "verified_on", None):
            row.verified_on = now_datetime()
    else:
        row.verified_by = None
        row.verified_on = None
