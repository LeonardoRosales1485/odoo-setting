FROM odoo:17

# Copy custom addons
COPY odoo-addons /mnt/extra-addons

# Set the addons path to include custom modules
ENV ADDONS_PATH=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

# Expose port
EXPOSE 8069

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1
