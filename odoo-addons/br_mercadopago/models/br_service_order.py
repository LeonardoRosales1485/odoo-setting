from odoo import models, fields, api
from odoo.exceptions import UserError


class BrServiceOrderPayment(models.Model):
    _inherit = 'br.service.order'

    payment_ids = fields.One2many(
        'br.payment',
        'order_id',
        string='Pagos',
    )

    payment_count = fields.Integer(
        string='Nº pagos',
        compute='_compute_payment_count',
    )

    mp_payment_link = fields.Char(
        string='Link de pago MP',
        compute='_compute_mp_link',
        store=False,
    )

    # Campos Flow B (efectivo)
    cobrador_id = fields.Many2one(
        'res.users',
        string='Cobrador asignado',
        domain=[('share', '=', False)],
    )

    cash_collected_at = fields.Datetime(string='Cobrado el')
    cash_collected_amount = fields.Float(string='Monto cobrado')

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends('payment_ids.mp_payment_link')
    def _compute_mp_link(self):
        for rec in self:
            active = rec.payment_ids.filtered(
                lambda p: p.status in ('pending', 'authorized')
            )
            rec.mp_payment_link = active[:1].mp_payment_link if active else False

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagos',
            'res_model': 'br.payment',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_create_payment(self):
        """Crea un br.payment para esta orden y lo autoriza (Flow A MP)."""
        self.ensure_one()
        if self.payment_method != 'mp':
            raise UserError('Esta acción es solo para pagos con MercadoPago.')
        if self.payment_ids.filtered(lambda p: p.status in ('pending', 'authorized', 'captured')):
            raise UserError('Ya existe un pago activo para esta orden.')

        payment = self.env['br.payment'].create({'order_id': self.id})
        payment.action_authorize()
        return True

    def action_cash_collected(self, cobrador_id, monto):
        """Marca la orden como cobrada en efectivo. Llamado desde br_api."""
        self.ensure_one()
        if self.payment_method != 'efectivo':
            raise UserError('Esta orden no es de pago en efectivo.')
        if self.state != 'pendiente_cobro_efvo':
            raise UserError('La orden no está en estado pendiente de cobro.')

        cobrador = self.env['res.users'].browse(cobrador_id)
        if not cobrador.exists():
            raise UserError('Cobrador no encontrado.')

        self.write({
            'cobrador_id': cobrador.id,
            'cash_collected_at': fields.Datetime.now(),
            'cash_collected_amount': monto,
            'state': 'completado',
        })

        # Crear registro de pago efectivo
        self.env['br.payment'].create({
            'order_id': self.id,
            'status': 'captured',
            'mp_payment_id': 'CASH-%s' % self.name,
        })
