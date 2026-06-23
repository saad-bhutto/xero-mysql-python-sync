import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_credit_notes_to_db(cn_data, tenant_id, sync_date):
    db = MySQLHelper()
    credit_notes = cn_data.get('CreditNotes', []) if isinstance(cn_data, dict) else cn_data
    xero_cn_ids = set()
    xero_item_ids = set()
    for cn in credit_notes:
        cn_id = cn.get('credit_note_id') or cn.get('CreditNoteID')
        xero_cn_ids.add(cn_id)
        cn_row = {
            'credit_note_id': cn_id,
            'type': cn.get('type') or cn.get('Type'),
            'contact_id': (cn.get('contact', {}) or {}).get('contact_id') or (cn.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (cn.get('contact', {}) or {}).get('name') or (cn.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(cn.get('date') or cn.get('Date')),
            'line_amount_types': cn.get('line_amount_types') or cn.get('LineAmountTypes'),
            'credit_note_number': cn.get('credit_note_number') or cn.get('CreditNoteNumber'),
            'reference': cn.get('reference') or cn.get('Reference'),
            'branding_theme_id': cn.get('branding_theme_id') or cn.get('BrandingThemeID'),
            'currency_code': cn.get('currency_code') or cn.get('CurrencyCode'),
            'currency_rate': cn.get('currency_rate') or cn.get('CurrencyRate'),
            'status': cn.get('status') or cn.get('Status'),
            'subtotal': cn.get('subtotal') or cn.get('SubTotal'),
            'total_tax': cn.get('total_tax') or cn.get('TotalTax'),
            'total': cn.get('total') or cn.get('Total'),
            'has_attachments': cn.get('has_attachments') or cn.get('HasAttachments'),
            'is_discounted': cn.get('is_discounted') or cn.get('IsDiscounted'),
            'amount_due': cn.get('amount_due') or cn.get('AmountDue'),
            'amount_paid': cn.get('amount_paid') or cn.get('AmountPaid'),
            'amount_credited': cn.get('amount_credited') or cn.get('AmountCredited'),
            'updated_date_utc': parse_xero_date(cn.get('updated_date_utc') or cn.get('UpdatedDateUTC')),
            'has_errors': cn.get('has_errors') or cn.get('HasErrors'),
        }
        sql_cn = """
        INSERT INTO credit_notes (credit_note_id, type, contact_id, contact_name, date, line_amount_types, credit_note_number, reference, branding_theme_id, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, is_discounted, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors)
        VALUES (%(credit_note_id)s, %(type)s, %(contact_id)s, %(contact_name)s, %(date)s, %(line_amount_types)s, %(credit_note_number)s, %(reference)s, %(branding_theme_id)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(is_discounted)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s)
        ON DUPLICATE KEY UPDATE
            type=VALUES(type), contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), line_amount_types=VALUES(line_amount_types), credit_note_number=VALUES(credit_note_number), reference=VALUES(reference), branding_theme_id=VALUES(branding_theme_id), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), is_discounted=VALUES(is_discounted), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors)
        """
        db.execute(sql_cn, cn_row)
        items = cn.get('line_items') or cn.get('LineItems') or []
        for item in items:
            item_id = item.get('line_item_id') or item.get('LineItemID')
            xero_item_ids.add(item_id)
            item_row = {
                'line_item_id': item_id,
                'credit_note_id': cn_id,
                'description': item.get('description') or item.get('Description'),
                'quantity': item.get('quantity') or item.get('Quantity'),
                'unit_amount': item.get('unit_amount') or item.get('UnitAmount'),
                'item_code': item.get('item_code') or item.get('ItemCode'),
                'account_code': item.get('account_code') or item.get('AccountCode'),
                'account_id': item.get('account_id') or item.get('AccountID'),
                'tax_type': item.get('tax_type') or item.get('TaxType'),
                'tax_amount': item.get('tax_amount') or item.get('TaxAmount'),
                'line_amount': item.get('line_amount') or item.get('LineAmount'),
                'item_id': item.get('item_id') or item.get('ItemID'),
                'item_name': item.get('item_name') or item.get('ItemName'),
            }
            sql_item = """
            INSERT INTO credit_note_items (line_item_id, credit_note_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name)
            VALUES (%(line_item_id)s, %(credit_note_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s)
            ON DUPLICATE KEY UPDATE
                credit_note_id=VALUES(credit_note_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name)
            """
            db.execute(sql_item, item_row)

def sync_credit_notes(first_run=False):
    try:
        client = XeroClient()
        tenants = client.get_tenants()
        now = datetime.now(timezone.utc)
        sync_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_utc = sync_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        end_str = end_utc.strftime('%Y-%m-%dT%H:%M:%S')
        six_months_ago = now - timedelta(days=SYNC_LOOKBACK_DAYS)
        from_date = six_months_ago.strftime('%Y-%m-%d')
        for tenant in tenants:
            tenant_id = tenant.get('tenant_id') or tenant.get('tenantId')
            try:
                if first_run:
                    cn_data = client.get_credit_notes(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    cn_data = client.get_credit_notes(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = cn_data.get('CreditNotes', [])
                if filtered:
                    print(f"Saving {len(filtered)} credit notes to DB for tenant {tenant_id}")
                    save_credit_notes_to_db({'CreditNotes': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} credit note sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Credit note sync main error: {str(e)}")

def main(myCreditNotesTimer):
    sync_credit_notes(first_run=False)
