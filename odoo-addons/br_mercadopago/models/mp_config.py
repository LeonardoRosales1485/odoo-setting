from odoo import models, fields, api


class MpConfig(models.Model):
    _name = 'mp.config'
    _description = 'Configuración MercadoPago'

    name = fields.Char(string='Nombre', required=True, default='Botón Rojo Principal')
    seller_id = fields.Char(string='Seller ID', required=True)
    access_token = fields.Char(string='Access Token', required=True)
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)
    api_url = fields.Char(string='API URL', default='https://api.mercadopago.com', required=True)
    webhook_token = fields.Char(string='Webhook Token')
    br_commission_percentage = fields.Float(string='% Comisión BR', default=15.0)
    provider_percentage = fields.Float(string='% Proveedor', default=85.0)
    is_active = fields.Boolean(string='Activo', default=True)
    is_production = fields.Boolean(string='Producción', default=False)
    last_error = fields.Text(string='Último error')
    last_success = fields.Datetime(string='Última ejecución exitosa')

    @api.model
    def get_active_config(self):
        config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            from odoo.exceptions import UserError
            raise UserError('No hay configuración activa de MercadoPago')
        return config
