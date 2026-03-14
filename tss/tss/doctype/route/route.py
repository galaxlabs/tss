from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
import requests

from tss.utils.transport_naming import clean_long_text, clean_text, make_code
from tss.utils.transport_validation import validate_child_row_uniqueness


class Route(Document):
    def before_insert(self):
        if not self.route_code:
            self.route_code = self._build_route_code()

    def validate(self):
        self.route_name = clean_text(self.route_name)
        self.route_name_ar = clean_text(self.route_name_ar)
        self.source = clean_text(self.source)
        self.destination = clean_text(self.destination)
        self.notes = clean_long_text(self.notes)
        self.status = clean_text(self.status or "Draft")
        self.is_active = 1 if self.status == "Active" else 0

        if not self.source or not self.destination:
            frappe.throw(_("Source and Destination are required."))
        if self.source == self.destination:
            frappe.throw(_("Source and Destination cannot be the same."))
        if not self.route_code:
            self.route_code = self._build_route_code()
        self.build_route_identity()
        if flt(self.distance_km) < 0:
            frappe.throw(_("Distance KM cannot be negative."))
        if cint(self.estimated_duration_minutes) < 0:
            frappe.throw(_("Estimated Duration Minutes cannot be negative."))

        rows = self.get("route_stops") or []
        validate_child_row_uniqueness(rows, lambda row: (cint(row.sequence_no),), "route stop sequence")
        validate_child_row_uniqueness(rows, lambda row: (clean_text(row.stop_name).lower(),), "route stop")
        for row in rows:
            row.stop_name = clean_text(row.stop_name)
            row.stop_name_ar = clean_text(row.stop_name_ar)
            row.notes = clean_long_text(row.notes)

    def build_route_identity(self):
        readable_name = " -> ".join([part for part in [self.source, self.destination] if part])
        if not self.route_name:
            self.route_name = readable_name

        title_parts = []
        if self.route_code:
            title_parts.append(self.route_code)
        if readable_name:
            title_parts.append(readable_name)
        self.route_title = " | ".join(title_parts) if title_parts else self.route_name

    def _build_route_code(self) -> str:
        from_code = _make_city_code(self.source)
        to_code = _make_city_code(self.destination)
        base_code = f"{from_code}-TO-{to_code}"
        return _make_unique_route_code(base_code, self.name)


def _get_google_maps_api_key() -> str:
    api_key = frappe.conf.get("google_maps_api_key")
    if api_key:
        return api_key

    if frappe.db.exists("DocType", "Google Map Settings"):
        api_key = frappe.db.get_single_value("Google Map Settings", "api_key")
        if api_key:
            return api_key

    if frappe.db.exists("DocType", "Google Settings"):
        api_key = frappe.db.get_single_value("Google Settings", "api_key")
        if api_key:
            return api_key

    frappe.throw(_("Google Maps API key not found. Add it in site_config.json or Google Map Settings."))


def _clean_place_name(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    return value


def _make_city_code(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9 ]", " ", clean_text(value or ""))
    text = re.sub(r"\s+", " ", text).strip().upper()
    if not text:
        return "UNK"
    joined = text.replace(" ", "")
    if len(joined) >= 3:
        return joined[:3]
    return (joined + "XXX")[:3]


def _make_unique_route_code(base_code: str, current_name: str | None = None) -> str:
    candidate = base_code
    counter = 2
    while True:
        existing = frappe.db.get_value("Route", {"route_code": candidate}, "name")
        if not existing or existing == current_name:
            return candidate
        candidate = f"{base_code}-{counter}"
        counter += 1


def _parse_distance_km(distance_text: str) -> float:
    text = (distance_text or "").lower().replace(",", "").strip()
    if " km" in text:
        return float(text.replace(" km", ""))
    if " m" in text:
        return float(text.replace(" m", "")) / 1000
    return float("".join(ch for ch in text if ch.isdigit() or ch == ".") or 0)


@frappe.whitelist()
def get_google_maps_config():
    return {"api_key": _get_google_maps_api_key(), "country": "sa"}


@frappe.whitelist()
def fetch_distance_for_route(route_name: str):
    if not route_name:
        frappe.throw(_("Route name is required."))

    route = frappe.get_doc("Route", route_name)
    route.check_permission("write")

    if not route.source or not route.destination:
        frappe.throw(_("Please set Source and Destination first."))

    api_key = _get_google_maps_api_key()
    response = requests.get(
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        params={
            "origins": route.source,
            "destinations": route.destination,
            "key": api_key,
            "region": "sa",
        },
        timeout=20,
    )
    data = response.json()

    if data.get("status") != "OK":
        frappe.throw(_("Google API Error: {0}").format(data.get("status")))

    element = (((data.get("rows") or [{}])[0]).get("elements") or [{}])[0]
    if element.get("status") != "OK":
        frappe.throw(_("Distance Matrix Error: {0}").format(element.get("status")))

    distance_km = _parse_distance_km((element.get("distance") or {}).get("text"))
    duration_seconds = cint((element.get("duration") or {}).get("value"))
    duration_minutes = max(1, cint(round(duration_seconds / 60))) if duration_seconds else 0

    route.db_set("distance_km", distance_km, update_modified=False)
    route.db_set("estimated_duration_minutes", duration_minutes, update_modified=False)
    if not route.route_name:
        route.db_set("route_name", f"{_clean_place_name(route.source)} - {_clean_place_name(route.destination)}", update_modified=False)

    return {
        "route": route.name,
        "route_code": route.route_code,
        "distance_km": distance_km,
        "estimated_duration_minutes": duration_minutes,
    }


def get_or_create_reverse_route_name(route_name: str) -> str:
    route = frappe.get_doc("Route", route_name)
    reverse_name = frappe.db.get_value("Route", {"source": route.destination, "destination": route.source}, "name")
    if reverse_name:
        return reverse_name

    reverse_doc = frappe.get_doc(
        {
            "doctype": "Route",
            "route_name": f"{route.destination} - {route.source}",
            "route_name_ar": route.route_name_ar,
            "source": route.destination,
            "destination": route.source,
            "route_type": route.route_type,
            "status": route.status or "Active",
            "distance_km": route.distance_km,
            "estimated_duration_minutes": route.estimated_duration_minutes,
            "default_vehicle_type": route.default_vehicle_type,
            "notes": route.notes,
            "route_stops": [
                {
                    "sequence_no": row.idx,
                    "stop_name": row.stop_name,
                    "stop_name_ar": row.stop_name_ar,
                    "stop_type": getattr(row, "stop_type", None),
                    "notes": row.notes,
                }
                for row in reversed(route.get("route_stops") or [])
            ],
        }
    )
    reverse_doc.insert(ignore_permissions=True)
    return reverse_doc.name


@frappe.whitelist()
def get_or_create_reverse_route(route_name: str):
    if not route_name:
        frappe.throw(_("Route is required."))
    return {"route": get_or_create_reverse_route_name(route_name)}
