import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_zatca_status():
    try:
        settings = frappe.db.get_value('TSS ZATCA Settings', 'TSS ZATCA Settings', ['enable_zatca', 'zatca_environment', 'phase', 'compliance_csid', 'production_csid', 'csid_expiry'], as_dict=1) or {}
        return {'success': True, 'data': {'enabled': bool(settings.get('enable_zatca', 0)), 'environment': settings.get('zatca_environment', 'Sandbox'), 'phase': settings.get('phase', 'Phase 2'), 'has_csid': bool(settings.get('compliance_csid')), 'has_production': bool(settings.get('production_csid'))}}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def onboard_zatca(**kwargs):
    data = frappe._dict(kwargs)
    try:
        settings = frappe.get_single('TSS ZATCA Settings')
        settings.enable_zatca = 1
        settings.zatca_environment = data.get('environment', 'Sandbox')
        settings.phase = data.get('phase', 'Phase 2')
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        return {'success': True, 'message': 'ZATCA onboarded'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def generate_compliance_csid():
    try:
        from tss.zatca.utils import build_csr
        settings = frappe.db.get_value('TSS ZATCA Settings', 'TSS ZATCA Settings', '*', as_dict=1) or {}
        if not settings.get('enable_zatca'):
            return {'success': False, 'error': 'ZATCA not enabled'}
        result = build_csr('Test Company', '310000000000003', '1010000000')
        return {'success': True, 'csr': result['csr'][:100] + '...'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

