import logging
import json
from bank_transactions import sync_bank_transactions
from bank_transfers import sync_bank_transfers
from credit_notes import sync_credit_notes
from invoices import sync_invoices
from linked_transactions import sync_linked_transactions
from payments import sync_payments
from purchase_orders import sync_purchase_orders
from quotes import sync_quotes
from receipts import sync_receipts
from repeating_invoices import sync_repeating_invoices
from expense_claims import sync_expense_claims
from xero_client import XeroClient
import azure.functions as func


def sync_contacts():
    try:
        client = XeroClient()
        tenants = client.get_tenants()
        for tenant in tenants:
            tenant_id = tenant.get('tenant_id') or tenant.get('TenantId')
            contacts_data = client.get_contacts(tenant_id=tenant_id)
            logging.info(f"Contacts for tenant {tenant_id}: {json.dumps(contacts_data)[:500]}")
    except Exception as e:
        logging.error(f"Error syncing contacts: {str(e)}")


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        func_name = req.params.get('function')
        sync_functions = {
            'sync_invoices': lambda: sync_invoices(True),
            'sync_bank_transactions': lambda: sync_bank_transactions(True),
            'sync_bank_transfers': lambda: sync_bank_transfers(True),
            'sync_credit_notes': lambda: sync_credit_notes(True),
            'sync_linked_transactions': lambda: sync_linked_transactions(True),
            'sync_payments': lambda: sync_payments(True),
            'sync_purchase_orders': lambda: sync_purchase_orders(True),
            'sync_quotes': lambda: sync_quotes(True),
            'sync_receipts': lambda: sync_receipts(True),
            'sync_repeating_invoices': lambda: sync_repeating_invoices(True),
            'sync_expense_claims': lambda: sync_expense_claims(True),
        }

        if func_name:
            func_to_run = sync_functions.get(func_name)
            if not func_to_run:
                return func.HttpResponse(
                    f"Invalid function name: {func_name}",
                    status_code=400
                )
            logging.info(f"Running sync function: {func_name}")
            func_to_run()
            return func.HttpResponse(
                f"<html><body><h1>Sync function '{func_name}' completed!</h1></body></html>",
                mimetype="text/html"
            )
        else:
            return func.HttpResponse(
                """
            <html>
            <head><title>One-Time Sync</title></head>
            <body style="font-family:sans-serif;max-width:600px;margin:40px auto;padding:0 20px">
                <h1>One-Time Sync</h1>
                <p>Click a link below to trigger a full historical sync for each data type:</p>
                <ul>
                    <li><a href="/api/one-time-sync?function=sync_invoices">Sync <strong>Invoices</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_bank_transactions">Sync <strong>Bank Transactions</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_bank_transfers">Sync <strong>Bank Transfers</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_credit_notes">Sync <strong>Credit Notes</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_linked_transactions">Sync <strong>Linked Transactions</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_payments">Sync <strong>Payments</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_purchase_orders">Sync <strong>Purchase Orders</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_quotes">Sync <strong>Quotes</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_receipts">Sync <strong>Receipts</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_repeating_invoices">Sync <strong>Repeating Invoices</strong></a></li>
                    <li><a href="/api/one-time-sync?function=sync_expense_claims">Sync <strong>Expense Claims</strong></a></li>
                </ul>
            </body>
            </html>
            """,
                mimetype="text/html"
            )
    except Exception as e:
        return func.HttpResponse(f"Error running one-time sync: {str(e)}", status_code=500)
