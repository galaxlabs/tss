from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "trip",
        "transactions": [
            {
                "label": "Trip Context",
                "items": ["Trip"],
            }
        ],
        "internal_links": {
            "Trip": ["trip"],
            "Route": ["route"],
            "Trip Pricing Rule": ["pricing_rule"],
        },
    }
