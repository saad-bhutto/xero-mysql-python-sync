import logging
import azure.functions as func
from xero_client import XeroClient

def main(mytimer: func.TimerRequest) -> None:
    """Azure Function timer trigger to refresh Xero OAuth2 token."""
    try:
        logging.info("===== Starting token refresh =====")
        client = XeroClient()
        client.refresh_token()
        logging.info("Token refreshed and saved to database successfully.")
    except Exception as e:
        logging.error(f"Error in background token refresh: {str(e)}")
        raise
