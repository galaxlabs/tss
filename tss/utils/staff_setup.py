from __future__ import annotations

import frappe


def apply_transport_staff_defaults(doc, method=None):
    """Default TSS Staff records into the linked ERP/User flow on creation."""

    if not doc.is_new():
        return

    if frappe.db.exists("DocType", "Employee"):
        doc.create_employee = 1

    if (doc.email or "").strip():
        doc.can_login = 1
        doc.create_user = 1


def ensure_transport_staff_links(doc, method=None):
    if doc.get("create_employee") and not doc.get("linked_employee"):
        doc.create_employee_if_available()


def backfill_transport_staff_links(dry_run: int | bool = 1) -> dict[str, int | bool]:
    dry_run = bool(int(dry_run))
    result = {
        "dry_run": dry_run,
        "staff_checked": 0,
        "employee_requested": 0,
        "user_requested": 0,
        "skipped_user_no_email": 0,
    }

    for staff_name in frappe.get_all("Staff", pluck="name"):
        doc = frappe.get_doc("Staff", staff_name)
        result["staff_checked"] += 1

        changed = False
        employee_link_missing = _employee_link_missing(doc)
        if frappe.db.exists("DocType", "Employee") and employee_link_missing:
            result["employee_requested"] += 1
            if not dry_run:
                if doc.get("linked_employee"):
                    doc.linked_employee = ""
                doc.create_employee = 1
                changed = True

        if not doc.get("linked_user"):
            if (doc.email or "").strip():
                result["user_requested"] += 1
                if not dry_run:
                    doc.can_login = 1
                    doc.create_user = 1
                    changed = True
            else:
                result["skipped_user_no_email"] += 1

        if changed:
            doc.save(ignore_permissions=True)

    if not dry_run:
        frappe.db.commit()

    return result


def _employee_link_missing(doc) -> bool:
    linked_employee = doc.get("linked_employee")
    if not linked_employee or not frappe.db.exists("Employee", linked_employee):
        return True

    employee_number = frappe.db.get_value("Employee", linked_employee, "employee_number")
    return bool(employee_number and employee_number != (doc.staff_id or doc.name))
