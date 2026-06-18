#!/usr/bin/env python3
"""TSS ZATCA Signing Engine - XML canonicalization, invoice hash, ECDSA signing"""
import base64, binascii, hashlib
from datetime import datetime
import asn1, frappe, lxml.etree as MyTree
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from frappe import _
from lxml import etree

def canonicalize_xml(xml_string):
    try:
        canonical = etree.tostring(etree.fromstring(xml_string.encode()), method="c14n").decode()
        return canonical
    except Exception as e:
        frappe.throw(_("XML canonicalization failed: {0}").format(str(e)))

def get_invoice_hash(canonical_xml):
    hash_obj = hashlib.sha256(canonical_xml.encode())
    return base64.b64encode(hash_obj.digest()).decode()

def sign_invoice_hash(invoice_hash_b64, private_key_pem):
    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None, backend=default_backend())
    signature = key.sign(invoice_hash_b64.encode(), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode()

def generate_uuid():
    import uuid
    return str(uuid.uuid4())

def sign_xml(invoice_xml, private_key_pem, certificate_pem):
    canonical = canonicalize_xml(invoice_xml)
    inv_hash = get_invoice_hash(canonical)
    signature = sign_invoice_hash(inv_hash, private_key_pem)
    uuid_str = generate_uuid()
    return {'uuid': uuid_str, 'invoice_hash': inv_hash, 'signature': signature, 'canonical_xml': canonical}

def get_pem_details(cert_pem):
    cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    return {'cert_pem': cert_pem, 'private_key': None}

def get_pem_compliance_details(doc):
    return get_pem_details(doc.get('certificate_file') or '')
