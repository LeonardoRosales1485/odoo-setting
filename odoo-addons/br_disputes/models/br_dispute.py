import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class BrDispute(models.Model):
    _name = 'br.dispute'
    _description = 'Disputa de orden Botón Rojo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_apertura desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
    )

    order_id = fields.Many2one(
        'br.service.order',
        string='Orden',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='order_id.client_id',
        store=True,
    )

    proveedor_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        related='order_id.provider_id',
        store=True,
    )

    motivo = fields.Text(string='Motivo del reclamo', required=True)

    estado = fields.Selection([
        ('abierta',     'Abierta'),
        ('en_revision', 'En revisión'),
        ('resuelta',    'Resuelta'),
        ('cerrada',     'Cerrada'),
    ], string='Estado', default='abierta', tracking=True)

    resolucion = fields.Selection([
        ('reembolso',      'Reembolso al cliente'),
        ('sin_reembolso',  'Sin reembolso'),
        ('re_servicio',    'Re-servicio'),
    ], string='Resolución', tracking=True)

    asignado_a = fields.Many2one(
        'res.users',
        string='Asignado a',
        domain=[('share', '=', False)],
        tracking=True,
    )

    fecha_apertura = fields.Datetime(
        string='Fecha apertura',
        default=fields.Datetime.now,
    )

    fecha_limite = fields.Datetime(
        string='Fecha límite SLA (48h)',
        compute='_compute_fecha_limite',
        store=True,
    )

    fecha_resolucion = fields.Datetime(string='Fecha resolución')

    alerta_sla = fields.Boolean(
        string='Alerta SLA',
        compute='_compute_alerta_sla',
        store=True,
    )

    notas_resolucion = fields.Text(string='Notas de resolución')

    monto_orden = fields.Float(
        related='order_id.amount',
        string='Monto orden',
        store=True,
    )

    @api.depends('fecha_apertura')
    def _compute_fecha_limite(self):
        for rec in self:
            if rec.fecha_apertura:
                rec.fecha_limite = rec.fecha_apertura + timedelta(hours=48)
            else:
                rec.fecha_limite = False

    @api.depends('fecha_apertura', 'estado')
    def _compute_alerta_sla(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.estado in ('abierta', 'en_revision') and rec.fecha_apertura:
                horas = (now - rec.fecha_apertura).total_seconds() / 3600
                rec.alerta_sla = horas >= 42
            else:
                rec.alerta_sla = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('br.dispute') or 'Nuevo'
        return super().create(vals_list)

    def action_iniciar_revision(self):
        self.ensure_one()
        if self.estado != 'abierta':
            raise UserError('Solo se pueden revisar disputas abiertas.')
        self.estado = 'en_revision'

    def action_resolver(self, resolucion, notas=''):
        self.ensure_one()
        if self.estado not in ('abierta', 'en_revision'):
            raise UserError('La disputa ya está resuelta o cerrada.')
        if resolucion not in ('reembolso', 'sin_reembolso', 're_servicio'):
            raise UserError('Resolución inválida.')

        self.write({
            'estado': 'resuelta',
            'resolucion': resolucion,
            'fecha_resolucion': fields.Datetime.now(),
            'notas_resolucion': notas,
        })

        if resolucion == 'reembolso':
            payment = self.order_id.payment_ids.filtered(
                lambda p: p.status in ('authorized', 'captured')
            )
            if payment:
                payment[0].action_refund()
            self.order_id.state = 'cancelado'
        elif resolucion == 'sin_reembolso':
            payment = self.order_id.payment_ids.filtered(
                lambda p: p.status == 'authorized'
            )
            if payment:
                payment[0].action_capture()
            self.order_id.state = 'completado'

    def action_resolver_reembolso(self):
        for rec in self:
            rec.action_resolver('reembolso')

    def action_resolver_sin_reembolso(self):
        for rec in self:
            rec.action_resolver('sin_reembolso')

    def action_resolver_re_servicio(self):
        for rec in self:
            rec.action_resolver('re_servicio')

    def action_cerrar(self):
        self.ensure_one()
        self.estado = 'cerrada'

    @api.model
    def cron_check_sla(self):
        """
        Cron: cada hora revisa disputas sin resolver cerca del límite SLA.
        A las 42h envía alerta a Ops por mail.thread.
        """
        now = fields.Datetime.now()
        limite_42h = now - timedelta(hours=42)

        disputas = self.search([
            ('estado', 'in', ('abierta', 'en_revision')),
            ('fecha_apertura', '<=', limite_42h),
            ('alerta_sla', '=', False),
        ])

        for disputa in disputas:
            disputa.alerta_sla = True
            disputa.message_post(
                body='⚠️ ALERTA SLA: Esta disputa lleva más de 42 horas sin resolución. Límite: %s'
                     % fields.Datetime.to_string(disputa.fecha_limite),
                subject='Alerta SLA disputa %s' % disputa.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            _logger.warning('BR Disputa SLA alert: %s', disputa.name)
