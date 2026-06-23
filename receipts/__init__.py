import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_receipts_to_db(receipts_data, tenant_id, sync_date):
    db = MySQLHelper()
    receipts = receipts_data.get('Receipts', []) if isinstance(receipts_data, dict) else receipts_data
    xero_receipt_ids = set()
    xero_receipt_line_item_ids = set()
    for receipt in receipts:
        receipt_id = receipt.get('receipt_id') or receipt.get('ReceiptID')
        xero_receipt_ids.add(receipt_id)
        receipt_row = {
            'receipt_id': receipt_id,
            'contact_id': (receipt.get('contact', {}) or {}).get('contact_id') or (receipt.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (receipt.get('contact', {}) or {}).get('name') or (receipt.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(receipt.get('date') or receipt.get('Date')),
            'line_amount_types': receipt.get('line_amount_types') or receipt.get('LineAmountTypes'),
            'reference': receipt.get('reference') or receipt.get('Reference'),
            'currency_code': receipt.get('currency_code') or receipt.get('CurrencyCode'),
            'currency_rate': receipt.get('currency_rate') or receipt.get('CurrencyRate'),
            'status': receipt.get('status') or receipt.get('Status'),
            'subtotal': receipt.get('subtotal') or receipt.get('SubTotal'),
            'total_tax': receipt.get('total_tax') or receipt.get('TotalTax'),
            'total': receipt.get('total') or receipt.get('Total'),
            'has_attachments': receipt.get('has_attachments') or receipt.get('HasAttachments'),
            'amount_due': receipt.get('amount_due') or receipt.get('AmountDue'),
            'amount_paid': receipt.get('amount_paid') or receipt.get('AmountPaid'),
            'amount_credited': receipt.get('amount_credited') or receipt.get('AmountCredited'),
            'updated_date_utc': parse_xero_date(receipt.get('updated_date_utc') or receipt.get('UpdatedDateUTC')),
            'has_errors': receipt.get('has_errors') or receipt.get('HasErrors'),
            'deleted_at': None,
        }
        sql_receipt = """
        INSERT INTO receipts (receipt_id, contact_id, contact_name, date, line_amount_types, reference, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors, deleted_at)
        VALUES (%(receipt_id)s, %(contact_id)s, %(contact_name)s, %(date)s, %(line_amount_types)s, %(reference)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), line_amount_types=VALUES(line_amount_types), reference=VALUES(reference), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors), deleted_at=NULL
        """
        db.execute(sql_receipt, receipt_row)
        line_items = receipt.get('line_items') or receipt.get('LineItems') or []
        for li in line_items:
            line_item_id = li.get('line_item_id') or li.get('LineItemID')
            xero_receipt_line_item_ids.add(line_item_id)
            line_item_row = {
                'line_item_id': line_item_id,
                'receipt_id': receipt_row['receipt_id'],
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
            INSERT INTO receipt_line_items (line_item_id, receipt_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name, deleted_at)
            VALUES (%(line_item_id)s, %(receipt_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s, %(deleted_at)s)
            ON DUPLICATE KEY UPDATE
                receipt_id=VALUES(receipt_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name), deleted_at=NULL
            """
            db.execute(sql_line_item, line_item_row)
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    if xero_receipt_ids:
        sql_soft_delete = f"""
            UPDATE receipts SET deleted_at=UTC_TIMESTAMP()
            WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
            AND receipt_id NOT IN ({','.join(['%s']*len(xero_receipt_ids))})
        """
        db.execute(sql_soft_delete, list(xero_receipt_ids))
    if xero_receipt_ids and xero_receipt_line_item_ids:
        sql_soft_delete_li = f"""
            UPDATE receipt_line_items SET deleted_at=UTC_TIMESTAMP()
            WHERE receipt_id IN ({','.join(['%s']*len(xero_receipt_ids))})
            AND line_item_id NOT IN ({','.join(['%s']*len(xero_receipt_line_item_ids))})
        """
        db.execute(sql_soft_delete_li, list(xero_receipt_ids) + list(xero_receipt_line_item_ids))

def sync_receipts(first_run=False):
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
                    receipts_data = client.get_receipts(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    receipts_data = client.get_receipts(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = receipts_data.get('Receipts', [])
                print(f"Filtered {len(filtered)} receipts for tenant {tenant_id}")
                if filtered:
                    save_receipts_to_db({'Receipts': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} receipt sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Receipt sync main error: {str(e)}")

def main(recTimer):
    sync_receipts(first_run=False)
