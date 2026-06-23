import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.getenv('SYNC_LOOKBACK_DAYS', 60))

def save_expense_claims_to_db(expense_claims_data, tenant_id, sync_date):
    db = MySQLHelper()
    expense_claims = expense_claims_data.get('ExpenseClaims', []) if isinstance(expense_claims_data, dict) else expense_claims_data
    xero_ids = set()
    xero_li_ids = set()
    for claim in expense_claims:
        claim_id = claim.get('expense_claim_id') or claim.get('ExpenseClaimID')
        xero_ids.add(claim_id)
        claim_row = {
            'expense_claim_id': claim_id,
            'user_id': claim.get('user_id') or claim.get('UserID'),
            'user_name': claim.get('user_name') or claim.get('UserName'),
            'contact_id': (claim.get('contact', {}) or {}).get('contact_id') or (claim.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (claim.get('contact', {}) or {}).get('name') or (claim.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(claim.get('date') or claim.get('Date')),
            'expense_claim_number': claim.get('expense_claim_number') or claim.get('ExpenseClaimNumber'),
            'reference': claim.get('reference') or claim.get('Reference'),
            'currency_code': claim.get('currency_code') or claim.get('CurrencyCode'),
            'currency_rate': claim.get('currency_rate') or claim.get('CurrencyRate'),
            'status': claim.get('status') or claim.get('Status'),
            'subtotal': claim.get('subtotal') or claim.get('SubTotal'),
            'total_tax': claim.get('total_tax') or claim.get('TotalTax'),
            'total': claim.get('total') or claim.get('Total'),
            'has_attachments': claim.get('has_attachments') or claim.get('HasAttachments'),
            'amount_due': claim.get('amount_due') or claim.get('AmountDue'),
            'amount_paid': claim.get('amount_paid') or claim.get('AmountPaid'),
            'amount_credited': claim.get('amount_credited') or claim.get('AmountCredited'),
            'updated_date_utc': parse_xero_date(claim.get('updated_date_utc') or claim.get('UpdatedDateUTC')),
            'has_errors': claim.get('has_errors') or claim.get('HasErrors'),
            'deleted_at': None,
        }
        sql_claim = """
        INSERT INTO expense_claims (expense_claim_id, user_id, user_name, contact_id, contact_name, date, expense_claim_number, reference, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors, deleted_at)
        VALUES (%(expense_claim_id)s, %(user_id)s, %(user_name)s, %(contact_id)s, %(contact_name)s, %(date)s, %(expense_claim_number)s, %(reference)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s, %(deleted_at)s)
        ON DUPLICATE KEY UPDATE
            user_id=VALUES(user_id), user_name=VALUES(user_name), contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), expense_claim_number=VALUES(expense_claim_number), reference=VALUES(reference), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors), deleted_at=NULL
        """
        db.execute(sql_claim, claim_row)
        line_items = claim.get('line_items') or claim.get('LineItems') or []
        for li in line_items:
            li_id = li.get('line_item_id') or li.get('LineItemID')
            xero_li_ids.add(li_id)
            li_row = {
                'line_item_id': li_id,
                'expense_claim_id': claim_id,
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
            INSERT INTO expense_claim_line_items (line_item_id, expense_claim_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name, deleted_at)
            VALUES (%(line_item_id)s, %(expense_claim_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s, %(deleted_at)s)
            ON DUPLICATE KEY UPDATE
                expense_claim_id=VALUES(expense_claim_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name), deleted_at=NULL
            """
            db.execute(sql_li, li_row)
    start_str = sync_date.strftime('%Y-%m-%d 00:00:00')
    end_str = sync_date.strftime('%Y-%m-%d 23:59:59')
    if xero_ids:
        sql_soft_delete = f"""
            UPDATE expense_claims SET deleted_at=UTC_TIMESTAMP()
            WHERE updated_date_utc BETWEEN '{start_str}' AND '{end_str}'
            AND expense_claim_id NOT IN ({','.join(['%s']*len(xero_ids))})
        """
        db.execute(sql_soft_delete, list(xero_ids))
    if xero_ids and xero_li_ids:
        sql_soft_delete_li = f"""
            UPDATE expense_claim_line_items SET deleted_at=UTC_TIMESTAMP()
            WHERE expense_claim_id IN ({','.join(['%s']*len(xero_ids))})
            AND line_item_id NOT IN ({','.join(['%s']*len(xero_li_ids))})
        """
        db.execute(sql_soft_delete_li, list(xero_ids) + list(xero_li_ids))

def sync_expense_claims(first_run=False):
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
                    data = client.get_expense_claims(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    data = client.get_expense_claims(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = data.get('ExpenseClaims', [])
                print(f"Filtered {len(filtered)} expense claims for tenant {tenant_id}")
                if filtered:
                    save_expense_claims_to_db({'ExpenseClaims': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} expense claim sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Expense claim sync main error: {str(e)}")

def main(expClaimTimer):
    sync_expense_claims(first_run=False)
