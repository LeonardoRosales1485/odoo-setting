# Botón Rojo Odoo 17 Configuration Guide

## Database Setup

```sql
CREATE DATABASE odoo_br_pilot;
CREATE USER odoo_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE odoo_br_pilot TO odoo_user;
ALTER DATABASE odoo_br_pilot OWNER TO odoo_user;
```

## Odoo Configuration

File: `/etc/odoo/odoo.conf`

```ini
[options]
addons_path = /opt/odoo/odoo-17/addons,/opt/odoo/custom-addons
admin_passwd = your_admin_password
db_host = localhost
db_port = 5432
db_user = odoo_user
db_password = secure_password
db_name = odoo_br_pilot
logfile = /var/log/odoo/odoo.log
log_level = info
workers = 2
```

## Environment Variables

Create `.env` in project root:

```
GCP_PROJECT_ID=mop-cloud
GCP_SA_KEY=your_base64_encoded_service_account_key
MERCADOPAGO_ACCESS_TOKEN=your_mp_access_token
MERCADOPAGO_PUBLIC_KEY=your_mp_public_key
ODOO_ADMIN_PASSWORD=your_admin_password
ODOO_DB_PASSWORD=secure_password
```

## Module Installation

1. Copy modules to `/opt/odoo/custom-addons/`
2. Restart Odoo service
3. Go to Apps → Search "Botón Rojo" → Install modules in order:
   - br_base
   - br_service_order
   - br_batisena
   - br_api
   - br_mercadopago
   - br_provider_score
   - br_subscription
   - br_disputes
   - br_liquidation

## Circle CI Setup

1. Go to https://circleci.com
2. Connect GitHub repository
3. Add environment variables:
   - `GCP_SA_KEY` (base64-encoded service account key)
   - `GCP_PROJECT_ID` (mop-cloud)

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test/

# Lint code
pylint odoo-addons/
```

## Deployment

Push to `main` branch → Circle CI automatically:
1. Runs tests
2. Deploys modules to GCP instance
3. Restarts Odoo service
