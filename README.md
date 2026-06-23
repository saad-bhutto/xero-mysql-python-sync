# Xero → MySQL Python Sync (Azure Functions)

> Sync your Xero accounting data to a MySQL database automatically using Azure Functions — open source, self-hostable, production-ready.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Azure Functions](https://img.shields.io/badge/Azure-Functions-0078d4)](https://docs.microsoft.com/en-us/azure/azure-functions/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## What It Does

This project bridges Xero's accounting API with a MySQL database. It authenticates with Xero via OAuth2, then continuously syncs all your accounting data using scheduled Azure Functions timer triggers.

**Use cases:**
- Custom reporting dashboards on top of Xero data
- Data warehousing / analytics pipelines
- Multi-system integrations that need a local copy of Xero data
- Audit trails and historical snapshots

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Xero API (OAuth2)                  │
└──────────────────────────┬──────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Azure Functions        │
              │                          │
              │  ┌──────────────────┐   │
              │  │ auth/            │   │  HTTP trigger
              │  │ auth_callback/   │   │  (OAuth2 flow)
              │  └──────────────────┘   │
              │                          │
              │  ┌──────────────────┐   │
              │  │ invoices/        │   │
              │  │ payments/        │   │  Timer triggers
              │  │ bank_transactions│   │  (scheduled sync)
              │  │ ... (11 modules) │   │
              │  └──────────────────┘   │
              │                          │
              │  ┌──────────────────┐   │
              │  │ invoices_webhook/ │   │  HTTP trigger
              │  └──────────────────┘   │  (real-time)
              │                          │
              │  ┌──────────────────┐   │
              │  │ one-time-sync/   │   │  HTTP trigger
              │  └──────────────────┘   │  (manual)
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │       MySQL Database     │
              │  (22 tables, full schema)│
              └─────────────────────────┘
```

---

## Features

- **Full OAuth2 flow** — browser-based authentication with Xero, tokens stored in MySQL
- **Automatic token refresh** — runs every 15 minutes via timer trigger
- **11 data type syncs** — Invoices, Payments, Bank Transactions, Bank Transfers, Credit Notes, Purchase Orders, Quotes, Receipts, Repeating Invoices, Expense Claims, Linked Transactions
- **Line items** — all parent records include their child line items
- **Incremental sync** — on each run fetches only records modified since last sync
- **First-run / historical backfill** — configurable lookback window (default 60 days)
- **Idempotent writes** — uses `INSERT ... ON DUPLICATE KEY UPDATE` for safe reruns
- **Soft deletes** — records removed in Xero are marked `deleted_at` rather than hard-deleted
- **Real-time webhooks** — optional Xero webhook receiver for instant invoice updates
- **Multi-tenant** — supports multiple Xero organisations automatically
- **One-time sync UI** — browser UI to trigger any individual sync manually

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| MySQL | 5.7+ or 8.0+ |
| Azure Functions Core Tools | v4 |
| Node.js | 14+ (for Azurite) |
| Azurite | Latest (local Azure Storage emulator) |

---

## 1. Create a Xero App

1. Go to [https://developer.xero.com/myapps](https://developer.xero.com/myapps)
2. Click **New App**
3. Fill in the details:
   - **App name**: anything (e.g. `My Xero Sync`)
   - **Company**: your company name
   - **OAuth 2.0 redirect URI**: `http://localhost:7071/api/auth/callback` (for local dev)
4. After creating the app, note your **Client ID** and **Client Secret**
5. Under **Scopes**, enable:
   ```
   openid  email  profile  offline_access
   accounting.settings  accounting.transactions  accounting.contacts
   accounting.journals.read  accounting.reports.read  accounting.attachments
   assets  projects
   ```

---

## 2. Set Up the Database

### Option A — Docker (recommended for local dev)

```bash
docker-compose up -d
```

This starts MySQL 8.0 and automatically runs `schema.sql` to create all tables.

### Option B — Existing MySQL instance

```bash
mysql -u your_user -p your_database < schema.sql
```

---

## 3. Installation

```bash
# Clone the repo
git clone https://github.com/your-username/xero-mysql-python-sync.git
cd xero-mysql-python-sync

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Azure Functions Core Tools (if not already installed)
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Install Azurite (local Azure Storage emulator)
npm install -g azurite
```

---

## 4. Configuration

Copy the example settings file:

```bash
cp local.settings.example.json local.settings.json
```

Edit `local.settings.json` with your values:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "XERO_CLIENT_ID": "your-client-id",
    "XERO_CLIENT_SECRET": "your-client-secret",
    "XERO_REDIRECT_URI": "http://localhost:7071/api/auth/callback",
    "XERO_WEBHOOK_KEY": "your-webhook-key-if-using-webhooks",
    "DB_HOST": "127.0.0.1",
    "DB_PORT": 3306,
    "DB_DATABASE": "xero_sync",
    "DB_USERNAME": "root",
    "DB_PASSWORD": "root",
    "SYNC_LOOKBACK_DAYS": "60"
  }
}
```

> **Security**: `local.settings.json` is in `.gitignore` and must never be committed. Use Azure Key Vault or App Settings for production.

---

## 5. Running Locally

```bash
# Terminal 1 — Start Azurite (local Azure Storage emulator)
azurite

