from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "route",
        "transactions": [
            {
                "label": "Operations",
                "items": ["Trip", "Trip Booking", "Trip Pricing Rule"],
            }
        ],
        "non_standard_fieldnames": {
            "Trip": "route",
            "Trip Booking": "route",
            "Trip Pricing Rule": "route",
        },
    }
