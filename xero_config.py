import os
from typing import Dict, Any

class XeroConfig:
    """Configuration class for Xero OAuth2 settings"""

    # OAuth2 scopes for the application
    SCOPES = [
        'openid',
        'email',
        'profile',
        'offline_access',
        'assets',
        'projects',
        'accounting.settings',
        'accounting.transactions',
        'accounting.contacts',
        'accounting.journals.read',
        'accounting.reports.read',
        'accounting.attachments'
    ]

    # Xero API endpoints
    AUTHORIZATION_URL = "https://login.xero.com/identity/connect/authorize"
    TOKEN_URL = "https://identity.xero.com/connect/token"
    API_BASE_URL = "https://api.xero.com/"

    @classmethod
    def get_client_id(cls) -> str:
        return os.getenv('XERO_CLIENT_ID', '')

    @classmethod
    def get_client_secret(cls) -> str:
        return os.getenv('XERO_CLIENT_SECRET', '')

    @classmethod
    def get_redirect_uri(cls) -> str:
        return os.getenv('XERO_REDIRECT_URI', 'http://localhost:7071/api/auth/callback')

    @classmethod
    def get_scopes_string(cls) -> str:
        return ' '.join(cls.SCOPES)

    @classmethod
    def validate_config(cls) -> bool:
        return bool(cls.get_client_id() and cls.get_client_secret())
