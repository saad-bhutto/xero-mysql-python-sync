import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.environ.get('SYNC_LOOKBACK_DAYS', 60))

def save_payments_to_db(payments_data, tenant_id, sync_date):
    db = MySQLHelper()
    payments = payments_data.get('Payments', []) if isinstance(payments_data, dict) else payments_data
    xero_payment_ids = set()
    for payment in payments:
        payment_id = payment.get('payment_id') or payment.get('PaymentID')
        xero_payment_ids.add(payment_id)
        payment_row = {
            'payment_id': payment_id,
            'invoice_id': payment.get('invoice_id') or payment.get('InvoiceID'),
            'credit_note_id': payment.get('credit_note_id') or payment.get('CreditNoteID'),
            'prepayment_id': payment.get('prepayment_id') or payment.get('PrepaymentID'),
            'overpayment_id': payment.get('overpayment_id') or payment.get('OverpaymentID'),
            'account_id': (payment.get('account', {}) or {}).get('account_id') or (payment.get('Account', {}) or {}).get('AccountID'),
            'account_code': (payment.get('account', {}) or {}).get('code') or (payment.get('Account', {}) or {}).get('Code'),
            'reference': payment.get('reference') or payment.get('Reference'),
            'currency_code': payment.get('currency_code') or payment.get('CurrencyCode'),
            'currency_rate': payment.get('currency_rate') or payment.get('CurrencyRate'),
            'date': parse_xero_date(payment.get('date') or payment.get('Date')),
            'amount': payment.get('amount') or payment.get('Amount'),
            'status': payment.get('status') or payment.get('Status'),
            'type': payment.get('type') or payment.get('Type'),
            'updated_date_utc': parse_xero_date(payment.get('updated_date_utc') or payment.get('UpdatedDateUTC')),
        }
        sql_payment = """
        INSERT INTO payments (payment_id, invoice_id, credit_note_id, prepayment_id, overpayment_id, account_id, account_code, reference, currency_code, currency_rate, date, amount, status, type, updated_date_utc)
        VALUES (%(payment_id)s, %(invoice_id)s, %(credit_note_id)s, %(prepayment_id)s, %(overpayment_id)s, %(account_id)s, %(account_code)s, %(reference)s, %(currency_code)s, %(currency_rate)s, %(date)s, %(amount)s, %(status)s, %(type)s, %(updated_date_utc)s)
        ON DUPLICATE KEY UPDATE
            invoice_id=VALUES(invoice_id), credit_note_id=VALUES(credit_note_id), prepayment_id=VALUES(prepayment_id), overpayment_id=VALUES(overpayment_id), account_id=VALUES(account_id), account_code=VALUES(account_code), reference=VALUES(reference), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), date=VALUES(date), amount=VALUES(amount), status=VALUES(status), type=VALUES(type), updated_date_utc=VALUES(updated_date_utc)
        """
        db.execute(sql_payment, payment_row)
        # Save allocations if present
        allocations = payment.get('allocations') or payment.get('Allocations') or []
        for alloc in allocations:
            alloc_row = {
                'payment_id': payment_id,
                'applied_to_id': alloc.get('applied_to_id') or alloc.get('AppliedToID'),
                'applied_to_type': alloc.get('applied_to_type') or alloc.get('AppliedToType'),
                'amount': alloc.get('amount') or alloc.get('Amount'),
            }
            sql_alloc = """
            INSERT INTO payment_allocations (payment_id, applied_to_id, applied_to_type, amount)
            VALUES (%(payment_id)s, %(applied_to_id)s, %(applied_to_type)s, %(amount)s)
            ON DUPLICATE KEY UPDATE
                applied_to_id=VALUES(applied_to_id), applied_to_type=VALUES(applied_to_type), amount=VALUES(amount)
            """
            db.execute(sql_alloc, alloc_row)
    # Soft delete logic can be added here if needed, similar to invoices

def sync_payments(first_run=False):
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
                    payments_data = client.get_payments(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    payments_data = client.get_payments(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = payments_data.get('Payments', [])
                print(f"Filtered {len(filtered)} payments for tenant {tenant_id}")
                if filtered:
                    print(f"Saving {len(filtered)} filtered payments to DB for tenant {tenant_id}")
                    save_payments_to_db({'Payments': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} payments sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Payments sync main error: {str(e)}")

def main(myPaymentsTimer):
    sync_payments(first_run=False)
