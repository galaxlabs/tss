#!/usr/bin/env python3
"""Captain Onboarding API - Full captain registration flow"""
import frappe
from frappe import _
from frappe.utils import now_datetime, today

@frappe.whitelist(allow_guest=True)
def register_captain(**kwargs):
    """Complete captain registration with company creation"""
    data = frappe._dict(kwargs)
    
    # Step 1: Create Base Company
    company_name = data.get('company_name')
    if not company_name:
        frappe.throw(_('Company name is required'))
    
    company_code = company_name[:3].upper() + '-' + frappe.generate_hash(length=4).upper()
    
    if not frappe.db.exists('Base Company', company_name):
        company = frappe.get_doc({
            'doctype': 'Base Company',
            'company_name': company_name,
            'company_code': company_code,
            'is_active': 1,
        })
        company.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.commit()
    
    # Step 2: Create Captain Profile
    captain = frappe.get_doc({
        'doctype': 'Captain Profile',
        'full_name': data.get('full_name'),
        'name_ar': data.get('name_ar', ''),
        'email': data.get('email'),
        'mobile_no': data.get('mobile_no'),
        'base_company': company_name,
        'national_id': data.get('national_id', ''),
        'national_id_expiry': data.get('national_id_expiry') or None,
        'driving_license_no': data.get('driving_license_no', ''),
        'driving_license_expiry': data.get('driving_license_expiry') or None,
        'company_cr': data.get('company_cr', ''),
        'vat_reg_no': data.get('vat_reg_no', ''),
        'bank_name': data.get('bank_name', ''),
        'iban_no': data.get('iban_no', ''),
        'account_no': data.get('account_no', ''),
        'passport_no': data.get('passport_no', ''),
        'status': 'Active',
    })
    captain.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    
    return {
        'success': True,
        'captain': captain.name,
        'company': company_name,
        'company_code': company_code,
    }

@frappe.whitelist(allow_guest=True)
def update_captain_profile(**kwargs):
    """Update captain personal and company info"""
    data = frappe._dict(kwargs)
    captain_name = data.get('captain')
    
    if not captain_name or not frappe.db.exists('Captain Profile', captain_name):
        frappe.throw(_('Captain not found'))
    
    captain = frappe.get_doc('Captain Profile', captain_name)
    updatable = ['full_name', 'name_ar', 'email', 'mobile_no', 'national_id',
                 'national_id_expiry', 'driving_license_no', 'driving_license_expiry',
                 'company_cr', 'vat_reg_no', 'bank_name', 'iban_no', 'account_no',
                 'passport_no', 'company_logo', 'id_document', 'driving_license_doc',
                 'bank_document', 'passport_doc', 'photo', 'notes']
    for field in updatable:
        if data.get(field) is not None:
            setattr(captain, field, data.get(field))
    
    captain.save(ignore_permissions=True)
    frappe.db.commit()
    return {'success': True, 'captain': captain.name}

