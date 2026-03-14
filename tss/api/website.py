from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate

from tss.utils.transport_naming import clean_long_text, clean_text


def _parse_payload(payload=None) -> dict[str, Any]:
    if payload:
        return frappe.parse_json(payload)
    return frappe._dict(frappe.local.form_dict or {})


def _get_default_base_company() -> str:
    base_company = frappe.form_dict.get("base_company") if getattr(frappe, "form_dict", None) else None
    if base_company and frappe.db.exists("Base Company", base_company):
        return base_company

    active_company = frappe.db.get_value("Base Company", {"status": "Active"}, "name")
    if active_company:
        return active_company

    any_company = frappe.db.get_value("Base Company", {}, "name")
    if any_company:
        return any_company

    frappe.throw(_("No Base Company is configured for website booking."))


def _get_active_pricing(route: str, base_company: str) -> dict[str, Any] | None:
    if not route:
        return None

    today = getdate()
    rows = frappe.get_all(
        "Trip Pricing Rule",
        filters={
            "base_company": base_company,
            "route": route,
            "status": "Active",
            "is_active": 1,
            "effective_from": ["<=", today],
        },
        fields=["name", "amount", "currency", "effective_to"],
        order_by="effective_from desc, modified desc",
    )
    for row in rows:
        if not row.get("effective_to") or getdate(row.get("effective_to")) >= today:
            return row
    return None


def _get_public_route_rows(base_company: str) -> list[dict[str, Any]]:
    routes = frappe.get_all(
        "Route",
        filters={"status": "Active", "is_active": 1},
        fields=[
            "name",
            "route_code",
            "route_name",
            "route_title",
            "source",
            "destination",
            "distance_km",
            "estimated_duration_minutes",
        ],
        order_by="route_title asc, modified desc",
    )

    for row in routes:
        pricing = _get_active_pricing(row.name, base_company)
        row["price"] = flt((pricing or {}).get("amount"))
        row["currency"] = (pricing or {}).get("currency") or "SAR"
        row["pricing_rule"] = (pricing or {}).get("name")
        row["label"] = row.route_title or " | ".join(
            part for part in [row.route_code, f"{row.source} -> {row.destination}"] if part
        )

    return routes


def _resolve_route(base_company: str, route=None, source=None, destination=None) -> str | None:
    if route and frappe.db.exists("Route", route):
        return route

    if not (source and destination):
        return None

    source = clean_text(source)
    destination = clean_text(destination)
    return frappe.db.get_value(
        "Route",
        {
            "status": "Active",
            "is_active": 1,
            "source": source,
            "destination": destination,
        },
        "name",
    )


def _build_booking_passengers(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("passengers") or []
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)

    if rows:
        return [
            {
                "passenger_name": clean_text(row.get("passenger_name")),
                "passenger_name_ar": clean_text(row.get("passenger_name_ar")),
                "nationality": clean_text(row.get("nationality")),
                "document_type": clean_text(row.get("document_type")),
                "document_number": clean_text(row.get("document_number")),
                "mobile_no": clean_text(row.get("mobile_no")),
                "seat_no": clean_text(row.get("seat_no")),
                "source": "Booking",
                "expiry_date": row.get("expiry_date"),
                "notes": clean_long_text(row.get("notes")),
            }
            for row in rows
            if clean_text(row.get("passenger_name"))
        ]

    primary_name = clean_text(data.get("passenger_name") or data.get("full_name"))
    primary_mobile = clean_text(data.get("mobile_no") or data.get("phone"))
    if not primary_name:
        return []
    return [
        {
            "passenger_name": primary_name,
            "mobile_no": primary_mobile,
            "source": "Booking",
            "notes": clean_long_text(data.get("notes")),
        }
    ]


def _get_default_customer_group() -> str | None:
    if frappe.db.exists("DocType", "Customer Group"):
        return frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    return None


def _get_default_territory() -> str | None:
    if frappe.db.exists("DocType", "Territory"):
        return frappe.db.get_value("Territory", {"is_group": 0}, "name")
    return None


