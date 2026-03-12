# Copyright (c) 2026, Galaxy Labs and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime


class Route(Document):
    def before_insert(self):
        self.set_default_values()
        self.prepare_route_code()

    def before_validate(self):
        self.prepare_route_code()

    def validate(self):
        self.normalize_fields()
        self.prepare_city_codes()
        self.build_route_title()
        self.validate_basic_fields()
        self.validate_return_route()
        self.sync_status_flags()
        self.set_duration_text()

    # -------------------------
    # Setup
    # -------------------------
    def set_default_values(self):
        if not self.status:
            self.status = "Draft"

        if self.is_active is None:
            self.is_active = 1

        if not self.avg_speed_kmph:
            self.avg_speed_kmph = 100

        if not self.distance_unit:
            self.distance_unit = "KM"

    def normalize_fields(self):
        self.route_code = self.clean_code(self.route_code)
        self.from_city = (self.from_city or "").strip()
        self.to_city = (self.to_city or "").strip()
        self.from_place_full = (self.from_place_full or "").strip()
        self.to_place_full = (self.to_place_full or "").strip()
        self.description = (self.description or "").strip()
        self.description_ar = (self.description_ar or "").strip()
        self.remarks = (self.remarks or "").strip()

    # -------------------------
    # Code / title helpers
    # -------------------------
    def prepare_route_code(self):
        if self.route_code:
            self.route_code = self.clean_code(self.route_code)
            return

        from_code = self.make_city_code(self.from_city)
        to_code = self.make_city_code(self.to_city)
        base_code = f"{from_code}-TO-{to_code}"
        self.route_code = self.make_unique_route_code(base_code)

    def prepare_city_codes(self):
        self.from_city_code = self.make_city_code(self.from_city)
        self.to_city_code = self.make_city_code(self.to_city)

    def build_route_title(self):
        if self.from_city and self.to_city:
            self.route_title = f"{self.from_city} → {self.to_city}"
        else:
            self.route_title = self.route_code

    def set_duration_text(self):
        minutes = cint(self.duration_minutes)
        if minutes > 0:
            hours = minutes // 60
            mins = minutes % 60
            if hours and mins:
                self.duration_text = f"{hours}h {mins}m"
            elif hours:
                self.duration_text = f"{hours}h"
            else:
                self.duration_text = f"{mins}m"
        else:
            self.duration_text = ""

    # -------------------------
    # Validation
    # -------------------------
    def validate_basic_fields(self):
        if not self.from_city:
            frappe.throw(_("From City is required."))

        if not self.to_city:
            frappe.throw(_("To City is required."))

        if self.normalize_city_name(self.from_city) == self.normalize_city_name(self.to_city):
            frappe.throw(_("From City and To City cannot be the same."))

        if self.from_place_full and self.to_place_full:
            if self.from_place_full.strip().lower() == self.to_place_full.strip().lower():
                frappe.throw(_("From Place and To Place cannot be the same."))

        if self.distance is not None and flt(self.distance) < 0:
            frappe.throw(_("Distance cannot be negative."))

        if self.duration_minutes is not None and cint(self.duration_minutes) < 0:
            frappe.throw(_("Duration Minutes cannot be negative."))

        if self.avg_speed_kmph is not None and flt(self.avg_speed_kmph) < 0:
            frappe.throw(_("Avg Speed cannot be negative."))

    def validate_return_route(self):
        if self.return_route and self.return_route == self.name:
            frappe.throw(_("Return Route cannot be the same route."))

        if self.has_return and not self.return_route:
            # allowed for now; user may create later
            return

        if self.return_route and frappe.db.exists("Route", self.return_route):
            rr = frappe.get_doc("Route", self.return_route)
            if rr.return_route and rr.return_route != self.name:
                # soft safety only
                pass

    def sync_status_flags(self):
        if self.status == "Active":
            self.is_active = 1
        elif self.status == "Inactive":
            self.is_active = 0
        elif not cint(self.is_active):
            self.status = "Inactive"

    # -------------------------
    # Public actions
    # -------------------------
    def activate(self):
        self.check_permission("write")
        self.status = "Active"
        self.is_active = 1
        self.save()

    def deactivate(self):
        self.check_permission("write")
        self.status = "Inactive"
        self.is_active = 0
        self.save()

    def fetch_distance_and_update(self):
        if not self.from_city or not self.to_city:
            frappe.throw(_("Please set From City and To City first."))

        api_key = _get_api_key()

        base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": self.from_city,
            "destinations": self.to_city,
            "key": api_key,
            "region": "sa",
        }

        res = requests.get(base_url, params=params, timeout=20)
        data = res.json()

        if data.get("status") != "OK":
            frappe.throw(_("Google API Error: {0}").format(data.get("status")))

        el = data["rows"][0]["elements"][0]
        if el.get("status") != "OK":
            frappe.throw(_("Distance Matrix Error: {0}").format(el.get("status")))

        distance_text = el["distance"]["text"]
        distance_km = _parse_distance_km(distance_text)

        avg_speed = flt(self.avg_speed_kmph or 0) or 100.0
        duration_minutes = max(1, int(round((distance_km / avg_speed) * 60)))

        self.distance = distance_km
        self.distance_unit = "KM"
        self.duration_minutes = duration_minutes
        self.distance_source = "Google Maps"
        self.google_maps_last_sync_on = now_datetime()
        self.from_place_full = self.get_place_name(self.from_city, api_key)
        self.to_place_full = self.get_place_name(self.to_city, api_key)
        self.set_duration_text()
        self.save()

        return {
            "route": self.name,
            "route_code": self.route_code,
            "distance": self.distance,
            "distance_unit": self.distance_unit,
            "duration_minutes": self.duration_minutes,
            "duration_text": self.duration_text,
            "avg_speed_used": avg_speed,
        }

    # -------------------------
    # API helper
    # -------------------------
    def as_api_dict(self) -> dict:
        return {
            "name": self.name,
            "route_code": self.route_code,
            "route_title": self.route_title,
            "status": self.status,
            "is_active": self.is_active,
            "base_company": self.base_company,
            "is_system_generated": self.is_system_generated,
            "from_city": self.from_city,
            "from_city_code": self.from_city_code,
            "from_place_full": self.from_place_full,
            "to_city": self.to_city,
            "to_city_code": self.to_city_code,
            "to_place_full": self.to_place_full,
            "distance": self.distance,
            "distance_unit": self.distance_unit,
            "duration_minutes": self.duration_minutes,
            "duration_text": self.duration_text,
            "avg_speed_kmph": self.avg_speed_kmph,
            "distance_source": self.distance_source,
            "google_maps_last_sync_on": self.google_maps_last_sync_on,
            "has_return": self.has_return,
            "return_route": self.return_route,
            "allow_dynamic_pricing": self.allow_dynamic_pricing,
            "show_on_website": self.show_on_website,
            "description": self.description,
            "description_ar": self.description_ar,
            "remarks": self.remarks,
        }

    # -------------------------
    # Static helpers
    # -------------------------
    @staticmethod
    def normalize_city_name(city: str) -> str:
        city = (city or "").strip().lower()
        city = city.replace("-", " ")
        city = re.sub(r"\s+", " ", city)

        aliases = {
            "jidda": "jeddah",
            "jiddah": "jeddah",
            "medina": "madinah",
            "al madinah al munawwarah": "madinah",
            "madinah al munawwarah": "madinah",
            "mecca": "makkah",
            "makkah al mukarramah": "makkah",
            "al khobar": "khobar",
            "hafar al batin": "hafar",
            "king abdulaziz international airport": "jeddah",
            "prince mohammad bin abdulaziz international airport": "madinah",
            "madinah station": "madinah",
            "madina markazia": "madinah",
            "makkah principality": "makkah",
            "jeddah airport terminal 1": "jeddah",
        }

        return aliases.get(city, city)

    @classmethod
    def make_city_code(cls, city: str) -> str:
        city = cls.normalize_city_name(city)

        cleaned = re.sub(r"[^A-Za-z ]", " ", city)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if not cleaned:
            return "UNK"

        first_word = cleaned.split()[0].upper()
        if len(first_word) >= 3:
            return first_word[:3]

        joined = cleaned.replace(" ", "").upper()
        if len(joined) >= 3:
            return joined[:3]

        return (joined + "XXX")[:3]

    @staticmethod
    def clean_code(value: str) -> str:
        value = (value or "").strip().upper()
        value = re.sub(r"[^A-Z0-9\-]", "", value)
        return value

    def make_unique_route_code(self, base_code: str) -> str:
        base_code = self.clean_code(base_code)

        existing = frappe.db.get_value("Route", {"route_code": base_code}, "name")
        if not existing or existing == self.name:
            return base_code

        counter = 2
        while True:
            candidate = f"{base_code}-{counter}"
            existing = frappe.db.get_value("Route", {"route_code": candidate}, "name")
            if not existing or existing == self.name:
                return candidate
            counter += 1

    @staticmethod
    def clean_place_name(name: str) -> str:
        if not name:
            return ""
        name = name.replace(", Saudi Arabia", "").replace(", United Arab Emirates", "").strip()
        return name.split(",")[0]

    @staticmethod
    def get_place_name(place: str, api_key: str):
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": place,
            "inputtype": "textquery",
            "fields": "place_id",
            "key": api_key,
        }
        res = requests.get(url, params=params, timeout=20).json()
        if not res.get("candidates"):
            return Route.clean_place_name(place)

        place_id = res["candidates"][0]["place_id"]

        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params_en = {"place_id": place_id, "fields": "name", "language": "en", "key": api_key}
        en_data = requests.get(details_url, params=params_en, timeout=20).json()
        en_name = en_data.get("result", {}).get("name", place)

        params_ar = {"place_id": place_id, "fields": "name", "language": "ar", "key": api_key}
        ar_data = requests.get(details_url, params=params_ar, timeout=20).json()
        ar_name = ar_data.get("result", {}).get("name", "")

        return f"{en_name} | {ar_name}" if ar_name else en_name


def _get_api_key():
    api_key = frappe.conf.get("google_maps_api_key")
    if not api_key:
        try:
            settings = frappe.get_single("Google Map Settings")
            api_key = settings.api_key
        except Exception:
            pass

    if not api_key:
        frappe.throw(_("Google Maps API key not found. Add it in site_config.json or Google Map Settings."))

    return api_key


def _parse_distance_km(distance_text: str) -> float:
    dt = (distance_text or "").lower().replace(",", "").strip()
    if " km" in dt:
        return float(dt.replace(" km", ""))
    if " m" in dt:
        return float(dt.replace(" m", "")) / 1000
    return float("".join(ch for ch in dt if (ch.isdigit() or ch == ".")))