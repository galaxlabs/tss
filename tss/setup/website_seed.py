from __future__ import annotations

from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate
from frappe.utils.file_manager import save_file


IMAGE_ROOT = Path("/home/dg/Transport-Hub/attached_assets/generated_images")


WEBSITE_SEED_DATA = {
    "categories": [
        {"category_name": "Sedan", "category_name_ar": "سيدان", "notes": "Comfortable saloon cars for airport and city transfers."},
        {"category_name": "MPV", "category_name_ar": "متعدد الاستخدام", "notes": "Family transport and pilgrimage transfer vehicles."},
        {"category_name": "Van", "category_name_ar": "فان", "notes": "Group transport vehicles with luggage space."},
        {"category_name": "SUV", "category_name_ar": "دفع رباعي", "notes": "Premium and executive transport vehicles."},
    ],
    "makes": [
        {"make_name": "Toyota", "make_name_ar": "تويوتا", "country_of_origin": "Japan"},
        {"make_name": "Hyundai", "make_name_ar": "هيونداي", "country_of_origin": "South Korea"},
        {"make_name": "GMC", "make_name_ar": "جي إم سي", "country_of_origin": "USA"},
    ],
    "types": [
        {
            "type_name": "Sedan Transfer",
            "type_name_ar": "سيدان للنقل",
            "category": "Sedan",
            "default_seating_capacity": 3,
            "notes": "Comfortable airport and hotel transfer sedan.",
            "image_file": "white_toyota_camry_sedan.png",
        },
        {
            "type_name": "Family MPV",
            "type_name_ar": "مركبة عائلية",
            "category": "MPV",
            "default_seating_capacity": 5,
            "notes": "Family MPV with comfortable luggage capacity for Umrah and city travel.",
            "image_file": "white_toyota_innova_mpv.png",
        },
        {
            "type_name": "Group Van",
            "type_name_ar": "فان جماعي",
            "category": "Van",
            "default_seating_capacity": 10,
            "notes": "HiAce class group van for families and pilgrim groups.",
            "image_file": "white_toyota_hiace_van.png",
        },
        {
            "type_name": "Premium MPV",
            "type_name_ar": "مركبة فاخرة",
            "category": "MPV",
            "default_seating_capacity": 7,
            "notes": "Premium MPV for executive and VIP transfers.",
            "image_file": "silver_hyundai_staria_mpv.png",
        },
        {
            "type_name": "Luxury SUV",
            "type_name_ar": "دفع رباعي فاخر",
            "category": "SUV",
            "default_seating_capacity": 6,
            "notes": "Luxury SUV for VIP travel and premium pilgrimage support.",
            "image_file": "black_gmc_yukon_suv.png",
        },
        {
            "type_name": "Passenger Van",
            "type_name_ar": "فان ركاب",
            "category": "Van",
            "default_seating_capacity": 8,
            "notes": "Medium passenger van for practical direct transport bookings.",
            "image_file": "white_hyundai_h1_van.png",
        },
    ],
    "models": [
        {
            "model_name": "Toyota Camry",
            "model_name_ar": "تويوتا كامري",
            "vehicle_make": "Toyota",
            "vehicle_type": "Sedan Transfer",
            "model_year_from": 2021,
            "seat_capacity": 3,
            "fuel_type": "Petrol",
            "notes": "Website seed model for sedan transfers.",
            "image_file": "white_toyota_camry_sedan.png",
        },
        {
            "model_name": "Toyota Innova",
            "model_name_ar": "تويوتا إنوفا",
            "vehicle_make": "Toyota",
            "vehicle_type": "Family MPV",
            "model_year_from": 2021,
            "seat_capacity": 5,
            "fuel_type": "Petrol",
            "notes": "Website seed model for family intercity travel.",
            "image_file": "white_toyota_innova_mpv.png",
        },
        {
            "model_name": "Toyota HiAce",
            "model_name_ar": "تويوتا هايس",
            "vehicle_make": "Toyota",
            "vehicle_type": "Group Van",
            "model_year_from": 2020,
            "seat_capacity": 10,
            "fuel_type": "Diesel",
            "notes": "Website seed model for group transfers.",
            "image_file": "white_toyota_hiace_van.png",
        },
        {
            "model_name": "Hyundai Staria",
            "model_name_ar": "هيونداي ستاريا",
            "vehicle_make": "Hyundai",
            "vehicle_type": "Premium MPV",
            "model_year_from": 2022,
            "seat_capacity": 7,
            "fuel_type": "Petrol",
            "notes": "Website seed model for premium MPV travel.",
            "image_file": "silver_hyundai_staria_mpv.png",
        },
        {
            "model_name": "GMC Yukon XL",
            "model_name_ar": "جي إم سي يوكن XL",
            "vehicle_make": "GMC",
            "vehicle_type": "Luxury SUV",
            "model_year_from": 2022,
            "seat_capacity": 6,
            "fuel_type": "Petrol",
            "notes": "Website seed model for luxury and VIP travel.",
            "image_file": "black_gmc_yukon_suv.png",
        },
        {
            "model_name": "Hyundai H1",
            "model_name_ar": "هيونداي H1",
            "vehicle_make": "Hyundai",
            "vehicle_type": "Passenger Van",
            "model_year_from": 2020,
            "seat_capacity": 8,
            "fuel_type": "Diesel",
            "notes": "Website seed model for practical van transfers.",
            "image_file": "white_hyundai_h1_van.png",
        },
    ],
    "routes": [
        {
            "route_name": "Jeddah Airport - Makkah Hotel",
            "route_name_ar": "مطار جدة - فندق مكة",
            "source": "Jeddah Airport",
            "destination": "Makkah Hotel",
            "route_type": "Airport",
            "distance_km": 85,
            "estimated_duration_minutes": 75,
            "default_vehicle_type": "Sedan Transfer",
            "notes": "Popular airport pickup route for website bookings.",
        },
        {
            "route_name": "Makkah - Madinah",
            "route_name_ar": "مكة - المدينة",
            "source": "Makkah",
            "destination": "Madinah",
            "route_type": "Intercity",
            "distance_km": 420,
            "estimated_duration_minutes": 270,
            "default_vehicle_type": "Family MPV",
            "notes": "Popular intercity pilgrimage route.",
        },
        {
            "route_name": "Jeddah Airport - Madinah",
            "route_name_ar": "مطار جدة - المدينة",
            "source": "Jeddah Airport",
            "destination": "Madinah",
            "route_type": "Airport",
            "distance_km": 450,
            "estimated_duration_minutes": 300,
            "default_vehicle_type": "Group Van",
            "notes": "Long-distance airport transfer route.",
        },
        {
            "route_name": "Madinah Hotel - Madinah Airport",
            "route_name_ar": "فندق المدينة - مطار المدينة",
            "source": "Madinah Hotel",
            "destination": "Madinah Airport",
            "route_type": "Airport",
            "distance_km": 25,
            "estimated_duration_minutes": 30,
            "default_vehicle_type": "Sedan Transfer",
            "notes": "Quick city-to-airport transfer.",
        },
        {
            "route_name": "Makkah Hotel - Jeddah Airport",
            "route_name_ar": "فندق مكة - مطار جدة",
            "source": "Makkah Hotel",
            "destination": "Jeddah Airport",
            "route_type": "Airport",
            "distance_km": 85,
            "estimated_duration_minutes": 75,
            "default_vehicle_type": "Premium MPV",
            "notes": "Return airport transfer route.",
        },
        {
            "route_name": "Makkah - Makkah Ziyarat",
            "route_name_ar": "مكة - زيارات مكة",
            "source": "Makkah",
            "destination": "Makkah Ziyarat",
            "route_type": "Intracity",
            "distance_km": 50,
            "estimated_duration_minutes": 240,
            "default_vehicle_type": "Luxury SUV",
            "notes": "VIP city ziyarat and hourly transfer route.",
        },
    ],
    "pricing_rules": [
        {"route_source": "Jeddah Airport", "route_destination": "Makkah Hotel", "vehicle_type": "Sedan Transfer", "trip_type": "One Way", "amount": 150},
        {"route_source": "Jeddah Airport", "route_destination": "Makkah Hotel", "vehicle_type": "Passenger Van", "trip_type": "One Way", "amount": 220},
        {"route_source": "Makkah", "route_destination": "Madinah", "vehicle_type": "Family MPV", "trip_type": "One Way", "amount": 650},
        {"route_source": "Jeddah Airport", "route_destination": "Madinah", "vehicle_type": "Group Van", "trip_type": "One Way", "amount": 850},
        {"route_source": "Madinah Hotel", "route_destination": "Madinah Airport", "vehicle_type": "Sedan Transfer", "trip_type": "One Way", "amount": 80},
        {"route_source": "Makkah Hotel", "route_destination": "Jeddah Airport", "vehicle_type": "Premium MPV", "trip_type": "One Way", "amount": 200},
        {"route_source": "Makkah", "route_destination": "Makkah Ziyarat", "vehicle_type": "Luxury SUV", "trip_type": "One Way", "amount": 450},
    ],
}


