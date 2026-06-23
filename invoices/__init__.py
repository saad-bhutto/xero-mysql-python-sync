import logging
import json
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
import re
from dateutil import parser
import os

# Set up error logging to file
logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_invoices_to_db(invoices_data, tenant_id, sync_date):
    db = MySQLHelper()
    invoices = invoices_data.get('Invoices', []) if isinstance(invoices_data, dict) else invoices_data
    xero_invoice_ids = set()
    xero_line_item_ids = set()
    for inv in invoices:
        invoice_id = inv.get('invoice_id') or inv.get('InvoiceID')
        xero_invoice_ids.add(invoice_id)
        invoice_row = {
            'invoice_id': invoice_id,
            'type': inv.get('type') or inv.get('Type'),
            'contact_id': (inv.get('contact', {}) or {}).get('contact_id') or (inv.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (inv.get('contact', {}) or {}).get('name') or (inv.get('Contact', {}) or {}).get('Name'),
            'DATE': parse_xero_date(inv.get('date') or inv.get('UpdatedDateUTC')),
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
        # Save line items
        line_items = inv.get('line_items') or inv.get('LineItems') or []
        for li in line_items:
            line_item_id = li.get('line_item_id') or li.get('LineItemID')
            xero_line_item_ids.add(line_item_id)
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
    # Soft delete invoices not in Xero for this day
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    sql_soft_delete_invoices = f"""
        UPDATE invoices SET deleted_at=UTC_TIMESTAMP()
        WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
        AND invoice_id NOT IN ({','.join(['%s']*len(xero_invoice_ids))})
    """
    if xero_invoice_ids:
        db.execute(sql_soft_delete_invoices, list(xero_invoice_ids))
    # Soft delete line items not in Xero for this day
    sql_soft_delete_line_items = f"""
        UPDATE line_items SET deleted_at=UTC_TIMESTAMP()
        WHERE invoice_id IN ({','.join(['%s']*len(xero_invoice_ids))})
        AND line_item_id NOT IN ({','.join(['%s']*len(xero_line_item_ids))})
    """
    if xero_invoice_ids and xero_line_item_ids:
        db.execute(sql_soft_delete_line_items, list(xero_invoice_ids) + list(xero_line_item_ids))

def sync_invoices(first_run=False):
    try:
        client = XeroClient()
        tenants = client.get_tenants()
        now = datetime.now(timezone.utc)
        sync_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = sync_date
        end_utc = sync_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_str = start_utc.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_utc.strftime('%Y-%m-%dT%H:%M:%S')
        six_months_ago = now - timedelta(days=SYNC_LOOKBACK_DAYS)
        from_date = six_months_ago.strftime('%Y-%m-%d')
        for tenant in tenants:
            tenant_id = tenant.get('tenant_id') or tenant.get('tenantId')
            try:
                if first_run:
                    invoices_data = client.get_invoices(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    invoices_data = client.get_invoices(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = invoices_data.get('Invoices', [])
                if filtered:
                    save_invoices_to_db({'Invoices': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} invoice sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Invoice sync main error: {str(e)}")

def main(myInvoicesTimer):
    sync_invoices(first_run=False)
