import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_bank_transfers_to_db(bt_data, tenant_id, sync_date):
    db = MySQLHelper()
    bank_transfers = bt_data.get('BankTransfers', []) if isinstance(bt_data, dict) else bt_data
    xero_bt_ids = set()
    for bt in bank_transfers:
        bt_id = bt.get('bank_transfer_id') or bt.get('BankTransferID')
        xero_bt_ids.add(bt_id)
        bt_row = {
            'bank_transfer_id': bt_id,
            'from_bank_account_id': (bt.get('from_bank_account', {}) or {}).get('account_id') or (bt.get('FromBankAccount', {}) or {}).get('AccountID'),
            'to_bank_account_id': (bt.get('to_bank_account', {}) or {}).get('account_id') or (bt.get('ToBankAccount', {}) or {}).get('AccountID'),
            'amount': bt.get('amount') or bt.get('Amount'),
            'date': parse_xero_date(bt.get('date') or bt.get('Date')),
            'reference': bt.get('reference') or bt.get('Reference'),
            'currency_code': bt.get('currency_code') or bt.get('CurrencyCode'),
            'currency_rate': bt.get('currency_rate') or bt.get('CurrencyRate'),
            'status': bt.get('status') or bt.get('Status'),
            'updated_date_utc': parse_xero_date(bt.get('updated_date_utc') or bt.get('UpdatedDateUTC')),
            'has_attachments': bt.get('has_attachments') or bt.get('HasAttachments'),
            'has_errors': bt.get('has_errors') or bt.get('HasErrors'),
            'deleted_at': None,
        }
        sql_bt = """
        INSERT INTO bank_transfers (bank_transfer_id, from_bank_account_id, to_bank_account_id, amount, date, reference, currency_code, currency_rate, status, updated_date_utc, has_attachments, has_errors, deleted_at)
        VALUES (%(bank_transfer_id)s, %(from_bank_account_id)s, %(to_bank_account_id)s, %(amount)s, %(date)s, %(reference)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(updated_date_utc)s, %(has_attachments)s, %(has_errors)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            from_bank_account_id=VALUES(from_bank_account_id), to_bank_account_id=VALUES(to_bank_account_id), amount=VALUES(amount), date=VALUES(date), reference=VALUES(reference), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), updated_date_utc=VALUES(updated_date_utc), has_attachments=VALUES(has_attachments), has_errors=VALUES(has_errors), deleted_at=NULL
        """
        db.execute(sql_bt, bt_row)
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    sql_soft_delete_bt = f"""
        UPDATE bank_transfers SET deleted_at=UTC_TIMESTAMP()
        WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
        AND bank_transfer_id NOT IN ({','.join(['%s']*len(xero_bt_ids))})
    """
    if xero_bt_ids:
        db.execute(sql_soft_delete_bt, list(xero_bt_ids))

def sync_bank_transfers(first_run=False):
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
                    bt_data = client.get_bank_transfers(
                        tenant_id=tenant_id,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    bt_data = client.get_bank_transfers(
                        tenant_id=tenant_id,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = bt_data.get('BankTransfers', [])
                print(f"Filtered {len(filtered)} bank transfers for tenant {tenant_id}")
                if filtered:
                    save_bank_transfers_to_db({'BankTransfers': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} bank transfer sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Bank transfer sync main error: {str(e)}")

def main(myBankTransfersTimer):
    sync_bank_transfers(first_run=False)
