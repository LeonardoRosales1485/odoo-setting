import secrets
from odoo import models, fields, api


class BrApiKey(models.Model):
    _name = 'br.api.key'
    _description = 'API Key para workspaces externos (mop-core-ng)'

    name = fields.Char(string='Workspace', required=True)
    api_key = fields.Char(string='API Key', required=True, default=lambda self: secrets.token_hex(32))
    is_active = fields.Boolean(string='Activa', default=True)
    webhook_url = fields.Char(string='URL Webhook destino')

    @api.model
    def authenticate(self, key):
        workspace = self.search([
            ('api_key', '=', key),
            ('is_active', '=', True),
        ], limit=1)
        return workspace or False
