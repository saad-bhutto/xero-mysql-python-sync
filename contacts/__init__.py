import azure.functions as func
import logging
import json
from xero_client import XeroClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function to get contacts from Xero"""
    logging.info('Python HTTP trigger function processed a contacts request.')

    try:
        tenant_id = req.params.get('tenant_id')
        client = XeroClient()
        contacts_data = client.get_contacts(tenant_id=tenant_id)

        return func.HttpResponse(
            json.dumps(contacts_data, indent=2),
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in contacts function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
