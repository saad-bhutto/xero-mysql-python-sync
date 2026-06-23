import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_repeating_invoices_to_db(repeating_invoices_data, tenant_id, sync_date):
    db = MySQLHelper()
    repeating_invoices = repeating_invoices_data.get('RepeatingInvoices', []) if isinstance(repeating_invoices_data, dict) else repeating_invoices_data
    xero_ids = set()
    xero_li_ids = set()
    for ri in repeating_invoices:
        ri_id = ri.get('repeating_invoice_id') or ri.get('RepeatingInvoiceID')
        xero_ids.add(ri_id)
        ri_row = {
            'repeating_invoice_id': ri_id,
            'contact_id': (ri.get('contact', {}) or {}).get('contact_id') or (ri.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (ri.get('contact', {}) or {}).get('name') or (ri.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(ri.get('date') or ri.get('Date')),
            'line_amount_types': ri.get('line_amount_types') or ri.get('LineAmountTypes'),
            'reference': ri.get('reference') or ri.get('Reference'),
            'branding_theme_id': ri.get('branding_theme_id') or ri.get('BrandingThemeID'),
            'currency_code': ri.get('currency_code') or ri.get('CurrencyCode'),
            'currency_rate': ri.get('currency_rate') or ri.get('CurrencyRate'),
            'status': ri.get('status') or ri.get('Status'),
            'subtotal': ri.get('subtotal') or ri.get('SubTotal'),
            'total_tax': ri.get('total_tax') or ri.get('TotalTax'),
            'total': ri.get('total') or ri.get('Total'),
            'has_attachments': ri.get('has_attachments') or ri.get('HasAttachments'),
            'is_discounted': ri.get('is_discounted') or ri.get('IsDiscounted'),
            'amount_due': ri.get('amount_due') or ri.get('AmountDue'),
            'amount_paid': ri.get('amount_paid') or ri.get('AmountPaid'),
            'amount_credited': ri.get('amount_credited') or ri.get('AmountCredited'),
            'updated_date_utc': parse_xero_date(ri.get('updated_date_utc') or ri.get('UpdatedDateUTC')),
            'has_errors': ri.get('has_errors') or ri.get('HasErrors'),
            'schedule_type': ri.get('schedule_type') or ri.get('ScheduleType'),
            'schedule_every': ri.get('schedule_every') or ri.get('ScheduleEvery'),
            'schedule_start_date': parse_xero_date(ri.get('schedule_start_date') or ri.get('ScheduleStartDate')),
            'schedule_end_date': parse_xero_date(ri.get('schedule_end_date') or ri.get('ScheduleEndDate')),
            'deleted_at': None,
        }
        sql_ri = """
        INSERT INTO repeating_invoices (repeating_invoice_id, contact_id, contact_name, date, line_amount_types, reference, branding_theme_id, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, is_discounted, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors, schedule_type, schedule_every, schedule_start_date, schedule_end_date, deleted_at)
        VALUES (%(repeating_invoice_id)s, %(contact_id)s, %(contact_name)s, %(date)s, %(line_amount_types)s, %(reference)s, %(branding_theme_id)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(is_discounted)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s, %(schedule_type)s, %(schedule_every)s, %(schedule_start_date)s, %(schedule_end_date)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), line_amount_types=VALUES(line_amount_types), reference=VALUES(reference), branding_theme_id=VALUES(branding_theme_id), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), is_discounted=VALUES(is_discounted), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors), schedule_type=VALUES(schedule_type), schedule_every=VALUES(schedule_every), schedule_start_date=VALUES(schedule_start_date), schedule_end_date=VALUES(schedule_end_date), deleted_at=NULL
        """
        db.execute(sql_ri, ri_row)
        line_items = ri.get('line_items') or ri.get('LineItems') or []
        for li in line_items:
            li_id = li.get('line_item_id') or li.get('LineItemID')
            xero_li_ids.add(li_id)
            li_row = {
                'line_item_id': li_id,
                'repeating_invoice_id': ri_id,
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
            sql_li = """
            INSERT INTO repeating_invoice_line_items (line_item_id, repeating_invoice_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name, deleted_at)
            VALUES (%(line_item_id)s, %(repeating_invoice_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s, %(deleted_at)s)
            ON DUPLICATE KEY UPDATE
                repeating_invoice_id=VALUES(repeating_invoice_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name), deleted_at=NULL
            """
            db.execute(sql_li, li_row)
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    if xero_ids:
        sql_soft_delete = f"""
            UPDATE repeating_invoices SET deleted_at=UTC_TIMESTAMP()
            WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
            AND repeating_invoice_id NOT IN ({','.join(['%s']*len(xero_ids))})
        """
        db.execute(sql_soft_delete, list(xero_ids))
    if xero_ids and xero_li_ids:
        sql_soft_delete_li = f"""
            UPDATE repeating_invoice_line_items SET deleted_at=UTC_TIMESTAMP()
            WHERE repeating_invoice_id IN ({','.join(['%s']*len(xero_ids))})
            AND line_item_id NOT IN ({','.join(['%s']*len(xero_li_ids))})
        """
        db.execute(sql_soft_delete_li, list(xero_ids) + list(xero_li_ids))

def sync_repeating_invoices(first_run=False):
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
                    data = client.get_repeating_invoices(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    data = client.get_repeating_invoices(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = data.get('RepeatingInvoices', [])
                print(f"Filtered {len(filtered)} repeating invoices for tenant {tenant_id}")
                if filtered:
                    save_repeating_invoices_to_db({'RepeatingInvoices': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} repeating invoice sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Repeating invoice sync main error: {str(e)}")

def main(timer):
    sync_repeating_invoices(first_run=False)
