from typing import Dict, Any, List, Optional
from xero_python.accounting import AccountingApi
from xero_python.api_client import ApiClient, serialize
from xero_python.api_client.configuration import Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.identity import IdentityApi
from xero_python.utils import getvalue
from xero_auth import XeroAuth
from xero_config import XeroConfig
from datetime import datetime

class XeroClient:
    """Client for interacting with Xero APIs"""

    def __init__(self):
        self.auth = XeroAuth()
        self.api_client = None
        self.accounting_api = None
        self.identity_api = None
        self.oauth2_token = None
        self._setup_api_client()

    def _setup_api_client(self):
        token_data = self.auth.get_valid_token()

        if not token_data:
            raise Exception("No valid token available. Please authenticate first.")

        self.oauth2_token = OAuth2Token(
            client_id=XeroConfig.get_client_id(),
            client_secret=XeroConfig.get_client_secret()
        )

        access_token = token_data.get('access_token', '')
        scope = token_data.get('scope', '')
        expires_in = token_data.get('expires_in', 1800)
        token_type = token_data.get('token_type', 'Bearer')
        expires_at = token_data.get('expires_at')
        refresh_token = token_data.get('refresh_token')

        if isinstance(scope, str):
            scope_list = scope.split(' ') if scope else []
        else:
            scope_list = scope if scope else []

        try:
            self.oauth2_token.update_token(
                access_token,
                scope_list,
                expires_in,
                token_type,
                expires_at,
                refresh_token
            )
        except Exception as e:
            print(f"Error updating OAuth2 token: {e}")
            raise

        config = Configuration(oauth2_token=self.oauth2_token)

        self.api_client = ApiClient(
            configuration=config,
            pool_threads=1
        )

        self.api_client.oauth2_token_getter(self._get_oauth2_token)
        self.api_client.oauth2_token_saver(self._save_oauth2_token)

        self.accounting_api = AccountingApi(self.api_client)
        self.identity_api = IdentityApi(self.api_client)

    def _get_oauth2_token(self) -> Dict[str, Any]:
        if not self.oauth2_token:
            raise Exception("OAuth2 token not initialized")

        return {
            'access_token': self.oauth2_token.access_token,
            'scope': self.oauth2_token.scope,
            'expires_in': self.oauth2_token.expires_in,
            'token_type': self.oauth2_token.token_type,
            'expires_at': self.oauth2_token.expires_at,
            'refresh_token': self.oauth2_token.refresh_token
        }

    def _save_oauth2_token(self, token: Dict[str, Any]) -> None:
        if self.oauth2_token:
            access_token = token.get('access_token', '')
            scope = token.get('scope', [])
            expires_in = token.get('expires_in', 1800)
            token_type = token.get('token_type', 'Bearer')
            expires_at = token.get('expires_at')
            refresh_token = token.get('refresh_token')

            if isinstance(scope, str):
                scope_list = scope.split(' ') if scope else []
            else:
                scope_list = scope if scope else []

            try:
                self.oauth2_token.update_token(
                    access_token,
                    scope_list,
                    expires_in,
                    token_type,
                    expires_at,
                    refresh_token
                )
            except Exception as e:
                print(f"Error updating OAuth2 token in saver: {e}")
                raise

        self.auth.save_token(token)

    def get_tenants(self) -> List[Dict[str, Any]]:
        if not self.identity_api:
            raise Exception("API client not initialized")

        tenants = []
        for connection in self.identity_api.get_connections():
            tenant = serialize(connection)
            if connection.tenant_type == "ORGANISATION":
                organisations = self.accounting_api.get_organisations(
                    xero_tenant_id=connection.tenant_id
                )
                tenant["organisations"] = serialize(organisations)
            tenants.append(tenant)

        return tenants

    def get_tenant_id(self) -> Optional[str]:
        tenants = self.get_tenants()
        for tenant in tenants:
            if tenant.get('tenant_type') == 'ORGANISATION':
                return tenant.get('tenant_id')
        return None

    def _get_xero_resource(
        self,
        api_method,
        resource_key: str,
        tenant_id: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        fetch_all: bool = False,
        if_modified_since: Optional[datetime] = None,
        date_field: str = 'Date',
        extra_kwargs: Optional[dict] = None
    ) -> Dict[str, Any]:
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        if not tenant_id:
            tenant_id = self.get_tenant_id()
            if not tenant_id:
                raise RuntimeError("No Xero tenant ID available.")
        page = 1
        page_size = 100
        all_items = []
        if date_field not in ['Date', 'UpdatedDateUTC']:
            raise ValueError(f"Invalid date_field: '{date_field}'. Must be 'Date' or 'UpdatedDateUTC'.")
        formatted_from_date_for_where = None
        if from_date:
            try:
                dt_obj = datetime.strptime(from_date, "%Y-%m-%d")
                formatted_from_date_for_where = f"DateTime({dt_obj.year},{dt_obj.month},{dt_obj.day})"
            except ValueError:
                raise ValueError(f"Invalid 'from_date' format: '{from_date}'. Expected 'YYYY-MM-DD'.")
        while True:
            kwargs = {
                'xero_tenant_id': tenant_id,
                'order': 'UpdatedDateUTC DESC',
                'page': page,
            }

            if not statuses:
                statuses = ["DRAFT", "SUBMITTED", "AUTHORISED", "PAID"]
            if statuses is not None:
                if 'statuses' in api_method.__code__.co_varnames:
                    kwargs['statuses'] = statuses
                elif 'status' in api_method.__code__.co_varnames:
                    kwargs['status'] = statuses
            if formatted_from_date_for_where:
                if api_method.__name__ in ['get_purchase_orders', 'get_bank_transfers', 'get_linked_transactions']:
                    kwargs['date_from'] = from_date
                else:
                    kwargs['where'] = f"{date_field} >= {formatted_from_date_for_where}"
            if if_modified_since:
                kwargs['if_modified_since'] = if_modified_since
            if extra_kwargs:
                kwargs.update(extra_kwargs)
            print(f"Xero API Call Parameters (Page {page}): {kwargs}")
            try:
                response = api_method(**kwargs)
                data = serialize(response)
                batch = data.get(resource_key, [])
                all_items.extend(batch)
                if not fetch_all or len(batch) < page_size:
                    break
                page += 1
            except Exception as e:
                print(f"Error fetching {resource_key}: {e}")
                break
        return {resource_key: all_items}

    def get_invoices(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_invoices, 'Invoices', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_invoice(self, invoice_id: str, tenant_id: str) -> Dict[str, Any]:
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        if not invoice_id or not tenant_id:
            raise ValueError("Both 'invoice_id' and 'tenant_id' are required.")
        try:
            response = self.accounting_api.get_invoice(xero_tenant_id=tenant_id, invoice_id=invoice_id)
            data = serialize(response)
            invoices = data.get('Invoices', [])
            return invoices[0] if invoices else {}
        except Exception as e:
            print(f"Error fetching invoice {invoice_id} for tenant {tenant_id}: {e}")
            raise

    def get_purchase_orders(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_purchase_orders, 'PurchaseOrders', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_credit_notes(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_credit_notes, 'CreditNotes', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_quotes(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_quotes, 'Quotes', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_payments(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_payments, 'Payments', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_bank_transactions(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_bank_transactions, 'BankTransactions', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_bank_transfers(self, tenant_id=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_bank_transfers, 'BankTransfers', tenant_id=tenant_id, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_linked_transactions(self, tenant_id=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_linked_transactions, 'LinkedTransactions', tenant_id=tenant_id, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_expense_claims(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_expense_claims, 'ExpenseClaims', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_receipts(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_receipts, 'Receipts', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_repeating_invoices(self, tenant_id=None, statuses=None, from_date=None, fetch_all=False, if_modified_since=None, date_field='Date'):
        if not self.accounting_api:
            raise RuntimeError("Xero Accounting API client not initialized.")
        return self._get_xero_resource(self.accounting_api.get_repeating_invoices, 'RepeatingInvoices', tenant_id=tenant_id, statuses=statuses, from_date=from_date, fetch_all=fetch_all, if_modified_since=if_modified_since, date_field=date_field)

    def get_contacts(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.accounting_api:
            raise Exception("API client not initialized")
        if not tenant_id:
            tenant_id = self.get_tenant_id()
            if not tenant_id:
                raise Exception("No tenant ID available")
        contacts = self.accounting_api.get_contacts(xero_tenant_id=tenant_id)
        return serialize(contacts)

    def create_contact(self, contact_data: Dict[str, Any], tenant_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.accounting_api:
            raise Exception("API client not initialized")
        if not tenant_id:
            tenant_id = self.get_tenant_id()
            if not tenant_id:
                raise Exception("No tenant ID available")
        from xero_python.accounting import Contact, Contacts
        contact = Contact(**contact_data)
        contacts = Contacts(contacts=[contact])
        created_contacts = self.accounting_api.create_contacts(xero_tenant_id=tenant_id, contacts=contacts)
        return serialize(created_contacts)

    def refresh_token(self) -> Dict[str, Any]:
        token_data = self.auth.load_token()
        if not token_data or not token_data.get('refresh_token'):
            raise Exception("No refresh token available")
        new_token_data = self.auth.refresh_access_token(token_data['refresh_token'])
        self._setup_api_client()
        return new_token_data


class MySQLHelper:
    """Helper for MySQL database operations."""
    def __init__(self):
        import os
        import mysql.connector
        self.config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_DATABASE', ''),
            'user': os.getenv('DB_USERNAME', ''),
            'password': os.getenv('DB_PASSWORD', '')
        }
        self.mysql = mysql.connector

    def get_connection(self):
        return self.mysql.connect(**self.config)

    def execute(self, sql, params=None, commit=True):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or {})
                if commit:
                    conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    def executemany(self, sql, seq_of_params, commit=True):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(sql, seq_of_params)
                if commit:
                    conn.commit()
                return cursor.rowcount
        finally:
            conn.close()

    def fetchone(self, sql, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or {})
                return cursor.fetchone()
        finally:
            conn.close()

    def fetchall(self, sql, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or {})
                return cursor.fetchall()
        finally:
            conn.close()
