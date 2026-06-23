import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_bank_transactions_to_db(bt_data, tenant_id, sync_date):
    db = MySQLHelper()
    bank_transactions = bt_data.get('BankTransactions', []) if isinstance(bt_data, dict) else bt_data
    xero_bt_ids = set()
    xero_line_item_ids = set()
    for bt in bank_transactions:
        bt_id = bt.get('bank_transaction_id') or bt.get('BankTransactionID')
        xero_bt_ids.add(bt_id)
        bt_row = {
            'bank_transaction_id': bt_id,
            'type': bt.get('type') or bt.get('Type'),
            'contact_id': (bt.get('contact', {}) or {}).get('contact_id') or (bt.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (bt.get('contact', {}) or {}).get('name') or (bt.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(bt.get('date') or bt.get('Date')),
            'line_amount_types': bt.get('line_amount_types') or bt.get('LineAmountTypes'),
            'reference': bt.get('reference') or bt.get('Reference'),
            'currency_code': bt.get('currency_code') or bt.get('CurrencyCode'),
            'currency_rate': bt.get('currency_rate') or bt.get('CurrencyRate'),
            'status': bt.get('status') or bt.get('Status'),
            'subtotal': bt.get('subtotal') or bt.get('SubTotal'),
            'total_tax': bt.get('total_tax') or bt.get('TotalTax'),
            'total': bt.get('total') or bt.get('Total'),
            'updated_date_utc': parse_xero_date(bt.get('updated_date_utc') or bt.get('UpdatedDateUTC')),
            'has_attachments': bt.get('has_attachments') or bt.get('HasAttachments'),
            'amount_paid': bt.get('amount_paid') or bt.get('AmountPaid'),
            'amount_due': bt.get('amount_due') or bt.get('AmountDue'),
            'amount_credited': bt.get('amount_credited') or bt.get('AmountCredited'),
            'has_errors': bt.get('has_errors') or bt.get('HasErrors'),
            'deleted_at': None,
        }
        sql_bt = """
        INSERT INTO bank_transactions (bank_transaction_id, type, contact_id, contact_name, date, line_amount_types, reference, currency_code, currency_rate, status, subtotal, total_tax, total, updated_date_utc, has_attachments, amount_paid, amount_due, amount_credited, has_errors, deleted_at)
        VALUES (%(bank_transaction_id)s, %(type)s, %(contact_id)s, %(contact_name)s, %(date)s, %(line_amount_types)s, %(reference)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(updated_date_utc)s, %(has_attachments)s, %(amount_paid)s, %(amount_due)s, %(amount_credited)s, %(has_errors)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            type=VALUES(type), contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), line_amount_types=VALUES(line_amount_types), reference=VALUES(reference), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), updated_date_utc=VALUES(updated_date_utc), has_attachments=VALUES(has_attachments), amount_paid=VALUES(amount_paid), amount_due=VALUES(amount_due), amount_credited=VALUES(amount_credited), has_errors=VALUES(has_errors), deleted_at=NULL
        """
        db.execute(sql_bt, bt_row)
        # Save line items
        line_items = bt.get('line_items') or bt.get('LineItems') or []
        for li in line_items:
            line_item_id = li.get('line_item_id') or li.get('LineItemID')
            xero_line_item_ids.add(line_item_id)
            line_item_row = {
                'line_item_id': line_item_id,
                'bank_transaction_id': bt_row['bank_transaction_id'],
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
            INSERT INTO bank_transaction_line_items (line_item_id, bank_transaction_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name, deleted_at)
            VALUES (%(line_item_id)s, %(bank_transaction_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s, %(deleted_at)s)
            ON DUPLICATE KEY UPDATE
                bank_transaction_id=VALUES(bank_transaction_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name), deleted_at=NULL
            """
            db.execute(sql_line_item, line_item_row)
    # Soft delete logic for bank_transactions and line_items
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    sql_soft_delete_bt = f"""
        UPDATE bank_transactions SET deleted_at=UTC_TIMESTAMP()
        WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
        AND bank_transaction_id NOT IN ({','.join(['%s']*len(xero_bt_ids))})
    """
    if xero_bt_ids:
        db.execute(sql_soft_delete_bt, list(xero_bt_ids))
    sql_soft_delete_line_items = f"""
        UPDATE bank_transaction_line_items SET deleted_at=UTC_TIMESTAMP()
        WHERE bank_transaction_id IN ({','.join(['%s']*len(xero_bt_ids))})
        AND line_item_id NOT IN ({','.join(['%s']*len(xero_line_item_ids))})
    """
    if xero_bt_ids and xero_line_item_ids:
        db.execute(sql_soft_delete_line_items, list(xero_bt_ids) + list(xero_line_item_ids))

def sync_bank_transactions(first_run=False):
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
                    bt_data = client.get_bank_transactions(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    bt_data = client.get_bank_transactions(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = bt_data.get('BankTransactions', [])
                print(f"Filtered {len(filtered)} bank transactions for tenant {tenant_id}")
                if filtered:
                    print(f"Saving {len(filtered)} filtered bank transactions to DB for tenant {tenant_id}")
                    save_bank_transactions_to_db({'BankTransactions': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} bank transaction sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Bank transaction sync main error: {str(e)}")

def main(myBankTransactionsTimer):
    sync_bank_transactions(first_run=False)
