import logging
from xero_client import XeroClient, MySQLHelper
from datetime import datetime, timedelta, timezone
import re
from dateutil import parser
import os

logging.basicConfig(filename='error.log', level=logging.ERROR)

SYNC_LOOKBACK_DAYS = int(os.environ.get('SYNC_LOOKBACK_DAYS', 60))

def parse_xero_date(date_str):
    """Convert /Date(timestamp+offset)/ to UTC datetime string."""
    if not date_str:
        return None
    match = re.match(r"/Date\((\d+)([+-]\d{4})?\)/", str(date_str))
    if match:
        ts = int(match.group(1)) / 1000.0
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    try:
        return str(datetime.fromisoformat(date_str))
    except Exception:
        return None

def save_purchase_orders_to_db(po_data, tenant_id, sync_date):
    db = MySQLHelper()
    purchase_orders = po_data.get('PurchaseOrders', []) if isinstance(po_data, dict) else po_data
    xero_po_ids = set()
    xero_item_ids = set()
    for po in purchase_orders:
        po_id = po.get('purchase_order_id') or po.get('PurchaseOrderID')
        xero_po_ids.add(po_id)
        po_row = {
            'purchase_order_id': po_id,
            'contact_id': (po.get('contact', {}) or {}).get('contact_id') or (po.get('Contact', {}) or {}).get('ContactID'),
            'contact_name': (po.get('contact', {}) or {}).get('name') or (po.get('Contact', {}) or {}).get('Name'),
            'date': parse_xero_date(po.get('date') or po.get('Date')),
            'delivery_date': parse_xero_date(po.get('delivery_date') or po.get('DeliveryDate')),
            'line_amount_types': po.get('line_amount_types') or po.get('LineAmountTypes'),
            'purchase_order_number': po.get('purchase_order_number') or po.get('PurchaseOrderNumber'),
            'reference': po.get('reference') or po.get('Reference'),
            'branding_theme_id': po.get('branding_theme_id') or po.get('BrandingThemeID'),
            'currency_code': po.get('currency_code') or po.get('CurrencyCode'),
            'currency_rate': po.get('currency_rate') or po.get('CurrencyRate'),
            'status': po.get('status') or po.get('Status'),
            'subtotal': po.get('subtotal') or po.get('SubTotal'),
            'total_tax': po.get('total_tax') or po.get('TotalTax'),
            'total': po.get('total') or po.get('Total'),
            'has_attachments': po.get('has_attachments') or po.get('HasAttachments'),
            'is_discounted': po.get('is_discounted') or po.get('IsDiscounted'),
            'amount_due': po.get('amount_due') or po.get('AmountDue'),
            'amount_paid': po.get('amount_paid') or po.get('AmountPaid'),
            'amount_credited': po.get('amount_credited') or po.get('AmountCredited'),
            'updated_date_utc': parse_xero_date(po.get('updated_date_utc') or po.get('UpdatedDateUTC')),
            'has_errors': po.get('has_errors') or po.get('HasErrors'),
            'delivery_address': po.get('delivery_address') or po.get('DeliveryAddress'),
            'attention_to': po.get('attention_to') or po.get('AttentionTo'),
            'expected_arrival_date': parse_xero_date(po.get('expected_arrival_date') or po.get('ExpectedArrivalDate')),
        }
        sql_po = """
        INSERT INTO purchase_orders (purchase_order_id, contact_id, contact_name, date, delivery_date, line_amount_types, purchase_order_number, reference, branding_theme_id, currency_code, currency_rate, status, subtotal, total_tax, total, has_attachments, is_discounted, amount_due, amount_paid, amount_credited, updated_date_utc, has_errors, delivery_address, attention_to, expected_arrival_date)
        VALUES (%(purchase_order_id)s, %(contact_id)s, %(contact_name)s, %(date)s, %(delivery_date)s, %(line_amount_types)s, %(purchase_order_number)s, %(reference)s, %(branding_theme_id)s, %(currency_code)s, %(currency_rate)s, %(status)s, %(subtotal)s, %(total_tax)s, %(total)s, %(has_attachments)s, %(is_discounted)s, %(amount_due)s, %(amount_paid)s, %(amount_credited)s, %(updated_date_utc)s, %(has_errors)s, %(delivery_address)s, %(attention_to)s, %(expected_arrival_date)s)
        ON DUPLICATE KEY UPDATE
            contact_id=VALUES(contact_id), contact_name=VALUES(contact_name), date=VALUES(date), delivery_date=VALUES(delivery_date), line_amount_types=VALUES(line_amount_types), purchase_order_number=VALUES(purchase_order_number), reference=VALUES(reference), branding_theme_id=VALUES(branding_theme_id), currency_code=VALUES(currency_code), currency_rate=VALUES(currency_rate), status=VALUES(status), subtotal=VALUES(subtotal), total_tax=VALUES(total_tax), total=VALUES(total), has_attachments=VALUES(has_attachments), is_discounted=VALUES(is_discounted), amount_due=VALUES(amount_due), amount_paid=VALUES(amount_paid), amount_credited=VALUES(amount_credited), updated_date_utc=VALUES(updated_date_utc), has_errors=VALUES(has_errors), delivery_address=VALUES(delivery_address), attention_to=VALUES(attention_to), expected_arrival_date=VALUES(expected_arrival_date)
        """
        db.execute(sql_po, po_row)
        items = po.get('line_items') or po.get('LineItems') or []
        for item in items:
            item_id = item.get('line_item_id') or item.get('LineItemID')
            xero_item_ids.add(item_id)
            item_row = {
                'line_item_id': item_id,
                'purchase_order_id': po_id,
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
            INSERT INTO purchase_order_items (line_item_id, purchase_order_id, description, quantity, unit_amount, item_code, account_code, account_id, tax_type, tax_amount, line_amount, item_id, item_name)
            VALUES (%(line_item_id)s, %(purchase_order_id)s, %(description)s, %(quantity)s, %(unit_amount)s, %(item_code)s, %(account_code)s, %(account_id)s, %(tax_type)s, %(tax_amount)s, %(line_amount)s, %(item_id)s, %(item_name)s)
            ON DUPLICATE KEY UPDATE
                purchase_order_id=VALUES(purchase_order_id), description=VALUES(description), quantity=VALUES(quantity), unit_amount=VALUES(unit_amount), item_code=VALUES(item_code), account_code=VALUES(account_code), account_id=VALUES(account_id), tax_type=VALUES(tax_type), tax_amount=VALUES(tax_amount), line_amount=VALUES(line_amount), item_id=VALUES(item_id), item_name=VALUES(item_name)
            """
            db.execute(sql_item, item_row)

def sync_purchase_orders(first_run=False):
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
                    po_data = client.get_purchase_orders(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=from_date,
                        fetch_all=True,
                        date_field='Date'
                    )
                else:
                    po_data = client.get_purchase_orders(
                        tenant_id=tenant_id,
                        statuses=["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"],
                        from_date=None,
                        fetch_all=False,
                        if_modified_since=parser.parse(end_str),
                        date_field='UpdatedDateUTC'
                    )
                filtered = po_data.get('PurchaseOrders', [])
                print(f"Filtered {len(filtered)} purchase orders for tenant {tenant_id}")
                if filtered:
                    save_purchase_orders_to_db({'PurchaseOrders': filtered}, tenant_id, sync_date)
            except Exception as e:
                logging.error(f"Tenant {tenant_id} purchase order sync error: {str(e)}")
    except Exception as e:
        logging.error(f"Purchase order sync main error: {str(e)}")

def main(myPurchaseOrdersTimer):
    sync_purchase_orders(first_run=False)