# Terminal 2 — Start Azure Functions runtime
func start
```

---

## 6. Authenticate with Xero

1. Open your browser: `http://localhost:7071/api/auth`
2. Click **Authenticate with Xero**
3. Log in to Xero and approve the permissions
4. You'll be redirected back to a success page with links to trigger syncs

---

## 7. Run Your First Sync

After authenticating, use the one-time sync UI to backfill all data:

```
http://localhost:7071/api/one-time-sync
```

Or trigger individual syncs:

```
http://localhost:7071/api/one-time-sync?function=sync_invoices
http://localhost:7071/api/one-time-sync?function=sync_payments
http://localhost:7071/api/one-time-sync?function=sync_bank_transactions
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth` | GET | Start Xero OAuth2 flow |
| `/api/auth/callback` | GET | OAuth2 callback (Xero redirects here) |
| `/api/contacts` | GET | Fetch contacts from Xero |
| `/api/tenants` | GET | List connected Xero organisations |
| `/api/one-time-sync` | GET | Manual sync UI / trigger |
| `/api/invoices/webhook` | POST | Xero webhook receiver |

---

## Sync Functions (Timer Triggers)

| Function | Schedule | Data Synced |
|---|---|---|
| `invoices` | Every 4 hours | Invoices + line items |
| `payments` | Every 6 hours | Payments + allocations |
| `bank_transactions` | Every 6 hours | Bank transactions + line items |
| `bank_transfers` | Every 8 hours | Bank transfers |
| `credit_notes` | Daily (midnight) | Credit notes + line items |
| `purchase_orders` | Every 8 hours | Purchase orders + line items |
| `quotes` | Every 8 hours | Quotes + line items |
| `receipts` | Daily (midnight) | Receipts + line items |
| `repeating_invoices` | Daily (midnight) | Repeating invoices + line items |
| `expense_claims` | Daily (midnight) | Expense claims + line items |
| `linked_transactions` | Every 8 hours | Linked transactions |
| `refresh_token` | Every 15 minutes | Refreshes OAuth2 token |