def _default_base_company(base_company: str | None = None) -> str:
    if base_company and frappe.db.exists("Base Company", base_company):
        return base_company

    active_company = frappe.db.get_value("Base Company", {"status": "Active"}, "name")
    if active_company:
        return active_company

    any_company = frappe.db.get_value("Base Company", {}, "name")
    if any_company:
        return any_company

    frappe.throw(_("Please create a Base Company before seeding website transport data."))


def _upsert_named_doc(doctype: str, name: str, values: dict[str, Any]):
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        for fieldname, value in values.items():
            doc.set(fieldname, value)
    else:
        doc = frappe.get_doc({"doctype": doctype, **values})

    doc.save(ignore_permissions=True)
    return doc


def _upsert_route(values: dict[str, Any]):
    route_name = frappe.db.get_value(
        "Route",
        {"source": values["source"], "destination": values["destination"]},
        "name",
    )
    if route_name:
        doc = frappe.get_doc("Route", route_name)
        for fieldname, value in values.items():
            doc.set(fieldname, value)
    else:
        doc = frappe.get_doc({"doctype": "Route", **values})

    doc.save(ignore_permissions=True)
    return doc


def _upsert_pricing_rule(base_company: str, route_name: str, values: dict[str, Any], currency: str):
    existing_name = frappe.db.get_value(
        "Trip Pricing Rule",
        {
            "base_company": base_company,
            "route": route_name,
            "vehicle_type": values["vehicle_type"],
            "trip_type": values["trip_type"],
        },
        "name",
    )
    payload = {
        "base_company": base_company,
        "route": route_name,
        "vehicle_type": values["vehicle_type"],
        "trip_type": values["trip_type"],
        "service_type": "Website Transfer",
        "effective_from": getdate(),
        "currency": currency,
        "amount": values["amount"],
        "status": "Active",
        "notes": "Website seed pricing rule",
    }
    if existing_name:
        doc = frappe.get_doc("Trip Pricing Rule", existing_name)
        for fieldname, value in payload.items():
            doc.set(fieldname, value)
    else:
        doc = frappe.get_doc({"doctype": "Trip Pricing Rule", **payload})

    doc.save(ignore_permissions=True)
    return doc


