import secrets
from odoo import models, fields, api
from datetime import timedelta


class BrApiToken(models.Model):
    _name = 'br.api.token'
    _description = 'Token de sesión para usuarios de la app'
    _order = 'create_date desc'

    token = fields.Char(
        string='Token',
        required=True,
        default=lambda self: secrets.token_hex(32),
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Usuario',
        required=True,
        ondelete='cascade',
    )

    role = fields.Selection([
        ('client',   'Cliente'),
        ('provider', 'Proveedor'),
    ], string='Rol', required=True)

    expires_at = fields.Datetime(string='Expira')
    is_active = fields.Boolean(string='Activo', default=True)

    @api.model
    def create_for_partner(self, partner_id, role):
        # Invalida tokens anteriores del mismo partner
        old = self.search([('partner_id', '=', partner_id), ('is_active', '=', True)])
        old.write({'is_active': False})

        return self.create({
            'partner_id': partner_id,
            'role': role,
            'expires_at': fields.Datetime.now() + timedelta(days=30),
        })

    @api.model
    def authenticate(self, token_str):
        import logging
        logger = logging.getLogger(__name__)
        now = fields.Datetime.now()
        logger.info('authenticate: searching for token_str=%s (len=%d)', token_str[:20] if token_str else '', len(token_str or ''))
        logger.info('authenticate: current time=%s', now)

        token = self.search([
            ('token', '=', token_str),
            ('is_active', '=', True),
            ('expires_at', '>=', now),
        ], limit=1)

        logger.info('authenticate: found token=%s (is_active=True, expires_at >= now)', bool(token))
        if not token:
            # Debug: check if token exists but is inactive or expired
            all_tokens = self.search([('token', '=', token_str)], limit=5)
            for t in all_tokens:
                logger.info('authenticate: existing token found but: is_active=%s, expires_at=%s', t.is_active, t.expires_at)

        return token or False
