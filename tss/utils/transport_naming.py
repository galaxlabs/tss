from __future__ import annotations

import re

import frappe
from frappe.utils import getdate


SERIES_MAP = {
    "Vehicle Type": "TVT-.YYYY.-.#####",
    "Vehicle Make": "TVM-.YYYY.-.#####",
    "Vehicle Model": "TMD-.YYYY.-.#####",
    "Vehicle Category": "VCG-.YYYY.-.#####",
    "Route": "RTE-.YYYY.-.#####",
    "Pricing": "PRC-.YYYY.-.#####",
    "Trip": "TRP-.YYYY.-.#####",
    "Trip Booking": "TBK-.YYYY.-.#####",
    "Vehicle Assignment": "VAS-.YYYY.-.#####",
    "Vehicle Inspection": "VIN-.YYYY.-.#####",
}


def make_code(doctype: str) -> str:
    return frappe.model.naming.make_autoname(SERIES_MAP.get(doctype, "TSS-.YYYY.-.#####"))


def make_readable_code(doctype: str, source_text: str | None, fieldname: str, fallback: str = "CODE") -> str:
    base = normalize_code(source_text, keep_dash=False)[:8] or fallback
    candidate = base
    counter = 2

    while frappe.db.exists(doctype, {fieldname: candidate}):
        suffix = str(counter)
        candidate = f"{base[: max(1, 8 - len(suffix))]}{suffix}"
        counter += 1

    return candidate


def make_trip_code(trip_date=None) -> str:
    trip_date = getdate(trip_date) if trip_date else getdate()
    series = f"TRP-{trip_date.year}-{trip_date.month:02d}-.#####"
    return frappe.model.naming.make_autoname(series)


def normalize_code(value: str | None, keep_dash: bool = True) -> str:
    value = (value or "").strip().upper()
    value = re.sub(r"[^A-Z0-9-]" if keep_dash else r"[^A-Z0-9]", "", value)
    value = re.sub(r"-{2,}", "-", value)
    return value


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def clean_long_text(value: str | None) -> str:
    value = (value or "").strip()
    value = re.sub(r"[ \t]+", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value)
