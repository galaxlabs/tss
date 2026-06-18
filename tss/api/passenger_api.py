#!/usr/bin/env python3
"""Passenger Registration API - Register, scan documents, link to trips"""
import frappe
from frappe import _
from frappe.utils import now_datetime, today

@frappe.whitelist(allow_guest=True)
def register_passenger(**kwargs):
    """Register a new passenger or return existing one"""
    data = frappe._dict(kwargs)
    doc_type = data.get('document_type', 'Iqama')
    doc_number = data.get('document_number', '').strip()
    full_name = data.get('full_name', '').strip()
    
    if not doc_number or not full_name:
        return {'success': False, 'error': 'Document number and full name required'}
    
    # Build identity key: doctype:docnumber
    identity_key = f"{doc_type.upper()}:{doc_number}"
    
    # Check if passenger already exists
    if frappe.db.exists('Passenger Master', identity_key):
        passenger = frappe.get_doc('Passenger Master', identity_key)
        passenger.last_seen_at = now_datetime()
        if data.get('contact_no'):
            passenger.contact_no = data.get('contact_no')
        passenger.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            'success': True,
            'name': passenger.name,
            'full_name': passenger.full_name,
            'identity_key': identity_key,
            'is_new': False,
        }
    
    # Create new passenger
    passenger = frappe.get_doc({
        'doctype': 'Passenger Master',
        'document_type': doc_type,
        'document_number': doc_number,
        'identity_key': identity_key,
        'full_name': full_name,
        'full_name_ar': data.get('full_name_ar', ''),
        'nationality': data.get('nationality', ''),
        'contact_no': data.get('contact_no', ''),
        'date_of_birth': data.get('date_of_birth') or None,
        'expiry_date': data.get('expiry_date') or None,
        'source': data.get('source', 'Mobile App'),
        'first_seen_at': now_datetime(),
        'last_seen_at': now_datetime(),
        'is_verified': 0,
    })
    passenger.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        'success': True,
        'name': passenger.name,
        'full_name': passenger.full_name,
        'identity_key': identity_key,
        'is_new': True,
    }

@frappe.whitelist(allow_guest=True)
def get_passenger_by_document(document_type, document_number):
    """Lookup passenger by document"""
    identity_key = f"{document_type.upper()}:{document_number}"
    if not frappe.db.exists('Passenger Master', identity_key):
        return {'success': False, 'error': 'Passenger not found'}
    
    passenger = frappe.get_doc('Passenger Master', identity_key)
    return {
        'success': True,
        'data': {
            'name': passenger.name,
            'full_name': passenger.full_name,
            'full_name_ar': passenger.full_name_ar,
            'nationality': passenger.nationality,
            'contact_no': passenger.contact_no,
            'document_type': passenger.document_type,
            'document_number': passenger.document_number,
            'expiry_date': str(passenger.expiry_date) if passenger.expiry_date else None,
            'is_verified': passenger.is_verified,
        }
    }

@frappe.whitelist(allow_guest=True)
def link_passenger_to_ride(ride_request_name, passenger_identity):
    """Link a passenger to an existing ride request"""
    if not frappe.db.exists('Ride Request', ride_request_name):
        return {'success': False, 'error': 'Ride request not found'}
    
    if not frappe.db.exists('Passenger Master', passenger_identity):
        return {'success': False, 'error': 'Passenger not found'}
    
    ride = frappe.get_doc('Ride Request', ride_request_name)
    passenger = frappe.get_doc('Passenger Master', passenger_identity)
    
    # Update ride with passenger info
    ride.customer_name = passenger.full_name
    ride.customer_phone = passenger.contact_no or ride.customer_phone
    ride.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        'success': True,
        'ride': ride.name,
        'passenger': passenger.full_name,
    }

@frappe.whitelist(allow_guest=True)
def get_passenger_rides(passenger_identity):
    """Get all rides for a specific passenger"""
    rides = frappe.get_all('Ride Request',
        filters={'customer_name': ['like', f'%{passenger_identity}%']},
        fields=['name', 'route', 'pickup_location', 'dropoff_location', 'travel_date', 'offered_price', 'final_price', 'status'],
        order_by='creation desc', limit_page_length=50)
    return {'success': True, 'data': rides}

@frappe.whitelist(allow_guest=True)
def search_passengers(query, limit=20):
    """Search passengers by name or document number"""
    passengers = frappe.get_all('Passenger Master',
        filters={'full_name': ['like', f'%{query}%']},
        or_filters={'document_number': ['like', f'%{query}%']},
        fields=['name', 'full_name', 'document_type', 'document_number', 'nationality', 'contact_no'],
        limit_page_length=int(limit))
    return {'success': True, 'data': passengers}