@frappe.whitelist(allow_guest=True)
def upload_document(**kwargs):
    """Upload a driver document (license, iqama, etc.)"""
    data = frappe._dict(kwargs)
    doc = frappe.get_doc({
        'doctype': 'Driver Document',
        'captain': data.get('captain'),
        'document_type': data.get('document_type'),
        'document_no': data.get('document_no', ''),
        'issue_date': data.get('issue_date') or None,
        'expiry_date': data.get('expiry_date') or None,
        'attachment': data.get('attachment') or None,
        'notes': data.get('notes', ''),
        'status': 'Valid',
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'name': doc.name}

@frappe.whitelist(allow_guest=True)
def register_vehicle(**kwargs):
    """Register a vehicle under captain"""
    data = frappe._dict(kwargs)
    
    doc = frappe.get_doc({
        'doctype': 'Vehicle',
        'vehicle_name': data.get('vehicle_name') or f"{data.get('plate_no')}",
        'vehicle_name_ar': data.get('vehicle_name_ar', ''),
        'plate_no': data.get('plate_no'),
        'plate_no_ar': data.get('plate_no_ar', ''),
        'vehicle_type': data.get('vehicle_type'),
        'vehicle_make': data.get('vehicle_make'),
        'vehicle_model': data.get('vehicle_model'),
        'model_year': data.get('model_year') or None,
        'color': data.get('color', ''),
        'seat_capacity': data.get('seat_capacity') or None,
        'fuel_type': data.get('fuel_type', 'Petrol'),
        'chassis_no': data.get('chassis_no', ''),
        'registration_no': data.get('registration_no', ''),
        'status': 'Active',
        'ownership_type': data.get('ownership_type', 'Owned'),
        'base_company': data.get('base_company') or 'Comprehensive Excellence Leading Transportation Company',
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'vehicle': doc.name, 'vehicle_code': doc.vehicle_code}

@frappe.whitelist(allow_guest=True)
def submit_daily_inspection(**kwargs):
    """Submit daily vehicle inspection checklist"""
    data = frappe._dict(kwargs)
    doc = frappe.get_doc({
        'doctype': 'Daily Vehicle Inspection',
        'vehicle': data.get('vehicle'),
        'inspector': data.get('captain'),
        'inspection_date': data.get('inspection_date') or today(),
        'tires_ok': data.get('tires_ok', 0),
        'lights_ok': data.get('lights_ok', 0),
        'brakes_ok': data.get('brakes_ok', 0),
        'oil_level': data.get('oil_level', 'OK'),
        'coolant_level': data.get('coolant_level', 'OK'),
        'windshield_ok': data.get('windshield_ok', 0),
        'ac_working': data.get('ac_working', 0),
        'seats_clean': data.get('seats_clean', 0),
        'seatbelts_ok': data.get('seatbelts_ok', 0),
        'first_aid_kit': data.get('first_aid_kit', 0),
        'fire_extinguisher': data.get('fire_extinguisher', 0),
        'spare_tire': data.get('spare_tire', 0),
        'odometer_reading': data.get('odometer_reading') or 0,
        'notes': data.get('notes', ''),
    })
    
    # Determine status
    all_checks_passed = all([
        doc.tires_ok, doc.lights_ok, doc.brakes_ok, doc.windshield_ok,
        doc.ac_working, doc.seatbelts_ok,
        doc.oil_level == 'OK', doc.coolant_level == 'OK',
    ])
    doc.status = 'Passed' if all_checks_passed else 'Failed'
    
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    return {'success': True, 'name': doc.name, 'status': doc.status}

@frappe.whitelist(allow_guest=True)
def get_captain_dashboard(captain_name):
    """Get captain dashboard with stats"""
    data = {
        'profile': frappe.db.get_value('Captain Profile', captain_name, '*') if frappe.db.exists('Captain Profile', captain_name) else {},
        'vehicles': frappe.get_all('Vehicle', filters={'assigned_driver': captain_name}, limit=10),
        'today_inspection': frappe.db.exists('Daily Vehicle Inspection', {'inspector': captain_name, 'inspection_date': today()}),
        'pending_rides': frappe.db.count('Ride Request', {'status': 'Pending'}),
        'my_offers': frappe.db.count('Ride Offer', {'driver': captain_name}),
        'my_rides': frappe.db.count('Ride Request', {'accepted_driver': captain_name}),
        'documents': frappe.get_all('Driver Document', filters={'captain': captain_name}),
    }
    return {'success': True, 'data': data}

@frappe.whitelist(allow_guest=True)
def get_captain_documents(captain_name):
    """Get all documents for a captain"""
    docs = frappe.get_all('Driver Document',
        filters={'captain': captain_name},
        fields=['name', 'document_type', 'document_no', 'issue_date', 'expiry_date', 'status'],
        order_by='expiry_date asc')
    return {'success': True, 'data': docs}

@frappe.whitelist(allow_guest=True)
def get_captain_vehicles(captain_name):
    """Get all vehicles for a captain"""
    vehicles = frappe.get_all('Vehicle', 
        filters={'assigned_driver': captain_name},
        fields=['name', 'vehicle_name', 'plate_no', 'vehicle_type', 'vehicle_make', 'model_year', 'color', 'status'])
    return {'success': True, 'data': vehicles}

@frappe.whitelist(allow_guest=True)
def get_inspection_history(vehicle_name, limit=30):
    """Get inspection history for a vehicle"""
    history = frappe.get_all('Daily Vehicle Inspection',
        filters={'vehicle': vehicle_name},
        fields=['name', 'inspection_date', 'status', 'odometer_reading', 'notes'],
        order_by='inspection_date desc',
        limit_page_length=limit)
    return {'success': True, 'data': history}
