from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class BrQueueEntry(models.Model):
    _name = 'br.queue.entry'
    _description = 'Cola Batisenal - Entrada de proveedor'
    _order = 'priority_score desc, offered_at asc'

    # Relaciones
    order_id = fields.Many2one(
        'br.service.order',
        string='Orden de servicio',
        required=True,
        ondelete='cascade',
    )

    provider_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        required=True,
        domain=[('br_is_provider', '=', True)],
    )

    # Tiempos
    offered_at = fields.Datetime(
        string='Oferta enviada',
        default=fields.Datetime.now,
    )

    expires_at = fields.Datetime(
        string='Expira a las',
    )

    # Score y prioridad
    provider_score = fields.Float(
        string='Score del proveedor',
        digits=(4, 2),
    )

    priority_score = fields.Float(
        string='Prioridad calculada',
        digits=(6, 4),
        help='score x 0.7 + jobs x 0.3',
    )

    # Estado
    status = fields.Selection([
        ('waiting',  'Esperando respuesta'),
        ('accepted', 'Aceptado'),
        ('expired',  'Expiro'),
        ('skipped',  'Saltado'),
    ], string='Estado', default='waiting')

    # Campos relacionados
    order_state = fields.Selection(
        related='order_id.state',
        string='Estado de la orden',
        store=True,
    )

    order_rubro = fields.Selection(
        related='order_id.rubro',
        string='Rubro',
        store=True,
    )

    order_amount = fields.Float(
        related='order_id.amount',
        string='Monto',
        store=True,
    )

    # Metodos
    @api.model
    def create_queue_for_order(self, order_id):
        order = self.env['br.service.order'].browse(order_id)
        if not order:
            raise UserError('Orden no encontrada.')

        providers = self.env['res.partner'].search([
            ('br_is_provider', '=', True),
            ('br_suspended', '=', False),
            ('br_level', '!=', '0_registered'),
        ])

        if not providers:
            raise UserError('No hay proveedores disponibles.')

        entries = []
        now = fields.Datetime.now()

        for provider in providers:
            priority = (provider.br_score * 0.7) + (provider.br_jobs_completed * 0.3)
            entries.append({
                'order_id': order.id,
                'provider_id': provider.id,
                'offered_at': now,
                'expires_at': now + timedelta(seconds=60),
                'provider_score': provider.br_score,
                'priority_score': priority,
                'status': 'waiting',
            })

        entries.sort(key=lambda x: x['priority_score'], reverse=True)
        created = self.create(entries)
        order.state = 'buscando_proveedor'
        return created

    def action_accept(self):
        self.ensure_one()
        if self.status != 'waiting':
            raise UserError('Esta oferta ya no esta disponible.')

        self.status = 'accepted'

        other = self.search([
            ('order_id', '=', self.order_id.id),
            ('id', '!=', self.id),
            ('status', '=', 'waiting'),
        ])
        other.write({'status': 'skipped'})

        self.order_id.write({
            'provider_id': self.provider_id.id,
            'state': 'proveedor_asignado',
        })
        return True

    def action_expire(self):
        self.ensure_one()
        self.status = 'expired'

    @api.model
    def get_active_queue(self, order_id):
        return self.search([
            ('order_id', '=', order_id),
            ('status', '=', 'waiting'),
        ], order='priority_score desc')
