from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "vehicle",
        "transactions": [
            {
                "label": "Inspection Context",
                "items": ["Trip", "Vehicle"],
            }
        ],
        "internal_links": {
            "Staff": ["inspector"],
            "Trip": ["trip"],
        },
        "non_standard_fieldnames": {
            "Trip": "trip",
        },
    }
