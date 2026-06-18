import json, frappe
from frappe import _
from frappe.utils import flt, today, money_in_words

@frappe.whitelist(allow_guest=True)
def calculate_invoice_totals(items_json, vat_rate=15, discount_amount=0):
    items = json.loads(items_json) if isinstance(items_json, str) else items_json
    subtotal = 0.0
    for item in items:
        qty = flt(item.get('qty', 1))
        rate = flt(item.get('rate', 0))
        item['amount'] = qty * rate
        subtotal += item['amount']
    after_discount = subtotal - flt(discount_amount)
    vat_amount = after_discount * flt(vat_rate) / 100
    grand_total = after_discount + vat_amount
    return {'success': True, 'data': {'subtotal': subtotal, 'vat_rate': vat_rate, 'vat_amount': vat_amount, 'grand_total': grand_total}}

@frappe.whitelist(allow_guest=True)
def get_invoice_list(captain=None, status=None, limit=50):
    filters = {}
    if captain: filters['captain'] = captain
    if status: filters['status'] = status
    try:
        invoices = frappe.get_all('Trip Invoice TSS', filters=filters, fields=['name', 'customer_name', 'grand_total', 'status', 'invoice_date'], order_by='creation desc', limit_page_length=int(limit))
        return {'success': True, 'data': invoices}
    except Exception as e:
        return {'success': False, 'error': str(e), 'data': []}

@frappe.whitelist(allow_guest=True)
def mark_invoice_ready(invoice_name):
    frappe.db.set_value('Trip Invoice TSS', invoice_name, 'status', 'Ready')
    frappe.db.commit()
    return {'success': True}

@frappe.whitelist(allow_guest=True)
def generate_vat_report(company, period_from, period_to):
    invoices = frappe.get_all('Trip Invoice TSS', filters={'invoice_date': ['between', [period_from, period_to]]}, fields=['trip_amount', 'vat_amount'])
    total_sales = sum(flt(inv['trip_amount']) for inv in invoices)
    total_vat = sum(flt(inv['vat_amount']) for inv in invoices)
    return {'success': True, 'total_sales': total_sales, 'total_vat': total_vat, 'invoice_count': len(invoices)}