def _ensure_customer(full_name: str, email: str | None, mobile_no: str | None) -> str | None:
    if not frappe.db.exists("DocType", "Customer"):
        return None

    customer_name = frappe.db.get_value("Customer", {"customer_name": full_name}, "name")
    if customer_name and frappe.db.exists("Customer", customer_name):
        customer = frappe.get_doc("Customer", customer_name)
    else:
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": full_name,
                "customer_type": "Individual",
                "customer_group": _get_default_customer_group(),
                "territory": _get_default_territory(),
            }
        )
        customer.insert(ignore_permissions=True)

    customer_meta = frappe.get_meta("Customer")
    if email and customer_meta.has_field("email_id"):
        customer.email_id = email
    if mobile_no and customer_meta.has_field("mobile_no"):
        customer.mobile_no = mobile_no
    if customer_meta.has_field("customer_group") and not customer.get("customer_group"):
        customer.customer_group = _get_default_customer_group()
    if customer_meta.has_field("territory") and not customer.get("territory"):
        customer.territory = _get_default_territory()
    customer.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Contact"):
        existing_contact = frappe.db.get_value("Contact", {"first_name": full_name}, "name")
        contact = frappe.get_doc("Contact", existing_contact) if existing_contact else frappe.new_doc("Contact")
        contact.first_name = full_name
        contact.is_primary_contact = 1
        if email and not any((row.email_id == email) for row in (contact.get("email_ids") or [])):
            contact.append("email_ids", {"email_id": email, "is_primary": 1})
        if mobile_no and not any((row.phone == mobile_no) for row in (contact.get("phone_nos") or [])):
            contact.append("phone_nos", {"phone": mobile_no, "is_primary_mobile_no": 1})
        if not any(
            (row.link_doctype == "Customer" and row.link_name == customer.name) for row in (contact.get("links") or [])
        ):
            contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
        contact.save(ignore_permissions=True)

    return customer.name


@frappe.whitelist(allow_guest=True)
def get_public_booking_context(base_company=None):
    base_company = base_company or _get_default_base_company()
    routes = _get_public_route_rows(base_company)
    locations = sorted({clean_text(row.get("source")) for row in routes} | {clean_text(row.get("destination")) for row in routes})
    return {
        "base_company": base_company,
        "routes": routes,
        "locations": [location for location in locations if location],
    }


@frappe.whitelist(allow_guest=True)
def create_public_trip_booking(payload=None):
    data = _parse_payload(payload)
    base_company = clean_text(data.get("base_company")) or _get_default_base_company()
    route = _resolve_route(
        base_company,
        route=clean_text(data.get("route")),
        source=data.get("source"),
        destination=data.get("destination"),
    )
    if not route:
        frappe.throw(_("No active route matches the selected source and destination."))

    pricing = _get_active_pricing(route, base_company)
    booking_passenger = _build_booking_passengers(data)
    passenger_name = clean_text(data.get("passenger_name") or data.get("full_name"))
    mobile_no = clean_text(data.get("mobile_no") or data.get("phone"))
    fare_amount = flt(data.get("fare_amount") or (pricing or {}).get("amount") or 1)
    seat_count = cint(data.get("seat_count") or data.get("passengers_count") or len(booking_passenger) or 1)

    doc = frappe.get_doc(
        {
            "doctype": "Trip Booking",
            "base_company": base_company,
            "route": route,
            "passenger_name": passenger_name,
            "mobile_no": mobile_no,
            "alternate_mobile": clean_text(data.get("alternate_mobile")),
            "seat_count": seat_count,
            "fare_amount": fare_amount,
            "payment_status": "Unpaid",
            "booking_status": "Draft",
            "source_channel": "Website" if clean_text(data.get("source_channel")) not in ("Bot", "API") else clean_text(data.get("source_channel")),
            "pickup_point": clean_text(data.get("pickup_point") or data.get("source")),
            "drop_point": clean_text(data.get("drop_point") or data.get("destination")),
            "pricing_rule": (pricing or {}).get("name"),
            "notes": clean_long_text(data.get("notes")),
            "booking_passenger": booking_passenger,
        }
    )
    doc.insert(ignore_permissions=True)

    return {
        "name": doc.name,
        "booking_code": doc.booking_code,
        "route": route,
        "fare_amount": doc.fare_amount,
    }


@frappe.whitelist(allow_guest=True)
def signup_customer(payload=None):
    data = _parse_payload(payload)
    full_name = clean_text(data.get("full_name"))
    email = clean_text(cstr(data.get("email")).lower())
    mobile_no = clean_text(data.get("mobile_no") or data.get("phone"))
    password = cstr(data.get("password"))

    if not full_name or not email or not password:
        frappe.throw(_("Full Name, Email, and Password are required."))
    if frappe.db.exists("User", email):
        frappe.throw(_("A user with this email already exists."))

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "full_name": full_name,
            "mobile_no": mobile_no,
            "user_type": "Website User",
            "enabled": 1,
            "send_welcome_email": 0,
            "new_password": password,
        }
    )
    user.insert(ignore_permissions=True)

    if frappe.db.exists("Role", "Customer"):
        user.add_roles("Customer")

    customer = _ensure_customer(full_name, email, mobile_no)

    return {
        "user": user.name,
        "customer": customer,
        "created_customer": bool(customer),
        "erpnext_available": bool(frappe.db.exists("DocType", "Customer")),
    }