To customise schedules, edit the `"schedule"` value in each `function.json` using [NCrontab syntax](https://github.com/atifaziz/NCrontab).

---

## Database Schema

The schema creates 22 tables. Key tables:

| Table | Description |
|---|---|
| `xero_tokens` | OAuth2 access/refresh tokens |
| `invoices` | Sales and purchase invoices |
| `line_items` | Invoice line items |
| `payments` | Payments linked to invoices |
| `payment_allocations` | Payment allocation details |
| `bank_transactions` | Bank transaction records |
| `bank_transaction_line_items` | Bank transaction line items |
| `bank_transfers` | Transfers between bank accounts |
| `credit_notes` | Credit note records |
| `credit_note_items` | Credit note line items |
| `purchase_orders` | Purchase order records |
| `purchase_order_items` | Purchase order line items |
| `quotes` | Quote records |
| `quote_items` | Quote line items |
| `receipts` | Receipt records |
| `receipt_line_items` | Receipt line items |
| `repeating_invoices` | Repeating/scheduled invoices |
| `repeating_invoice_line_items` | Repeating invoice line items |
| `expense_claims` | Employee expense claims |
| `expense_claim_line_items` | Expense claim line items |
| `linked_transactions` | Transaction linkage records |

---

## Deployment to Azure

```bash
# Login to Azure
az login

# Create a Function App (if not existing)
az functionapp create \
  --name your-function-app-name \
  --resource-group your-resource-group \
  --runtime python \
  --runtime-version 3.10 \
  --functions-version 4 \
  --os-type linux \
  --consumption-plan-location australiaeast

# Deploy
func azure functionapp publish your-function-app-name

# Set environment variables in Azure
az functionapp config appsettings set \
  --name your-function-app-name \
  --resource-group your-resource-group \
  --settings \
    XERO_CLIENT_ID="..." \
    XERO_CLIENT_SECRET="..." \
    XERO_REDIRECT_URI="https://your-function-app-name.azurewebsites.net/api/auth/callback" \
    DB_HOST="..." \
    DB_DATABASE="..." \
    DB_USERNAME="..." \
    DB_PASSWORD="..."
```

Update the **Redirect URI** in your Xero app to match the deployed URL, then re-authenticate via `https://your-function-app-name.azurewebsites.net/api/auth`.

---

## Webhooks (Optional)

To receive real-time invoice updates from Xero:

1. In your Xero app settings, go to **Webhooks**
2. Set the webhook URL to: `https://your-function-app-name.azurewebsites.net/api/invoices/webhook`
3. Copy the **Webhook key** Xero provides
4. Set `XERO_WEBHOOK_KEY` in your app settings

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `XERO_CLIENT_ID` | Yes | Your Xero app's Client ID |
| `XERO_CLIENT_SECRET` | Yes | Your Xero app's Client Secret |
| `XERO_REDIRECT_URI` | Yes | OAuth2 callback URL |
| `XERO_WEBHOOK_KEY` | No | Webhook signature key |
| `DB_HOST` | Yes | MySQL host |
| `DB_PORT` | No | MySQL port (default: 3306) |
| `DB_DATABASE` | Yes | MySQL database name |
| `DB_USERNAME` | Yes | MySQL username |
| `DB_PASSWORD` | Yes | MySQL password |
| `SYNC_LOOKBACK_DAYS` | No | Days of history on first run (default: 60) |

---

## Project Structure

```
xero-mysql-python-sync/
├── xero_config.py          # OAuth2 configuration & scopes
├── xero_auth.py            # OAuth2 flow & token management
├── xero_client.py          # Xero API client wrapper + MySQLHelper
├── xero_utils.py           # Date parsing utilities
├── schema.sql              # MySQL database schema (22 tables)
├── requirements.txt        # Python dependencies
├── host.json               # Azure Functions runtime config
├── local.settings.example.json  # Config template (copy → local.settings.json)
├── docker-compose.yml      # Local MySQL via Docker
├── CLAUDE.md               # AI assistant guidance for this repo
├── auth/                   # OAuth2 initiation endpoint
├── auth_callback/          # OAuth2 callback handler
├── invoices/               # Invoice sync (timer + save function)
├── payments/               # Payment sync
├── bank_transactions/      # Bank transaction sync
├── bank_transfers/         # Bank transfer sync
├── credit_notes/           # Credit note sync
├── purchase_orders/        # Purchase order sync
├── quotes/                 # Quote sync
├── receipts/               # Receipt sync
├── repeating_invoices/     # Repeating invoice sync
├── expense_claims/         # Expense claim sync
├── linked_transactions/    # Linked transaction sync
├── refresh_token/          # Token refresh timer
├── contacts/               # Contacts HTTP endpoint
├── tenants/                # Tenants HTTP endpoint
├── invoices_webhook/       # Xero webhook receiver
└── one-time-sync/          # Manual sync UI & trigger
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs are welcome!

---

## License

[MIT](LICENSE)
