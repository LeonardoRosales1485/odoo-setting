from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    br_score = fields.Float(
        string='Score BR',
        default=5.0,
        digits=(4, 2),
    )

    br_level = fields.Selection([
        ('0_registered', 'Registrado'),
        ('1_active',     'Activo'),
        ('2_verified',   'Verificado'),
        ('3_referenced', 'Referenciado'),
    ], string='Nivel', default='0_registered')

    br_suspended = fields.Boolean(
        string='Suspendido',
        default=False,
    )

    br_rubros = fields.Char(
        string='Rubros',
        help='Ej: plomero, electricista',
    )

    br_whatsapp = fields.Char(
        string='WhatsApp Batiseñal',
    )

    br_zona = fields.Char(
        string='Zona de cobertura',
        help='Ej: Nordelta, La Barra',
    )

    br_jobs_completed = fields.Integer(
        string='Trabajos completados',
        default=0,
    )

    br_is_provider = fields.Boolean(
        string='Es proveedor BR',
        default=False,
    )