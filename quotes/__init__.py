import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
from xero_utils import parse_xero_date
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.environ.get('SYNC_LOOKBACK_DAYS', 60))

def save_quotes_to_db(quotes_data, tenant_id, sync_date):
    db = MySQLHelper()
    quotes = quotes_data.get('Quotes', []) if isinstance(quotes_data, dict) else quotes_data
    xero_quote_ids = set()
    xero_item_ids = set()
    for quote in quotes:
        quote_id = quote.get('quote_id') or quote.get('QuoteID')
        xero_quote_ids.add(quote_id)
        quote_row = {
            'quote_id': quote_id,
            'contact_id': (quote.get('contact', {}) or {}).get('contact_id') or (quote.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (quote.get('contact', {}) or {}).get('name') or (quote.get('Contact', {}) or {}).get('Name'),
            'quote_number': quote.get('quote_number') or quote.get('QuoteNumber'),
            'reference': quote.get('reference') or quote.get('Reference'),
            'status': quote.get('status') or quote.get('Status'),
            'title': quote.get('title') or quote.get('Title'),
            'summary': quote.get('summary') or quote.get('Summary'),
            'currency_code': quote.get('currency_code') or quote.get('CurrencyCode'),
            'currency_rate': quote.get('currency_rate') or quote.get('CurrencyRate'),
            'date': parse_xero_date(quote.get('date') or quote.get('Date')),
            'expiry_date': parse_xero_date(quote.get('expiry_date') or quote.get('ExpiryDate')),
            'line_amount_types': quote.get('line_amount_types') or quote.get('LineAmountTypes'),
            'subtotal': quote.get('subtotal') or quote.get('SubTotal'),
            'total_tax': quote.get('total_tax') or quote.get('TotalTax'),
            'total': quote.get('total') or quote.get('Total'),
            'updated_date_utc': parse_xero_date(quote.get('updated_date_utc') or quote.get('UpdatedDateUTC')),
            'has_attachments': quote.get('has_attachments') or quote.get('HasAttachments'),
            'has_errors': quote.get('has_errors') or quote.get('HasErrors'),
        }
        sql_quote = """
        INSERT INTO quotes (quote_id, contact_id, contact_name, quote_number, reference, status, title, summary, currency_code, currency_rate, date, expiry_date, line_amount_types, subtotal, total_tax, total, updated_date_utc, has_attachments, has_errors)
        VALUES (%(quote_id)s, %(contact_id)s, %(contact_name)s, %(quote_number)s, %(reference)s, %(status)s, %(title)s, %(summary)s, %(currency_code)s, %(currency_rate)s, %(date)s, %(expiry_date)s, %(line_amount_types)s, %(subtotal)s, %(total_tax)s, %(total)s, %(updated_date_utc)s, %(has_attachments)s, %(has_errors)s)
        ON DUPLICATE KEY UPDATE
            contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), quote_number=VALUES(quote_number), reference=VALUES(reference), status=VALUES(status), title=VALUES(title), summary=VALUES(summary), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), date=VALUES(date), expiry_date=VALUES(expiry_date), line_amount_types=VALUES(line_amount_types), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), updated_date_utc=VALUES(updated_date_utc), has_attachments=VALUES(has_attachments), has_errors=VALUES(has_errors)
        """
        db.execute(sql_quote, quote_row)
        items = quote.get('line_items') or quote.get('LineItems') or []
        for item in items:
            item_id = item.get('line_item_id') or item.get('LineItemID')
            xero_item_ids.add(item_id)
            item_row = {
                'line_item_id': item_id,
                'quote_id': quote_id,
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
            INSERT INTO quote_items (line_item_id, quote_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name)
            VALUES (%(line_item_id)s, %(quote_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s)
            ON DUPLICATE KEY UPDATE
                quote_id=VALUES(quote_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name)
            """
            db.execute(sql_item, item_row)

def sync_quotes(first_run=False):
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
                    quotes_data = client.get_quotes(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    quotes_data = client.get_quotes(
                        tenant_id=tenant_id,
                        statuses=None,
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = quotes_data.get('Quotes', [])
                print(f"Filtered {len(filtered)} quotes for tenant {tenant_id}")
                if filtered:
                    save_quotes_to_db({'Quotes': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} quotes sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Quotes sync main error: {str(e)}")

def main(myQuotesTimer):
    sync_quotes(first_run=False)
