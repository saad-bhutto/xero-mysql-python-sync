import json
import os
import requests
from typing import Dict, Any, Optional
from xero_config import XeroConfig
import mysql.connector

class XeroAuth:
    """Handles Xero OAuth2 authentication and token management"""

    def __init__(self):
        self.token_file = "xero_token.json"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate authorization URL for OAuth2 flow"""
        params = {
            'response_type': 'code',
            'client_id': XeroConfig.get_client_id(),
            'redirect_uri': XeroConfig.get_redirect_uri(),
            'scope': XeroConfig.get_scopes_string(),
            'state': state or 'state'
        }

        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{XeroConfig.AUTHORIZATION_URL}?{query_string}"

    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': XeroConfig.get_redirect_uri(),
            'client_id': XeroConfig.get_client_id(),
            'client_secret': XeroConfig.get_client_secret()
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(XeroConfig.TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()

        token_data = response.json()
        self.save_token(token_data)
        return token_data

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': XeroConfig.get_client_id(),
            'client_secret': XeroConfig.get_client_secret()
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(XeroConfig.TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()

        token_data = response.json()
        self.save_token(token_data)
        return token_data

    def _get_db_connection(self):
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', 3306)),
            database=os.getenv('DB_DATABASE', ''),
            user=os.getenv('DB_USERNAME', ''),
            password=os.getenv('DB_PASSWORD', '')
        )

    def save_token(self, token_data: Dict[str, Any], user_id: str = 'default_user', tenant_id: str = None) -> None:
        """Save token data to MySQL database."""
        if 'scope' not in token_data:
            token_data['scope'] = XeroConfig.get_scopes_string()

        if 'expires_at' not in token_data and 'expires_in' in token_data:
            import time
            token_data['expires_at'] = time.time() + token_data['expires_in']

        if not tenant_id:
            tenant_id = token_data.get('tenant_id') or token_data.get('xero_tenant_id') or 'default_tenant'
        tenant_id = str(tenant_id) if tenant_id is not None else 'default_tenant'

        db_data = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'expires_at': token_data.get('expires_at'),
            'token_type': token_data.get('token_type'),
            'scope': token_data.get('scope'),
            'id_token': token_data.get('id_token'),
        }

        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO xero_tokens (user_id, tenant_id, access_token, refresh_token, expires_in, expires_at, token_type, scope, id_token)
                VALUES (%(user_id)s, %(tenant_id)s, %(access_token)s, %(refresh_token)s, %(expires_in)s, %(expires_at)s, %(token_type)s, %(scope)s, %(id_token)s)
                ON DUPLICATE KEY UPDATE
                    access_token=VALUES(access_token),
                    refresh_token=VALUES(refresh_token),
                    expires_in=VALUES(expires_in),
                    expires_at=VALUES(expires_at),
                    token_type=VALUES(token_type),
                    scope=VALUES(scope),
                    id_token=VALUES(id_token),
                    updated_at=CURRENT_TIMESTAMP
                """
                cursor.execute(sql, db_data)
            conn.commit()
        finally:
            conn.close()

    def load_token(self, user_id: str = 'default_user', tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Load token data from MySQL database"""
        if not tenant_id:
            tenant_id = 'default_tenant'
        tenant_id = str(tenant_id) if tenant_id is not None else 'default_tenant'

        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT access_token, refresh_token, expires_in, expires_at, token_type, scope, id_token
                FROM xero_tokens
                ORDER BY updated_at DESC
                LIMIT 1
                """
                cursor.execute(sql, (user_id, tenant_id))
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    token_data = dict(zip(columns, row))
                    token_data['user_id'] = user_id
                    token_data['tenant_id'] = tenant_id
                    return token_data
        except Exception as e:
            print(f"Error loading token from DB: {e}")
        finally:
            conn.close()
        return None

    def get_valid_token(self) -> Optional[Dict[str, Any]]:
        """Get a valid token, refreshing if necessary"""
        token_data = self.load_token()

        if not token_data:
            return None

        import time
        current_time = time.time()
        expires_at = token_data.get('expires_at', 0)

        if current_time >= expires_at - 300:
            refresh_token = token_data.get('refresh_token')
            if refresh_token:
                try:
                    new_token_data = self.refresh_access_token(refresh_token)
                    new_token_data['expires_at'] = current_time + new_token_data.get('expires_in', 1800)
                    self.save_token(new_token_data)
                    return new_token_data
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    return None

        return token_data

    def is_token_valid(self) -> bool:
        token_data = self.get_valid_token()
        return token_data is not None
