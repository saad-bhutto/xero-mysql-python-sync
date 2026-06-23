import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_linked_transactions_to_db(lt_data, tenant_id, sync_date):
    db = MySQLHelper()
    linked_transactions = lt_data.get('LinkedTransactions', []) if isinstance(lt_data, dict) else lt_data
    xero_lt_ids = set()
    for lt in linked_transactions:
        lt_id = lt.get('linked_transaction_id') or lt.get('LinkedTransactionID')
        xero_lt_ids.add(lt_id)
        lt_row = {
            'linked_transaction_id': lt_id,
            'source_transaction_id': lt.get('source_transaction_id') or lt.get('SourceTransactionID'),
            'source_line_item_id': lt.get('source_line_item_id') or lt.get('SourceLineItemID'),
            'contact_id': (lt.get('contact', {}) or {}).get('contact_id') or (lt.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (lt.get('contact', {}) or {}).get('name') or (lt.get('Contact', {}) or {}).get('Name'),
            'status': lt.get('status') or lt.get('Status'),
            'type': lt.get('type') or lt.get('Type'),
            'description': lt.get('description') or lt.get('Description'),
            'updated_date_utc': parse_xero_date(lt.get('updated_date_utc') or lt.get('UpdatedDateUTC')),
            'amount': lt.get('amount') or lt.get('Amount'),
            'has_errors': lt.get('has_errors') or lt.get('HasErrors'),
            'deleted_at': None,
        }
        sql_lt = """
        INSERT INTO linked_transactions (linked_transaction_id, source_transaction_id, source_line_item_id, contact_id, contact_name, status, type, description, updated_date_utc, amount, has_errors, deleted_at)
        VALUES (%(linked_transaction_id)s, %(source_transaction_id)s, %(source_line_item_id)s, %(contact_id)s, %(contact_name)s, %(status)s, %(type)s, %(description)s, %(updated_date_utc)s, %(amount)s, %(has_errors)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            source_transaction_id=VALUES(source_transaction_id), source_line_item_id=VALUES(source_line_item_id), contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), status=VALUES(status), type=VALUES(type), description=VALUES(description), updated_date_utc=VALUES(updated_date_utc), amount=VALUES(amount), has_errors=VALUES(has_errors), deleted_at=NULL
        """
        db.execute(sql_lt, lt_row)
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    if xero_lt_ids:
        sql_soft_delete = f"""
            UPDATE linked_transactions SET deleted_at=UTC_TIMESTAMP()
            WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
            AND linked_transaction_id NOT IN ({','.join(['%s']*len(xero_lt_ids))})
        """
        db.execute(sql_soft_delete, list(xero_lt_ids))

def sync_linked_transactions(first_run=False):
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
                    lt_data = client.get_linked_transactions(
                        tenant_id=tenant_id,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    lt_data = client.get_linked_transactions(
                        tenant_id=tenant_id,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = lt_data.get('LinkedTransactions', [])
                print(f"Filtered {len(filtered)} linked transactions for tenant {tenant_id}")
                if filtered:
                    save_linked_transactions_to_db({'LinkedTransactions': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} linked transaction sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Linked transaction sync main error: {str(e)}")

def main(myLinkedTransactionsTimer):
    sync_linked_transactions(first_run=False)
