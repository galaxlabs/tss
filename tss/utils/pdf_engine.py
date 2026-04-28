from __future__ import annotations

import frappe
from frappe.core.doctype.file.file import create_new_folder
from frappe.utils.file_manager import save_file

from tss.utils.chrome_pdf import get_pdf as chrome_get_pdf


def generate_pdf(doctype: str, name: str, print_format: str | None = None, no_letterhead: int = 0) -> bytes:
    html = frappe.get_print(doctype, name, print_format=print_format, no_letterhead=no_letterhead)
    return chrome_get_pdf(html, options={"page-size": "A4"})


def save_pdf(
    pdf_bytes: bytes,
    doctype: str,
    name: str,
    folder: str = "Home/Attachments",
    public: bool = False,
):
    ensure_folder(folder)
    file_doc = save_file(
        fname=f"{doctype}-{name}.pdf".replace(" ", "-").replace("/", "-"),
        content=pdf_bytes,
        dt=doctype,
        dn=name,
        folder=folder,
        is_private=0 if public else 1,
    )
    return file_doc.file_url, file_doc.file_name, file_doc.name


def ensure_folder(folder: str):
    if not folder or folder == "Home":
        return
    if frappe.db.exists("File", {"file_url": folder}) or frappe.db.exists("File", folder):
        return

    parent_folder = "Home"
    folder_name = folder
    if "/" in folder:
        parent_folder, folder_name = folder.rsplit("/", 1)
    create_new_folder(folder_name, parent_folder)
