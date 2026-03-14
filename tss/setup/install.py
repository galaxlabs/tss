from __future__ import annotations

import frappe

def after_install():
    ensure_settings()


def after_migrate():
    ensure_settings()


def ensure_settings():
    if not frappe.db.exists("Transport Settings", "Transport Settings"):
        frappe.get_doc({"doctype": "Transport Settings"}).insert(ignore_permissions=True)
