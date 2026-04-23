# CircleCI Deployment Guide — Botón Rojo

## Overview

This guide walks you through deploying Botón Rojo using CircleCI with automated testing, Docker builds, and deployment to a sandbox environment.

---

## Architecture

```
GitHub/GitLab
    ↓
CircleCI (CI/CD Pipeline)
    ├─ Lint & Test (every push)
    ├─ Build Docker (main/develop)
    └─ Deploy to Sandbox (main branch)
    ↓
Docker Registry (optional)
    ↓
Sandbox Server (VPS/Cloud)
    ↓
Public URL → MercadoPago Webhook
```

---

## Prerequisites

1. **GitHub Repository** - Your code must be pushed to GitHub
2. **CircleCI Account** - Free tier available at https://circleci.com
3. **Sandbox Server** - Cloud VPS (AWS EC2, GCP, DigitalOcean, etc.)
4. **SSH Access** - Private key for deploying to your server
5. **Docker Hub Account** (optional) - For storing Docker images

---

## Step 1: Connect CircleCI to GitHub

### 1.1 Sign up / Login to CircleCI
- Go to https://circleci.com
- Click "Sign Up" or "Log In"
- Choose "GitHub" as your VCS

### 1.2 Authorize CircleCI
- Grant permission to access your repositories
- Select the repository containing Botón Rojo

