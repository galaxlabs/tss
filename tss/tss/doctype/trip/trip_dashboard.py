from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "trip",
        "transactions": [
            {
                "label": "Linked Records",
                "items": ["Trip Booking", "Vehicle Inspection Log"],
            }
        ],
        "internal_links": {
            "Route": ["route"],
            "Vehicle": ["vehicle"],
            "Staff": ["driver", "conductor"],
            "Trip Pricing Rule": ["pricing_rule"],
        },
        "non_standard_fieldnames": {
            "Trip Booking": "trip",
            "Vehicle Inspection Log": "trip",
        },
    }
