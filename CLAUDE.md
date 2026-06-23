# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An Azure Functions Python application that syncs Xero accounting data to a MySQL database via OAuth2. Timer-triggered functions run on schedules; HTTP-triggered functions handle auth, webhooks, and manual syncs.

## Local Development

### Prerequisites
- Python 3.8+, MySQL 5.7+/8.0+, Azure Functions Core Tools v4, Node.js 14+, Azurite

### Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.example.json local.settings.json   # then fill in credentials
docker-compose up -d                                  # start local MySQL
```

### Running
```bash
# Terminal 1
azurite

# Terminal 2
func start
```

Then authenticate at `http://localhost:7071/api/auth` and trigger syncs via `http://localhost:7071/api/one-time-sync`.

### Deployment
```bash
func azure functionapp publish <your-function-app-name>
```

## Architecture

### Shared modules (root-level)
- `xero_config.py` — OAuth2 scopes, endpoint URLs, env var accessors
- `xero_auth.py` — `XeroAuth`: OAuth2 flow, token exchange/refresh, token persistence to `xero_tokens` MySQL table
- `xero_client.py` — `XeroClient`: wraps `xero-python` SDK, handles pagination via `_get_xero_resource()`; `MySQLHelper`: thin wrapper over `mysql-connector-python` with `execute/executemany/fetchone/fetchall`
- `xero_utils.py` — `parse_xero_date()`: converts Xero's `/Date(ms)/` format to MySQL DATETIME strings

### Function modules (one directory per function)
Each directory has `function.json` (binding config) and `__init__.py` (handler). Two patterns:

**Timer-triggered sync functions** (`invoices/`, `payments/`, `bank_transactions/`, etc.):
- Export a `sync_<resource>(first_run=False)` function
- `first_run=True` → full historical backfill using `if_modified_since=None` + `from_date` set to `SYNC_LOOKBACK_DAYS` ago
- `first_run=False` → incremental: passes `if_modified_since` to filter only records changed since last run
- Also export a `save_<resource>_to_db()` function that does the MySQL upsert + soft-delete logic
- Azure Functions entry point: `main(myTimer)` which calls `sync_<resource>(first_run=False)`

**HTTP-triggered functions** (`auth/`, `auth_callback/`, `one-time-sync/`, `invoices_webhook/`, `contacts/`, `tenants/`):
- `auth/` + `auth_callback/` — OAuth2 initiation and callback; store token via `XeroAuth.save_token()`
- `one-time-sync/` — serves an HTML UI and dispatches to any `sync_*` function with `first_run=True` via `?function=sync_invoices`
- `invoices_webhook/` — validates Xero webhook signature then upserts invoice data

### Data flow
```
Xero API → XeroClient._get_xero_resource() → save_*_to_db() → MySQL
```

### DB write pattern
All writes use `INSERT ... ON DUPLICATE KEY UPDATE` (idempotent). Records removed in Xero are soft-deleted: `UPDATE ... SET deleted_at=UTC_TIMESTAMP() WHERE ... NOT IN (xero_ids)`. Hard deletes are never used.

### Xero API field naming
The `xero-python` SDK's `serialize()` can return fields in either `snake_case` or `PascalCase` depending on context. All `save_*_to_db()` functions handle both: `inv.get('invoice_id') or inv.get('InvoiceID')`.

## Adding a New Sync Module

1. Create `<resource>/function.json` with a `timerTrigger` binding and NCrontab schedule
2. Create `<resource>/__init__.py` with:
   - `save_<resource>_to_db(data, tenant_id, sync_date)` — upsert + soft-delete logic
   - `sync_<resource>(first_run=False)` — fetches from `XeroClient`, calls the save function
   - `main(myTimer)` — Azure Functions entry point
3. Wire it into `one-time-sync/__init__.py`'s `sync_functions` dict

## Configuration

All config lives in `local.settings.json` (local) or Azure App Settings (production). Key variables: `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_REDIRECT_URI`, `DB_HOST/PORT/DATABASE/USERNAME/PASSWORD`, `SYNC_LOOKBACK_DAYS` (default 60).

`local.settings.json` is gitignored and must never be committed.