def _image_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    path = IMAGE_ROOT / filename
    return path if path.exists() else None


def _attach_image(doc, fieldname: str, filename: str | None, force: bool = False):
    image_path = _image_path(filename)
    if not image_path:
        return

    if doc.get(fieldname) and not force:
        return

    existing = frappe.db.get_value(
        "File",
        {
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "attached_to_field": fieldname,
        },
        ["name", "file_url"],
        as_dict=True,
    )
    if existing and existing.file_url and not force:
        doc.db_set(fieldname, existing.file_url, update_modified=False)
        return

    file_doc = save_file(
        image_path.name,
        image_path.read_bytes(),
        doc.doctype,
        doc.name,
        is_private=0,
        df=fieldname,
    )
    doc.db_set(fieldname, file_doc.file_url, update_modified=False)


@frappe.whitelist()
def seed_website_demo_data(base_company: str | None = None, force: int | str = 0):
    force = bool(cint(force))
    base_company = _default_base_company(base_company)
    currency = frappe.db.get_value("Base Company", base_company, "default_currency") or "SAR"

    created = {
        "base_company": base_company,
        "categories": [],
        "makes": [],
        "types": [],
        "models": [],
        "routes": [],
        "pricing_rules": [],
    }

    for row in WEBSITE_SEED_DATA["categories"]:
        doc = _upsert_named_doc("Vehicle Category", row["category_name"], {**row, "status": "Active"})
        created["categories"].append(doc.name)

    for row in WEBSITE_SEED_DATA["makes"]:
        doc = _upsert_named_doc("Vehicle Make", row["make_name"], {**row, "status": "Active"})
        _attach_image(doc, "image", row.get("image_file"), force=force)
        created["makes"].append(doc.name)

    for row in WEBSITE_SEED_DATA["types"]:
        image_file = row.get("image_file")
        values = {k: v for k, v in row.items() if k != "image_file"}
        values["status"] = "Active"
        doc = _upsert_named_doc("Vehicle Type", row["type_name"], values)
        _attach_image(doc, "image", image_file, force=force)
        created["types"].append(doc.name)

    for row in WEBSITE_SEED_DATA["models"]:
        image_file = row.get("image_file")
        values = {k: v for k, v in row.items() if k != "image_file"}
        values["status"] = "Active"
        doc = _upsert_named_doc("Vehicle Model", row["model_name"], values)
        _attach_image(doc, "image", image_file, force=force)
        created["models"].append(doc.name)

    route_map: dict[tuple[str, str], str] = {}
    for row in WEBSITE_SEED_DATA["routes"]:
        doc = _upsert_route({**row, "status": "Active"})
        route_map[(row["source"], row["destination"])] = doc.name
        created["routes"].append(doc.name)

    for row in WEBSITE_SEED_DATA["pricing_rules"]:
        route_name = route_map.get((row["route_source"], row["route_destination"]))
        if not route_name:
            continue
        doc = _upsert_pricing_rule(base_company, route_name, row, currency)
        created["pricing_rules"].append(doc.name)

    frappe.db.commit()
    return {
        "message": _("Website transport seed completed."),
        **created,
    }
