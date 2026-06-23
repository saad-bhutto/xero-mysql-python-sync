import azure.functions as func
import logging
import json
from xero_client import XeroClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function to get Xero tenants/organizations"""
    logging.info('Python HTTP trigger function processed a tenants request.')

    try:
        client = XeroClient()
        tenants_data = client.get_tenants()

        return func.HttpResponse(
            json.dumps(tenants_data, indent=2),
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in tenants function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
