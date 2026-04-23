FROM odoo:17

# Install additional system dependencies if needed
RUN apt-get update && apt-get install -y \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy custom addons
COPY addons /mnt/extra-addons

# Set the addons path to include custom modules
ENV ADDONS_PATH=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

# Expose port
EXPOSE 8069

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1
