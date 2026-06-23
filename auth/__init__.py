import azure.functions as func
import logging
from xero_auth import XeroAuth
from xero_client import XeroClient
from xero_config import XeroConfig
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function to initiate Xero OAuth2 authentication"""
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Validate configuration
        if not XeroConfig.validate_config():
            return func.HttpResponse(
                "Xero configuration is missing. Please set XERO_CLIENT_ID and XERO_CLIENT_SECRET environment variables.",
                status_code=500
            )

        # Create auth instance
        auth = XeroAuth()

        # Generate authorization URL
        auth_url = auth.get_authorization_url()

        # Read index.html content from the same directory
        index_html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        try:
            with open(index_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as file_error:
            logging.error(f"Could not read index.html: {str(file_error)}")
            return func.HttpResponse(
                f"Error: Could not read index.html: {str(file_error)}",
                status_code=500
            )

        # Replace placeholders in HTML
        html_content = html_content.replace("{{AUTH_URL}}", auth_url)
        html_content = html_content.replace("{{REDIRECT_URI}}", os.getenv('XERO_REDIRECT_URI', ''))

        return func.HttpResponse(
            html_content,
            mimetype="text/html"
        )

    except Exception as e:
        logging.error(f"Error in auth function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
