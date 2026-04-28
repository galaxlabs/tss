__version__ = "0.0.1"


def override_frappe_get_pdf(bootinfo=None):
    import frappe
    import frappe.utils.pdf as frappe_pdf

    if not getattr(frappe.local, "site", None):
        return
    if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
        return

    try:
        from tss.utils.chrome_pdf import get_pdf as chrome_get_pdf
        frappe_pdf.get_pdf = chrome_get_pdf
        frappe.logger().info("tss: Overridden frappe.utils.pdf.get_pdf with Chrome-based generator")
    except Exception:
        frappe.logger().exception("tss: Failed to override frappe.utils.pdf.get_pdf")
