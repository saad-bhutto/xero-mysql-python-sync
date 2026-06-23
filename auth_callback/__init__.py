import azure.functions as func
import logging
from xero_auth import XeroAuth
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function to handle Xero OAuth2 callback"""
    logging.info('Python HTTP trigger function processed a callback request.')

    try:
        # Get authorization code from query parameters
        code = req.params.get('code')
        error = req.params.get('error')

        if error:
            return func.HttpResponse(
                f"Authentication error: {error}",
                status_code=400
            )

        if not code:
            return func.HttpResponse(
                "No authorization code received",
                status_code=400
            )

        # Create auth instance
        auth = XeroAuth()

        # Exchange code for token
        token_data = auth.exchange_code_for_token(code)

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
        # No dynamic placeholders for now, but could add if needed
        return func.HttpResponse(
            html_content,
            mimetype="text/html"
        )

    except Exception as e:
        logging.error(f"Error in auth callback function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