### 1.3 Enable Project
- In CircleCI Dashboard, find your repository
- Click "Set Up Project"
- Choose "Existing Config" (since we've provided `.circleci/config.yml`)
- Click "Let's Go" to start the first pipeline

---

## Step 2: Set Up Sandbox Server

### 2.1 Launch a VPS

Choose one:
- **AWS EC2** (t3.medium recommended, ~$20/month)
- **DigitalOcean Droplet** (Standard 2GB, ~$12/month)
- **Google Cloud VM** (e2-medium, ~$20/month)

**Recommended OS:** Ubuntu 22.04 LTS or Debian 12

### 2.2 Install Docker on the Server

```bash
# SSH into your server
ssh root@<YOUR_SERVER_IP>

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your deploy user to docker group
sudo usermod -aG docker deploy

# Verify Docker is running
docker --version
```

### 2.3 Create Deployment Directory

```bash
# Create directory for Botón Rojo
sudo mkdir -p /opt/botonrojo
sudo chown deploy:deploy /opt/botonrojo

# Clone the repository (or set up a deployment directory)
cd /opt/botonrojo
git clone https://github.com/YOUR_GITHUB/botonrojo.git .
```

### 2.4 Create SSH User for Deployments

```bash
# Create 'deploy' user
sudo useradd -m -s /bin/bash deploy

# Generate SSH key for CircleCI
sudo -u deploy ssh-keygen -t rsa -b 4096 -f /home/deploy/.ssh/id_rsa -N ""

# Add public key to authorized_keys
sudo -u deploy cat /home/deploy/.ssh/id_rsa.pub >> /home/deploy/.ssh/authorized_keys

# Display private key for CircleCI
sudo cat /home/deploy/.ssh/id_rsa
```

Copy the **private key** output — you'll need this in Step 3.

---

## Step 3: Configure CircleCI Environment Variables

### 3.1 Add Project Context (Sandbox)

In CircleCI Dashboard:

1. Go to **Organization Settings** → **Contexts**
2. Click **Create Context** 
3. Name it: `botonrojo-deploy-sandbox`
4. Click **Create Context**

### 3.2 Add Environment Variables

In the context, add these variables:

| Variable | Value |
|---|---|
| `SANDBOX_HOST` | Your server IP (e.g., `34.39.181.0` or `deploy.example.com`) |
| `SSH_PRIVATE_KEY_SANDBOX` | The private SSH key from Step 2.4 |

**Note:** SSH_PRIVATE_KEY_SANDBOX will be masked in the CircleCI logs for security.

---

## Step 4: Create Environment Files on Server

### 4.1 SSH into your sandbox server

```bash
ssh deploy@<YOUR_SERVER_IP>
```

### 4.2 Create `.env` file

```bash
cd /opt/botonrojo
cat > .env << 'EOF'
# Database Configuration
DB_NAME=odoo_br_pilot
DB_USER=odoo
DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE
DB_HOST=db
DB_PORT=5432

# Odoo Configuration
ODOO_PORT=8069
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD_HERE

# MercadoPago Configuration (will be set in Odoo UI)
# These will be configured via the Botón Rojo → Integración MP menu
MP_SELLER_ID=
MP_ACCESS_TOKEN=
MP_CLIENT_ID=
MP_CLIENT_SECRET=

# Application
ENVIRONMENT=sandbox
DEBUG=0
EOF
```

**Replace:**
- `YOUR_SECURE_PASSWORD_HERE` - A strong DB password
- `YOUR_ADMIN_PASSWORD_HERE` - A strong Odoo admin password

### 4.3 Create docker-compose override

```bash
cat > docker-compose.override.yml << 'EOF'
version: '3.8'
services:
  odoo:
    environment:
      - WEB_INTERFACE=1
      - DISABLE_SESSION_GC=False
    volumes:
      - odoo_addons:/mnt/extra-addons
      - odoo_sessions:/var/lib/odoo/sessions
      
volumes:
  odoo_addons:
  odoo_sessions:
EOF
```

---

## Step 5: Push Code to GitHub

```bash
# From your local machine
cd /c/botonrojo

git remote add origin https://github.com/YOUR_GITHUB/botonrojo.git
git branch -M main
git push -u origin main
```

---

## Step 6: Monitor First Deployment

1. Go to **CircleCI Dashboard**
2. Select your project
3. Watch the pipeline:
   - ✅ **lint-and-test** should pass
   - ✅ **build-docker** creates the image
   - ✅ **deploy-sandbox** deploys to your server

If any step fails:
- Click the failed job
- Read the error logs
- Fix the issue locally
- Push again

---

## Step 7: Access Your Deployment

Once deployed, visit:

```
http://<YOUR_SERVER_IP>:8069
```

Login:
- **User:** `admin`
- **Password:** (the admin password you set in Step 4.2)

---

## Step 8: Configure MercadoPago

Now that your app is at a **public URL**, you can configure real MercadoPago credentials:

### 8.1 In Odoo, install br_mercadopago

1. Go to **Aplicaciones**
2. Search: `br_mercadopago`
3. Click **Instalar**

### 8.2 Get MP Credentials

1. Log in to [MercadoPago Developers](https://www.mercadopago.com.ar/developers/panel)
2. Copy:
   - **User ID** (Seller ID)
   - **Access Token**
   - **Client ID**
   - **Client Secret**

### 8.3 Set Webhook URL

In MercadoPago Developers → Webhooks:
- Set webhook URL to: `http://<YOUR_SERVER_IP>:8069/br/api/webhooks/mercadopago`

### 8.4 Enter Credentials in Odoo

In Odoo:
1. **Botón Rojo** → **Integración MP**
2. Click **"Botón Rojo Principal"**
3. Paste the 4 credentials
4. Click **"Probar conexión"**
5. Mark **is_active** ✓
6. **Guardar**

---

## Continuous Deployment

From now on:

1. **Make changes locally** in VS Code
2. **Commit to git:**
   ```bash
   git add .
   git commit -m "Your message"
   git push origin main
   ```
3. **CircleCI automatically:**
   - Runs lint & tests
   - Builds Docker image
   - Deploys to sandbox
4. **View results** in CircleCI Dashboard

---

## Troubleshooting

### Pipeline fails at lint-and-test
→ Fix the Python syntax errors shown in the logs
→ Commit & push again

### Docker build fails
→ Check that `Dockerfile` exists and references are correct
→ Verify all custom addons are in `/addons` directory

### Deploy fails to connect
→ Verify SSH key is correct in CircleCI context
→ Check server IP address is reachable: `ping <YOUR_SERVER_IP>`
→ Confirm `deploy` user exists and has SSH access

### Odoo won't start after deploy
→ SSH to server: `docker-compose logs -f odoo`
→ Check database initialization: `docker-compose logs db`
→ Restart: `docker-compose restart`

### MercadoPago webhook not working
→ Verify public URL is accessible: `curl http://<YOUR_SERVER_IP>:8069/`
→ Check webhook endpoint exists: `curl http://<YOUR_SERVER_IP>:8069/br/api/webhooks/mercadopago`
→ Review MP webhook logs in developers panel

---

## Security Notes

1. **Change default passwords** in `.env`
2. **Use SSL/TLS** - Consider setting up a reverse proxy with Let's Encrypt
3. **Firewall rules** - Only expose port 8069 to necessary IPs
4. **Regular backups** - Schedule PostgreSQL backups
5. **Monitor logs** - Set up log aggregation (optional but recommended)

---

## Next: Production Deployment

Once satisfied with sandbox testing:

1. Create a **production context** in CircleCI: `botonrojo-deploy-production`
2. Add production server credentials
3. Create a new CircleCI job: `deploy-production`
4. Configure to deploy only on tags: `v*.*.*`
5. Test the full flow with real MercadoPago accounts

---

## Support

- **CircleCI Docs:** https://circleci.com/docs/
- **Docker Docs:** https://docs.docker.com/
- **Odoo Docs:** https://www.odoo.com/documentation/17.0/

