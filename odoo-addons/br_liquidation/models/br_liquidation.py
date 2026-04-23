import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, date

_logger = logging.getLogger(__name__)


class BrLiquidation(models.Model):
    _name = 'br.liquidation'
    _description = 'Liquidación semanal de proveedores'
    _order = 'fecha desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
    )

    fecha = fields.Date(string='Fecha de liquidación', required=True, default=fields.Date.today)

    estado = fields.Selection([
        ('borrador',    'Borrador'),
        ('confirmada',  'Confirmada'),
        ('transferida', 'Transferida'),
    ], string='Estado', default='borrador')

    linea_ids = fields.One2many(
        'br.liquidation.line',
        'liquidacion_id',
        string='Líneas',
    )

    total_amount = fields.Float(
        string='Total a liquidar',
        compute='_compute_total',
        store=True,
    )

    cantidad_ordenes = fields.Integer(
        string='Órdenes incluidas',
        compute='_compute_total',
        store=True,
    )

    notas = fields.Text(string='Notas')

    @api.depends('linea_ids.monto_proveedor')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.linea_ids.mapped('monto_proveedor'))
            rec.cantidad_ordenes = sum(rec.linea_ids.mapped('cantidad_ordenes'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('br.liquidation') or 'Nuevo'
        return super().create(vals_list)

    def action_confirmar(self):
        self.ensure_one()
        if not self.linea_ids:
            raise UserError('No hay líneas de liquidación.')
        self.estado = 'confirmada'

    def action_transferir(self):
        self.ensure_one()
        if self.estado != 'confirmada':
            raise UserError('Confirmá la liquidación antes de transferir.')
        for linea in self.linea_ids:
            linea.orden_ids.write({'state': 'completado'})
            linea.orden_ids.mapped('payment_ids').filtered(
                lambda p: p.status == 'authorized'
            ).write({'status': 'captured'})
        self.estado = 'transferida'
        _logger.info('BR Liquidacion %s transferida: %.2f ARS', self.name, self.total_amount)

    @api.model
    def cron_liquidacion_semanal(self):
        """
        Cron jueves 18:00: agrupa órdenes pago_liberado de la semana y genera liquidación.
        """
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=7)

        ordenes = self.env['br.service.order'].search([
            ('state', '=', 'pago_liberado'),
            ('write_date', '>=', str(inicio_semana)),
            ('provider_id', '!=', False),
            ('payment_method', '=', 'mp'),
        ])

        if not ordenes:
            _logger.info('BR Liquidacion semanal: no hay ordenes a liquidar.')
            return

        liquidacion = self.create({'fecha': hoy})

        proveedores = ordenes.mapped('provider_id')
        for proveedor in proveedores:
            ords_proveedor = ordenes.filtered(lambda o: o.provider_id == proveedor)
            monto = sum(
                p.provider_split
                for o in ords_proveedor
                for p in o.payment_ids.filtered(lambda p: p.status in ('authorized', 'captured'))
            )
            if monto > 0:
                self.env['br.liquidation.line'].create({
                    'liquidacion_id': liquidacion.id,
                    'proveedor_id': proveedor.id,
                    'orden_ids': [(6, 0, ords_proveedor.ids)],
                    'monto_proveedor': monto,
                    'cantidad_ordenes': len(ords_proveedor),
                })

        _logger.info(
            'BR Liquidacion %s creada: %d proveedores, %.2f ARS total',
            liquidacion.name, len(liquidacion.linea_ids), liquidacion.total_amount,
        )


class BrLiquidationLine(models.Model):
    _name = 'br.liquidation.line'
    _description = 'Línea de liquidación por proveedor'

    liquidacion_id = fields.Many2one(
        'br.liquidation',
        string='Liquidación',
        required=True,
        ondelete='cascade',
    )

    proveedor_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        required=True,
        domain=[('br_is_provider', '=', True)],
    )

    orden_ids = fields.Many2many(
        'br.service.order',
        string='Órdenes incluidas',
    )

    cantidad_ordenes = fields.Integer(string='Cantidad de órdenes')

    monto_proveedor = fields.Float(string='Monto a pagar (85%)', digits=(10, 2))

    cbu = fields.Char(
        string='CBU / Alias MP',
        help='Dato de transferencia del proveedor (manual o sincronizado por integración).',
    )

    estado_transferencia = fields.Selection([
        ('pendiente',   'Pendiente'),
        ('transferida', 'Transferida'),
        ('error',       'Error'),
    ], string='Estado', default='pendiente')
