# CircleCI Deployment — Quick Start (5 minutes)

## TL;DR

```bash
# 1. Push to GitHub
git push origin main

# 2. In CircleCI Dashboard:
#    - Add Context: botonrojo-deploy-sandbox
#    - Add variables: SANDBOX_HOST, SSH_PRIVATE_KEY_SANDBOX

# 3. SSH to server and run setup
ssh root@YOUR_SERVER_IP
bash /opt/botonrojo/scripts/setup-server.sh

# 4. Configure .env on server
ssh deploy@YOUR_SERVER_IP
cd /opt/botonrojo
nano .env  # Set DB_PASSWORD, ADMIN_PASSWORD

# 5. Watch CircleCI deploy automatically
# https://app.circleci.com/pipelines/github/YOUR_GITHUB/botonrojo

# 6. Access your app
http://YOUR_SERVER_IP:8069
```

---

## Step-by-Step

### A. GitHub Setup (1 min)

```bash
# Push your code
git add .
git commit -m "Setup CircleCI deployment"
git push origin main
```

### B. CircleCI Setup (2 min)

1. Go to https://circleci.com
2. Click your project
3. Go to **Project Settings** (gear icon)
4. **Organization** → **Contexts**
5. Create Context: `botonrojo-deploy-sandbox`
6. Add variables:

   | Name | Value |
   |------|-------|
   | `SANDBOX_HOST` | `YOUR_SERVER_IP` |
   | `SSH_PRIVATE_KEY_SANDBOX` | (From Step D below) |

### C. Server Setup (1 min)

```bash
# SSH to your server as root
ssh root@YOUR_SERVER_IP

# Run setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB/botonrojo/main/scripts/setup-server.sh | bash

# ⚠️ Important: Copy the SSH private key output
# You'll paste it into CircleCI in step B
```

### D. Configure Server (1 min)

```bash
# SSH as deploy user
ssh deploy@YOUR_SERVER_IP

# Go to app directory
cd /opt/botonrojo

# Clone if not done yet
git clone https://github.com/YOUR_GITHUB/botonrojo.git .

# Create .env from example
cp .env.example .env

# Edit with your passwords
nano .env
# Set:
#   DB_PASSWORD=something_strong
#   ADMIN_PASSWORD=something_strong

# Save and exit (Ctrl+X, Y, Enter)
```

### E. Deploy

```bash
# Trigger deployment by pushing to main
git add .
git commit -m "Trigger deployment"
git push origin main

# Watch it in CircleCI:
# https://app.circleci.com/pipelines/github/YOUR_GITHUB/botonrojo
```

---

## Access Your App

Once deployed:

```
http://YOUR_SERVER_IP:8069
```

**Login:**
- User: `admin`
- Password: (whatever you set in .env ADMIN_PASSWORD)

---

## Configure MercadoPago

Once your server is live:

### 1. Install br_mercadopago module

In Odoo:
1. **Aplicaciones** → **Aplicaciones**
2. Click **"Actualizar lista"**
3. Search: `br_mercadopago`
4. Click **Instalar**

### 2. Get Credentials

Go to: https://www.mercadopago.com.ar/developers/panel

Copy:
- User ID (Seller ID)
- Access Token
- Client ID
- Client Secret

### 3. Configure in Odoo

1. **Botón Rojo** → **Integración MP**
2. Click **"Botón Rojo Principal"**
3. Paste the 4 credentials
4. Click **"Probar conexión"**
5. Mark `is_active` ✓
6. **Guardar**

### 4. Set Webhook URL in MercadoPago

In [MercadoPago Developers](https://www.mercadopago.com.ar/developers/panel):

Webhooks → Add:
```
URL: http://YOUR_SERVER_IP:8069/br/api/webhooks/mercadopago
Events: payment.authorized, payment.captured, payment.refunded
```

---

## Troubleshooting

### CircleCI pipeline fails
→ Click the failed job
→ Read the error
→ Fix locally
→ `git push origin main` again

### Can't SSH to server
→ `ping YOUR_SERVER_IP` (check server is up)
→ Check security group/firewall rules

### Odoo not starting
→ `ssh deploy@YOUR_SERVER_IP`
→ `cd /opt/botonrojo`
→ `docker-compose logs odoo` (see errors)

### MercadoPago webhook failing
→ Check URL is public: `curl http://YOUR_SERVER_IP:8069/`
→ Verify endpoint: `curl http://YOUR_SERVER_IP:8069/br/api/webhooks/mercadopago`

---

## What Happens on Each Push

```
git push origin main
    ↓
CircleCI runs:
    1. lint-and-test (checks Python syntax)
    2. build-docker (creates Docker image)
    3. deploy-sandbox (deploys to your server)
    ↓
Your server updates automatically
    ↓
Visit http://YOUR_SERVER_IP:8069 → Latest code is live
```

---

## For Detailed Info

- **Full deployment guide:** `CIRCLECI_DEPLOYMENT.md`
- **Local testing:** `docker-compose up -d`
- **Module development:** See individual `br_*/` addon README files

---

## Security Reminders

✅ Change default passwords in `.env`
✅ Keep `.env` out of git (it's in `.gitignore`)
✅ Keep SSH keys private
✅ Consider setting up SSL/TLS with Let's Encrypt

---

**Happy deploying! 🚀**
