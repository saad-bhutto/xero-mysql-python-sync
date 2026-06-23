import os
import azure.functions as func
import logging
import json
import hashlib
import hmac
import base64
from datetime import datetime, timezone
from invoices import save_invoices_to_db
from xero_client import XeroClient

XERO_WEBHOOK_KEY = os.getenv('XERO_WEBHOOK_KEY')

ALLOWED_EVENT_CATEGORIES = ['INVOICE']


def verify_signature(payload: str, signature: str, webhook_key: str) -> bool:
    """Verify the Xero webhook HMAC-SHA256 signature."""
    try:
        computed_signature = base64.b64encode(
            hmac.new(
                webhook_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        return hmac.compare_digest(signature, computed_signature)
    except Exception as e:
        logging.error(f"Signature verification error: {str(e)}")
        return False


def sync_single_invoice_to_db(invoice_data, tenant_id, sync_date):
    """Sync a single invoice entity to the database."""
    from xero_utils import parse_xero_date
    from xero_client import MySQLHelper
    db = MySQLHelper()
    inv = invoice_data
    invoice_id = inv.get('invoice_id') or inv.get('InvoiceID')
    invoice_row = {
        'invoice_id': invoice_id,
        'type': inv.get('type') or inv.get('Type'),
        'contact_id': (inv.get('contact', {}) or {}).get('contact_id') or (inv.get('Contact', {}) or {}).get('ContactID'),
        'contact_name': (inv.get('contact', {}) or {}).get('name') or (inv.get('Contact', {}) or {}).get('Name'),
        'DATE': parse_xero_date(inv.get('date') or inv.get('Date')),
        'line_amount_types': inv.get('line_amount_types') or inv.get('LineAmountTypes'),
        'invoice_number': inv.get('invoice_number') or inv.get('InvoiceNumber'),
        'reference': inv.get('reference') or inv.get('Reference'),
        'branding_theme_id': inv.get('branding_theme_id') or inv.get('BrandingThemeID'),
        'currency_code': inv.get('currency_code') or inv.get('CurrencyCode'),
        'currency_rate': inv.get('currency_rate') or inv.get('CurrencyRate'),
        'status': inv.get('status') or inv.get('Status'),
        'subtotal': inv.get('subtotal') or inv.get('SubTotal'),
        'total_tax': inv.get('total_tax') or inv.get('TotalTax'),
        'total': inv.get('total') or inv.get('Total'),
        'has_attachments': inv.get('has_attachments') or inv.get('HasAttachments'),
        'is_discounted': inv.get('is_discounted') or inv.get('IsDiscounted'),
        'amount_due': inv.get('amount_due') or inv.get('AmountDue'),
        'amount_paid': inv.get('amount_paid') or inv.get('AmountPaid'),
        'amount_credited': inv.get('amount_credited') or inv.get('AmountCredited'),
        'updated_date_utc': parse_xero_date(inv.get('updated_date_utc') or inv.get('UpdatedDateUTC')),
        'has_errors': inv.get('has_errors') or inv.get('HasErrors'),
        'deleted_at': None,
    }
    sql_invoice = """
    INSERT INTO invoices (invoice_id, type, contact_id, contact_name, DATE, line_amount_types, invoice_number, reference, branding_theme_id, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, is_discounted, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors, deleted_at)
    VALUES (%(invoice_id)s, %(type)s, %(contact_id)s, %(contact_name)s, %(DATE)s, %(line_amount_types)s, %(invoice_number)s, %(reference)s, %(branding_theme_id)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(is_discounted)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s, %(deleted_at)s)
    ON DUPLICATE KEY UPDATE
        type=VALUES(type), contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), DATE=VALUES(DATE), line_amount_types=VALUES(line_amount_types), invoice_number=VALUES(invoice_number), reference=VALUES(reference), branding_theme_id=VALUES(branding_theme_id), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), is_discounted=VALUES(is_discounted), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors), deleted_at=NULL
    """
    db.execute(sql_invoice, invoice_row)
    line_items = inv.get('line_items') or inv.get('LineItems') or []
    for li in line_items:
        line_item_id = li.get('line_item_id') or li.get('LineItemID')
        line_item_row = {
            'line_item_id': line_item_id,
            'invoice_id': invoice_row['invoice_id'],
            'description': li.get('description') or li.get('Description'),
            'quantity': li.get('quantity') or li.get('Quantity'),
            'unit_amount': li.get('unit_amount') or li.get('UnitAmount'),
            'item_code': li.get('item_code') or li.get('ItemCode'),
            'account_code': li.get('account_code') or li.get('AccountCode'),
            'account_id': li.get('account_id') or li.get('AccountID'),
            'tax_type': li.get('tax_type') or li.get('TaxType'),
            'tax_amount': li.get('tax_amount') or li.get('TaxAmount'),
            'line_amount': li.get('line_amount') or li.get('LineAmount'),
            'item_id': li.get('item_id') or li.get('ItemID'),
            'item_name': li.get('item_name') or li.get('ItemName'),
            'deleted_at': None,
        }
        sql_line_item = """
        INSERT INTO line_items (line_item_id, invoice_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name, deleted_at)
        VALUES (%(line_item_id)s, %(invoice_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            invoice_id=VALUES(invoice_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name), deleted_at=NULL
        """
        db.execute(sql_line_item, line_item_row)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function webhook receiver for Xero invoice events."""
    logging.info('Xero webhook received.')

    try:
        intent_header = req.headers.get('x-xero-intent')
        if intent_header:
            logging.info(f"Received Xero intent to receive: {intent_header}")
            return func.HttpResponse(intent_header, status_code=200, mimetype='text/plain')

        if req.method != 'POST':
            return func.HttpResponse(
                json.dumps({'error': 'Only POST method allowed'}),
                status_code=405,
                mimetype='application/json'
            )

        try:
            raw_body = req.get_body().decode('utf-8')
            data = json.loads(raw_body)
        except Exception as e:
            logging.error(f"Failed to parse request body: {str(e)}")
            return func.HttpResponse(
                json.dumps({'error': 'Invalid JSON', 'details': str(e)}),
                status_code=400,
                mimetype='application/json'
            )

        signature_header = req.headers.get('x-xero-signature')
        if signature_header and XERO_WEBHOOK_KEY:
            if not verify_signature(raw_body, signature_header, XERO_WEBHOOK_KEY):
                logging.error("Invalid webhook signature")
                return func.HttpResponse(
                    json.dumps({'error': 'Invalid signature'}),
                    status_code=401,
                    mimetype='application/json'
                )

        events = data.get('events', [])
        if not events:
            return func.HttpResponse(
                json.dumps({'status': 'success', 'message': 'No events to process'}),
                status_code=200,
                mimetype='application/json'
            )

        processed_count = 0
        for event in events:
            try:
                tenant_id = event.get('tenantId')
                resource_url = event.get('resourceUrl')
                event_category = event.get('eventCategory')
                event_type = event.get('eventType')

                logging.info(f"Processing event: {event_category}.{event_type} for tenant {tenant_id}")

                if event_category == 'INVOICE' and tenant_id:
                    sync_date = datetime.now(timezone.utc)
                    invoice_id = resource_url.split('/')[-1] if resource_url else None

                    if invoice_id:
                        try:
                            xero_client = XeroClient()
                            invoice_data = xero_client.get_invoice(str(invoice_id), tenant_id)
                            sync_single_invoice_to_db(invoice_data, tenant_id, sync_date)
                            logging.info(f"Invoice {invoice_id} synced for tenant {tenant_id}")
                        except Exception as sync_exc:
                            logging.error(f"Failed to sync invoice {invoice_id}: {sync_exc}")

                    processed_count += 1

            except Exception as e:
                logging.error(f"Error processing event: {str(e)}")
                continue

        return func.HttpResponse(
            json.dumps({'status': 'success', 'processed_events': processed_count}),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': 'Internal server error'}),
            status_code=500,
            mimetype='application/json'
        )
