from odoo import models, fields


class BrServiceOrderSubscription(models.Model):
    _inherit = 'br.service.order'

    subscription_id = fields.Many2one(
        'br.subscription',
        string='Suscripción',
        ondelete='set null',
    )
