#!/bin/bash
# Setup script for Botón Rojo deployment server
# Run as: bash setup-server.sh

set -e

echo "🚀 Botón Rojo Server Setup"
echo "========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}This script must be run as root (use sudo)${NC}"
  exit 1
fi

# Update system packages
echo -e "${YELLOW}[1/6] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install Docker
echo -e "${YELLOW}[2/6] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  rm get-docker.sh
  echo -e "${GREEN}✓ Docker installed${NC}"
else
  echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}[3/6] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
  echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Create deployment user
echo -e "${YELLOW}[4/6] Setting up deployment user...${NC}"
if ! id "deploy" &>/dev/null; then
  useradd -m -s /bin/bash deploy
  usermod -aG docker deploy
  echo -e "${GREEN}✓ Deploy user created${NC}"
else
  echo -e "${GREEN}✓ Deploy user already exists${NC}"
fi

# Create SSH directory and keys
echo -e "${YELLOW}[5/6] Setting up SSH keys...${NC}"
mkdir -p /home/deploy/.ssh
chown deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh

if [ ! -f /home/deploy/.ssh/id_rsa ]; then
  sudo -u deploy ssh-keygen -t rsa -b 4096 -f /home/deploy/.ssh/id_rsa -N ""
  sudo -u deploy cat /home/deploy/.ssh/id_rsa.pub >> /home/deploy/.ssh/authorized_keys
  chmod 600 /home/deploy/.ssh/authorized_keys
  echo -e "${GREEN}✓ SSH keys generated${NC}"
  echo ""
  echo -e "${YELLOW}SSH Private Key (add to CircleCI as SSH_PRIVATE_KEY_SANDBOX):${NC}"
  echo "---"
  cat /home/deploy/.ssh/id_rsa
  echo "---"
else
  echo -e "${GREEN}✓ SSH keys already exist${NC}"
fi

# Create application directory
echo -e "${YELLOW}[6/6] Creating application directory...${NC}"
mkdir -p /opt/botonrojo
chown deploy:deploy /opt/botonrojo

# Setup sudo for deploy user (allow docker commands without password)
echo "deploy ALL=(ALL) NOPASSWD: /usr/bin/docker*" | tee -a /etc/sudoers.d/deploy > /dev/null
chmod 440 /etc/sudoers.d/deploy

echo ""
echo -e "${GREEN}✅ Server setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Add the SSH private key above to CircleCI context: botonrojo-deploy-sandbox"
echo "2. Clone the repository:"
echo "   ssh deploy@YOUR_SERVER_IP"
echo "   cd /opt/botonrojo"
echo "   git clone https://github.com/YOUR_GITHUB/botonrojo.git ."
echo "3. Create .env file with your configuration"
echo "4. Start monitoring CircleCI for deployments"
echo ""
echo "Server info:"
echo "- Docker installed: $(docker --version)"
echo "- Docker Compose installed: $(docker-compose --version)"
echo "- Deployment user: deploy"
echo "- App directory: /opt/botonrojo"
