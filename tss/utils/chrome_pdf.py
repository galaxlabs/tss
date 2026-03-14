from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile

import frappe
from frappe.utils import get_url
from frappe.utils.pdf import prepare_options
from pypdf import PdfReader, PdfWriter

URLS_NOT_HTTP_TAG_PATTERN = re.compile(r'(href|src)([\s]*=[\s]*[\'"]?)((?!http)[^\'">]+)([\'"]?)')
URL_NOT_HTTP_NOTATION_PATTERN = re.compile(r'(:[\s]?url)(\([\'"]?)((?!http)[^\'">]+)([\'"]?\))')


def scrub_urls(html: str) -> str:
    return expand_relative_urls(html)


def expand_relative_urls(html: str) -> str:
    base_url = get_url().rstrip("/")

    urls_http_tag_pattern = re.compile(
        r'(href|src)([\s]*=[\s]*[\'"]?)((?:{0})[^\'">]+)([\'"]?)'.format(
            re.escape(base_url.replace("https://", "http://"))
        )
    )
    url_http_notation_pattern = re.compile(
        r'(:[\s]?url)(\([\'"]?)((?:{0})[^\'">]+)([\'"]?\))'.format(
            re.escape(base_url.replace("https://", "http://"))
        )
    )

    def _expand_relative_urls(match):
        parts = list(match.groups())
        url_value = parts[2]

        if url_value.startswith(("data:", "mailto:", "tel:")):
            return "".join(parts)

        if not url_value.startswith(base_url):
            if not url_value.startswith("/"):
                url_value = "/" + url_value
            url_value = base_url + url_value

        parts[2] = url_value
        if frappe.session and getattr(frappe.session, "sid", None) and hasattr(frappe.local, "request"):
            separator = "&" if "?" in parts[-2] else "?"
            parts[-2] += f"{separator}sid={frappe.session.sid}"

        return "".join(parts)

    html = urls_http_tag_pattern.sub(_expand_relative_urls, html)
    html = URLS_NOT_HTTP_TAG_PATTERN.sub(_expand_relative_urls, html)
    html = URL_NOT_HTTP_NOTATION_PATTERN.sub(_expand_relative_urls, html)
    html = url_http_notation_pattern.sub(_expand_relative_urls, html)
    return html


def get_pdf(html: str, options: dict | None = None, output: PdfWriter | None = None):
    options = options or {}
    pdf_file_path = f"/tmp/{frappe.generate_hash()}.pdf"
    html = scrub_urls(html)
    html, options = prepare_options(html, options)
    html = _inject_page_style(html, options)

    chrome_binary = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome_binary:
        frappe.throw("Chrome or Chromium is required for Arabic-safe PDF generation.")

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".html", delete=True, encoding="utf-8") as html_file:
        html_file.write(html)
        html_file.seek(0)
        subprocess.run(
            [
                chrome_binary,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={pdf_file_path}",
                html_file.name,
            ],
            check=True,
            shell=False,
        )
        with open(pdf_file_path, "rb") as pdf_file:
            content = pdf_file.read()

    os.remove(pdf_file_path)
    reader = PdfReader(io.BytesIO(content))

    if output:
        output.append_pages_from_reader(reader)
        return output

    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    if options.get("password"):
        writer.encrypt(options["password"])

    return _get_file_data_from_writer(writer)


def _inject_page_style(html: str, options: dict) -> str:
    additional_style = ""
    if options.get("page-height") or options.get("page-width"):
        additional_style += (
            "<style>@page {"
            f"size: {options.get('page-width')}mm {options.get('page-height')}mm;"
            "}</style>"
        )
    elif options.get("page-size"):
        size = get_page_size(options.get("page-size"))
        page_size = f"{size['width']}in {size['height']}in" if size else options.get("page-size")
        additional_style += f"<style>@page {{ size: {page_size}; }}</style>"

    margin_parts = [
        f"{key}: {options.get(key)};"
        for key in ("margin-top", "margin-bottom", "margin-left", "margin-right")
        if options.get(key)
    ]
    if margin_parts:
        additional_style += f"<style>@page {{ {' '.join(margin_parts)} }}</style>"

    return additional_style + html


def _get_file_data_from_writer(writer_obj: PdfWriter) -> bytes:
    stream = io.BytesIO()
    writer_obj.write(stream)
    stream.seek(0)
    return stream.read()


def get_page_size(page_size: str):
    paper_sizes = {
        "A4": {"width": 8.3, "height": 11.7},
        "A5": {"width": 5.8, "height": 8.3},
        "Letter": {"width": 8.5, "height": 11.0},
        "Legal": {"width": 8.5, "height": 14.0},
    }
    return paper_sizes.get(page_size)
