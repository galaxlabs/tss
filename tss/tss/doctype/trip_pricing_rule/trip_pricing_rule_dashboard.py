from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "pricing_rule",
        "transactions": [
            {
                "label": "Usage",
                "items": ["Trip", "Trip Booking"],
            }
        ],
        "internal_links": {
            "Route": ["route"],
            "Vehicle Type": ["vehicle_type"],
        },
        "non_standard_fieldnames": {
            "Trip": "pricing_rule",
            "Trip Booking": "pricing_rule",
        },
    }
