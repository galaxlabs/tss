from __future__ import annotations

import frappe

from tss.utils.pdf_engine import generate_pdf, save_pdf


def create_trip_pdf(doc, event=None):
    if doc.doctype != "Trip" or not doc.name:
        return

    existing = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Trip",
            "attached_to_name": doc.name,
            "is_private": 0,
            "file_name": ["like", f"%{doc.name}%"],
        },
        limit=1,
        pluck="name",
    )
    if existing:
        return

    pdf_bytes = generate_pdf("Trip", doc.name, print_format="Trip Manifest")
    save_pdf(pdf_bytes, "Trip", doc.name, folder="Home/Trip PDFs", public=True)
