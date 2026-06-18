#!/usr/bin/env python3
"""Trip Invoice API - Generate from trip, calculate VAT, ZATCA ready"""
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, today, money_in_words

@frappe.whitelist(allow_guest=True)
def generate_trip_invoice(**kwargs):
    """Generate an invoice from a ride request / trip"""
    data = frappe._dict(kwargs)
    ride_name = data.get('ride_request') or data.get('trip')
    
    if not ride_name or not frappe.db.exists('Ride Request', ride_name):
        return {'success': False, 'error': 'Ride request not found'}
    
    ride = frappe.get_doc('Ride Request', ride_name)
    
    # Calculate amounts
    trip_amount = flt(ride.final_price or ride.offered_price or 0)
    vat_rate = flt(data.get('vat_rate', 15))
    vat_amount = trip_amount * vat_rate / 100
    grand_total = trip_amount + vat_amount
    
    invoice = frappe.get_doc({
        'doctype': 'Trip Invoice TSS',
        'trip': ride.name,
        'captain': ride.accepted_driver or data.get('captain', ''),
        'customer_name': ride.customer_name or data.get('customer_name', ''),
        'customer_phone': ride.customer_phone or data.get('customer_phone', ''),
        'customer_vat': data.get('customer_vat', ''),
        'trip_amount': trip_amount,
        'vat_rate': vat_rate,
        'vat_amount': vat_amount,
        'grand_total': grand_total,
        'invoice_date': data.get('invoice_date') or today(),
        'status': 'Draft',
        'notes': data.get('notes', ''),
    })
    invoice.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.commit()
    
    return {
        'success': True,
        'name': invoice.name,
        'data': {
            'trip_amount': trip_amount,
            'vat_rate': vat_rate,
            'vat_amount': vat_amount,
            'grand_total': grand_total,
            'grand_total_words': money_in_words(grand_total, 'SAR'),
        }
    }

@frappe.whitelist(allow_guest=True)
def mark_invoice_ready(invoice_name):
    """Mark invoice as ready for printing/Kashf"""
    if not frappe.db.exists('Trip Invoice TSS', invoice_name):
        return {'success': False, 'error': 'Invoice not found'}
    
    frappe.db.set_value('Trip Invoice TSS', invoice_name, 'status', 'Ready')
    frappe.db.set_value('Trip Invoice TSS', invoice_name, 'kashf_sent', 1)
    frappe.db.commit()
    return {'success': True, 'status': 'Ready'}

@frappe.whitelist(allow_guest=True)
def get_invoice_detail(invoice_name):
    """Get full invoice details"""
    if not frappe.db.exists('Trip Invoice TSS', invoice_name):
        return {'success': False, 'error': 'Invoice not found'}
    
    invoice = frappe.get_doc('Trip Invoice TSS', invoice_name)
    return {
        'success': True,
        'data': {
            'name': invoice.name,
            'trip': invoice.trip,
            'captain': invoice.captain,
            'customer_name': invoice.customer_name,
            'customer_phone': invoice.customer_phone,
            'trip_amount': invoice.trip_amount,
            'vat_rate': invoice.vat_rate,
            'vat_amount': invoice.vat_amount,
            'grand_total': invoice.grand_total,
            'status': invoice.status,
            'invoice_date': str(invoice.invoice_date),
            'kashf_sent': invoice.kashf_sent,
            'zatca_submitted': invoice.zatca_submitted,
            'notes': invoice.notes,
        }
    }

@frappe.whitelist(allow_guest=True)
def get_captain_invoices(captain_name, limit=50):
    """Get all invoices for a captain"""
    invoices = frappe.get_all('Trip Invoice TSS',
        filters={'captain': captain_name},
        fields=['name', 'trip', 'customer_name', 'grand_total', 'status', 'invoice_date', 'kashf_sent'],
        order_by='creation desc',
        limit_page_length=int(limit))
    return {'success': True, 'data': invoices}

@frappe.whitelist(allow_guest=True)
def calculate_vat(trip_amount, vat_rate=15):
    """Simple VAT calculator"""
    ta = flt(trip_amount)
    vr = flt(vat_rate)
    vat = ta * vr / 100
    return {
        'success': True,
        'data': {
            'trip_amount': ta,
            'vat_rate': vr,
            'vat_amount': vat,
            'grand_total': ta + vat,
            'vat_included_price': ta / (1 + vr/100) if vr > 0 else ta,
        }
    }
