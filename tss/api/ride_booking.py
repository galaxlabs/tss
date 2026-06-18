#!/usr/bin/env python3
"""Ride Booking API for TSS - InDrive-style bidding"""
import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist(allow_guest=True)
def get_available_routes():
    routes = frappe.get_all('Route', filters={'is_active': 1},
        fields=['name','route_name','source','destination','route_type','distance_km','estimated_duration_minutes','default_vehicle_type'],
        limit_page_length=100)
    return {'success': True, 'data': routes}

@frappe.whitelist(allow_guest=True)
def get_vehicle_types():
    types = frappe.get_all('Vehicle Type', filters={'is_active': 1},
        fields=['name','type_name','type_code','category','default_seating_capacity'])
    return {'success': True, 'data': types}

@frappe.whitelist(allow_guest=True)
def get_vehicle_makes():
    makes = frappe.get_all('Vehicle Make', filters={'is_active': 1},
        fields=['name','make_name','make_code','country_of_origin'])
    return {'success': True, 'data': makes}

@frappe.whitelist(allow_guest=True)
def create_ride_request(**kwargs):
    """Passenger creates a ride request with offered price"""
    data = frappe._dict(kwargs)
    doc = frappe.get_doc({
        'doctype': 'Ride Request',
        'customer_name': data.get('customer_name') or 'Guest',
        'customer_phone': data.get('phone') or '',
        'route': data.get('route'),
        'pickup_location': data.get('pickup_location'),
        'dropoff_location': data.get('dropoff_location'),
        'travel_date': data.get('travel_date'),
        'passenger_count': data.get('passengers', 1),
        'offered_price': data.get('offered_price', 0),
        'vehicle_type': data.get('vehicle_type') or None,
        'notes': data.get('message', ''),
        'status': 'Pending',
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'name': doc.name, 'status': doc.status}

@frappe.whitelist(allow_guest=True)
def get_ride_requests():
    """List all pending ride requests (for drivers to browse)"""
    rides = frappe.get_all('Ride Request',
        filters={'status': 'Pending'},
        fields=['name','customer_name','customer_phone','route','pickup_location','dropoff_location','travel_date','passenger_count','offered_price','vehicle_type','notes'],
        order_by='creation desc', limit_page_length=50)
    return {'success': True, 'data': rides}

@frappe.whitelist(allow_guest=True)
def get_my_rides():
    """Get logged-in user's rides"""
    user = frappe.session.user
    email = frappe.db.get_value('User', user, 'email') if user != 'Guest' else ''
    rides = frappe.get_all('Ride Request',
        fields=['name','customer_name','customer_phone','route','pickup_location','dropoff_location','travel_date','passenger_count','offered_price','final_price','status','notes'],
        order_by='creation desc', limit_page_length=50)
    return {'success': True, 'data': rides}

@frappe.whitelist(allow_guest=True)
def get_offers_for_ride(ride_request_name):
    """Get all driver offers for a specific ride request"""
    offers = frappe.get_all('Ride Offer',
        filters={'ride_request': ride_request_name, 'status': 'Pending'},
        fields=['name','driver','offered_price','vehicle','estimated_arrival','message'],
        order_by='offered_price asc')
    return {'success': True, 'data': offers}

@frappe.whitelist(allow_guest=True)
def submit_offer(**kwargs):
    """Driver submits a counter-offer on a ride request"""
    data = frappe._dict(kwargs)
    if not frappe.db.exists('Ride Request', data.get('ride_request')):
        frappe.throw(_('Ride request not found'))
    doc = frappe.get_doc({
        'doctype': 'Ride Offer',
        'ride_request': data.get('ride_request'),
        'driver': data.get('driver') or 'Driver',
        'offered_price': data.get('offered_price', 0),
        'vehicle': data.get('vehicle') or None,
        'estimated_arrival': data.get('estimated_arrival') or None,
        'message': data.get('message', ''),
        'status': 'Pending',
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'name': doc.name, 'status': doc.status}

@frappe.whitelist(allow_guest=True)
def accept_offer(offer_name):
    """Passenger accepts a driver's offer"""
    if not frappe.db.exists('Ride Offer', offer_name):
        frappe.throw(_('Offer not found'))
    offer = frappe.get_doc('Ride Offer', offer_name)
    offer.status = 'Accepted'
    offer.save(ignore_permissions=True)
    
    # Also mark other offers as rejected
    other_offers = frappe.get_all('Ride Offer',
        filters={'ride_request': offer.ride_request, 'name': ['!=', offer_name], 'status': 'Pending'})
    for o in other_offers:
        frappe.db.set_value('Ride Offer', o.name, 'status', 'Rejected')
    
    # Update ride request
    ride = frappe.get_doc('Ride Request', offer.ride_request)
    ride.status = 'Accepted'
    ride.accepted_driver = offer.driver
    ride.accepted_offer = offer.name
    ride.final_price = offer.offered_price
    ride.save(ignore_permissions=True)
    frappe.db.commit()
    return {'success': True, 'ride': ride.name, 'offer': offer.name, 'driver': offer.driver, 'price': offer.offered_price}

@frappe.whitelist(allow_guest=True)
def submit_rating(**kwargs):
    """Submit a rating for a ride"""
    data = frappe._dict(kwargs)
    doc = frappe.get_doc({
        'doctype': 'Ride Rating',
        'ride_request': data.get('ride_request'),
        'rating_type': data.get('rating_type', 'Driver'),
        'rated_by': data.get('rated_by', ''),
        'rated_user': data.get('rated_user', ''),
        'rating': data.get('rating', 5),
        'review': data.get('review', ''),
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'name': doc.name}

@frappe.whitelist(allow_guest=True)
def get_driver_dashboard():
    new_requests = frappe.db.count('Ride Request', {'status': 'Pending'})
    available = frappe.get_all('Ride Request',
        filters={'status': 'Pending'},
        fields=['name','customer_name','pickup_location','dropoff_location','travel_date','passenger_count','offered_price','notes'],
        limit=20)
    return {'success': True, 'data': {'new_requests': new_requests, 'available_rides': available}}

