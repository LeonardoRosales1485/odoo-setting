import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class BrSubscription(models.Model):
    _name = 'br.subscription'
    _description = 'Suscripción recurrente de servicio'
    _order = 'proximo_vencimiento asc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
    )

    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
    )

    proveedor_id = fields.Many2one(
        'res.partner',
        string='Proveedor preferido',
        domain=[('br_is_provider', '=', True)],
    )

    rubro = fields.Selection([
        ('plomero',       'Plomero'),
        ('electricista',  'Electricista'),
        ('limpieza',      'Limpieza'),
        ('jardinero',     'Jardinero'),
        ('piletero',      'Piletero'),
        ('parrillero',    'Parrillero'),
        ('ninyera',       'Niñera'),
        ('lava_autos',    'Lava-autos'),
    ], string='Rubro', required=True)

    precio_fijo = fields.Float(string='Precio fijo', required=True, digits=(10, 2))

    frecuencia = fields.Selection([
        ('mensual', 'Mensual'),
        ('anual',   'Anual'),
    ], string='Frecuencia', default='mensual', required=True)

    franja = fields.Selection([
        ('manana',   'Mañana (9-12)'),
        ('mediodia', 'Mediodía (12-15)'),
        ('tarde',    'Tarde (15-18)'),
    ], string='Franja horaria preferida')

    payment_method = fields.Selection([
        ('mp',       'MercadoPago'),
        ('efectivo', 'Efectivo'),
    ], string='Método de pago', default='mp')

    proximo_vencimiento = fields.Date(string='Próximo vencimiento', required=True)

    estado = fields.Selection([
        ('activa',    'Activa'),
        ('pausada',   'Pausada'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='activa')

    orden_ids = fields.One2many(
        'br.service.order',
        'subscription_id',
        string='Órdenes generadas',
    )

    cantidad_ordenes = fields.Integer(
        string='Órdenes generadas',
        compute='_compute_cantidad',
    )

    notas = fields.Text(string='Notas')

    @api.depends('orden_ids')
    def _compute_cantidad(self):
        for rec in self:
            rec.cantidad_ordenes = len(rec.orden_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('br.subscription') or 'Nuevo'
        return super().create(vals_list)

    def action_pausar(self):
        self.ensure_one()
        if self.estado != 'activa':
            raise UserError('Solo se pueden pausar suscripciones activas.')
        self.estado = 'pausada'

    def action_reactivar(self):
        self.ensure_one()
        if self.estado != 'pausada':
            raise UserError('Solo se pueden reactivar suscripciones pausadas.')
        self.estado = 'activa'

    def action_cancelar(self):
        self.ensure_one()
        self.estado = 'cancelada'

    def _crear_orden(self):
        """Crea una br.service.order para el período actual."""
        self.ensure_one()
        orden = self.env['br.service.order'].create({
            'client_id': self.cliente_id.id,
            'provider_id': self.proveedor_id.id if self.proveedor_id else False,
            'rubro': self.rubro,
            'service_type': 'recurrente',
            'amount': self.precio_fijo,
            'payment_method': self.payment_method,
            'franja': self.franja,
            'scheduled_date': self.proximo_vencimiento,
            'subscription_id': self.id,
            'description': 'Orden automática — suscripción %s' % self.name,
        })

        # Activar Batiseñal si hay proveedor preferido, sino crear cola abierta
        if self.proveedor_id and not self.proveedor_id.br_suspended:
            self.env['br.queue.entry'].create({
                'order_id': orden.id,
                'provider_id': self.proveedor_id.id,
                'provider_score': self.proveedor_id.br_score,
                'priority_score': self.proveedor_id.br_score * 0.7,
            })
        else:
            self.env['br.queue.entry'].sudo().create_queue_for_order(orden.id)

        # Avanzar próximo vencimiento
        delta = relativedelta(months=1) if self.frecuencia == 'mensual' else relativedelta(years=1)
        self.proximo_vencimiento = self.proximo_vencimiento + delta

        _logger.info('BR Subscription %s: orden %s creada', self.name, orden.name)
        return orden

    def action_generar_orden(self):
        self.ensure_one()
        if self.estado != 'activa':
            raise UserError('Solo se pueden generar órdenes en suscripciones activas.')
        return self._crear_orden()

    @api.model
    def cron_renovar_suscripciones(self):
        """
        Cron mensual: genera órdenes para suscripciones vencidas hoy.
        """
        hoy = date.today()
        suscripciones = self.search([
            ('estado', '=', 'activa'),
            ('proximo_vencimiento', '<=', str(hoy)),
        ])
        for sub in suscripciones:
            try:
                sub._crear_orden()
            except Exception as e:
                _logger.error('BR Subscription %s error al renovar: %s', sub.name, e)
