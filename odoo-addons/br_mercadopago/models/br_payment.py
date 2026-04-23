import logging
import json
from odoo import models, fields, api
from odoo.exceptions import UserError
from .mp_client import MercadoPagoClient

_logger = logging.getLogger(__name__)


class BrPayment(models.Model):
    _name = 'br.payment'
    _description = 'Pago MercadoPago - Botón Rojo'
    _order = 'create_date desc'

    order_id = fields.Many2one(
        'br.service.order',
        string='Orden de servicio',
        required=True,
        ondelete='cascade',
    )

    mp_payment_id = fields.Char(string='ID pago MP', readonly=True)
    mp_payment_link = fields.Char(string='Link de pago')
    mp_preference_id = fields.Char(string='Preference ID', readonly=True)
    mp_raw_response = fields.Text(string='Respuesta MP (raw)', readonly=True)

    status = fields.Selection([
        ('pending',    'Pendiente'),
        ('authorized', 'Autorizado'),
        ('captured',   'Capturado'),
        ('cancelled',  'Cancelado'),
        ('refunded',   'Reembolsado'),
    ], string='Estado', default='pending')

    amount = fields.Float(
        string='Monto total',
        related='order_id.amount',
        store=True,
    )

    payment_method = fields.Selection(
        selection=[
            ('mp',       'MercadoPago'),
            ('efectivo', 'Efectivo'),
        ],
        related='order_id.payment_method',
        string='Método de pago',
        store=True,
    )

    mp_payment_method = fields.Selection([
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('transfer', 'Transferencia'),
        ('wallet', 'Billetera'),
        ('other', 'Otro'),
    ], string='Método de pago MP', default='credit_card')

    mp_fee_percentage = fields.Float(string='Fee % aplicado', readonly=True)
    mp_fee_fixed = fields.Float(string='Fee fijo aplicado', readonly=True)
    mp_fee_amount = fields.Float(string='Fee total ($)', readonly=True, store=True)

    provider_split = fields.Float(
        string='Split proveedor',
        compute='_compute_splits_with_fees',
        store=True,
    )

    br_split = fields.Float(
        string='Comisión BR',
        compute='_compute_splits_with_fees',
        store=True,
    )

    @api.depends('order_id.amount', 'mp_payment_method')
    def _compute_splits_with_fees(self):
        """
        Calcula splits dinámicamente basado en fees actuales de mp.payment.fee.config

        Fórmula:
        1. Fee MP = (monto × fee_percentage%) + fee_fixed
        2. Neto = Monto - Fee MP
        3. BR fee = Neto × 15%
        4. Provider = Neto - BR fee
        """
        fee_config = self.env['mp.payment.fee.config'].sudo()

        for rec in self:
            amount = rec.order_id.amount or 0.0

            # Obtener fees dinámicamente (sin cachés)
            fee_pct, fee_fixed = fee_config.get_fee(rec.mp_payment_method)

            # Calcular fee de MP
            mp_fee = round((amount * fee_pct / 100) + fee_fixed, 2)

            # Neto después del fee de MP
            neto = round(amount - mp_fee, 2)

            # BR recibe 15% del neto
            br_amount = round(neto * 0.15, 2)

            # Provider recibe lo que sobra
            provider_amount = round(neto - br_amount, 2)

            # Guardar para auditoría
            rec.mp_fee_percentage = fee_pct
            rec.mp_fee_fixed = fee_fixed
            rec.mp_fee_amount = mp_fee
            rec.br_split = br_amount
            rec.provider_split = provider_amount

    def action_authorize(self):
        self.ensure_one()
        if self.status != 'pending':
            raise UserError('Solo se pueden autorizar pagos pendientes.')

        # Obtener configuración activa de MP
        try:
            config = self.env['mp.config'].get_active_config()
        except KeyError:
            _logger.warning('mp.config model not found. Using stub configuration.')
            # Crear config de prueba (stub)
            config = None

        if not config:
            # Para pruebas: simular autorización sin credenciales reales
            _logger.warning('No config available, simulating authorize')
            self.write({
                'status': 'authorized',
                'mp_payment_id': f'TEST-{self.order_id.name}',
                'mp_raw_response': json.dumps({'status': 'authorized', 'test': True}),
            })
            self.order_id.state = 'pago_autorizado'
            return

        client = MercadoPagoClient(config)

        # Llamar a API de MP para autorizar
        result = client.authorize_payment(
            self.order_id,
            description=f'Orden {self.order_id.name} - {self.order_id.rubro}',
        )

        if result['success']:
            self.write({
                'status': 'authorized',
                'mp_payment_id': result['mp_id'],
                'mp_raw_response': json.dumps(result['raw_response']),
            })
            self.order_id.state = 'pago_autorizado'
            _logger.info(
                'BR MP authorize success — order %s mp_id %s',
                self.order_id.name, result['mp_id'],
            )
        else:
            error_msg = result.get('error', 'Error desconocido')
            raise UserError(f'Error al autorizar pago: {error_msg}')

    def action_capture(self):
        self.ensure_one()
        if self.status != 'authorized':
            raise UserError('Solo se pueden capturar pagos autorizados.')

        if not self.order_id.provider_id:
            raise UserError('Debe asignar un proveedor a la orden antes de capturar el pago.')

        if not self.mp_payment_id:
            raise UserError('No hay ID de pago MP para capturar.')

        # Obtener configuración activa de MP
        try:
            config = self.env['mp.config'].get_active_config()
        except KeyError:
            _logger.warning('mp.config model not found. Using stub configuration.')
            config = None

        if not config:
            # Para pruebas: simular captura sin credenciales reales
            _logger.warning('No config available, simulating capture')
            self.write({
                'status': 'captured',
                'mp_raw_response': json.dumps({'status': 'captured', 'test': True}),
            })
            self.order_id.state = 'pago_liberado'
            return

        client = MercadoPagoClient(config)

        # Llamar a API de MP para capturar
        result = client.capture_payment(self.mp_payment_id)

        if result['success']:
            self.write({
                'status': 'captured',
                'mp_raw_response': json.dumps(result['raw_response']),
            })
            self.order_id.state = 'pago_liberado'
            _logger.info(
                'BR MP capture success — order %s provider %.2f BR %.2f',
                self.order_id.name, self.provider_split, self.br_split,
            )
        else:
            error_msg = result.get('error', 'Error desconocido')
            raise UserError(f'Error al capturar pago: {error_msg}')

    def action_cancel(self):
        self.ensure_one()
        if self.status not in ('pending', 'authorized'):
            raise UserError('No se puede cancelar un pago en estado %s.' % self.status)

        # Si es autorizado, hay que cancelarlo en MP
        if self.status == 'authorized' and self.mp_payment_id:
            try:
                config = self.env['mp.config'].get_active_config()
            except KeyError:
                _logger.warning('mp.config model not found, simulating cancel')
                config = None

            if config:
                client = MercadoPagoClient(config)
                result = client.cancel_payment(self.mp_payment_id)

                if not result['success']:
                    error_msg = result.get('error', 'Error desconocido')
                    raise UserError(f'Error al cancelar pago en MP: {error_msg}')

                self.write({
                    'status': 'cancelled',
                    'mp_raw_response': json.dumps(result['raw_response']),
                })
            else:
                # Sin config, solo actualizar estado localmente
                self.write({
                    'status': 'cancelled',
                    'mp_raw_response': json.dumps({'status': 'cancelled', 'test': True}),
                })
        else:
            self.status = 'cancelled'

        _logger.info('BR MP cancel — order %s', self.order_id.name)

    def action_refund(self):
        self.ensure_one()
        if self.status != 'captured':
            raise UserError('Solo se pueden reembolsar pagos capturados.')
        _logger.info('BR MP refund stub — order %s', self.order_id.name)
        self.status = 'refunded'

    @api.model
    def process_mp_webhook(self, payload):
        """
        Procesa webhooks de MercadoPago Advanced Payments API.

        Tipos de eventos:
        - payment.authorized: Pago fue autorizado
        - payment.captured: Pago fue capturado
        - payment.cancelled: Pago fue cancelado
        - payment.refunded: Pago fue reembolsado
        """
        # Buscar el ID de pago en el payload
        mp_id = str(payload.get('data', {}).get('id') or payload.get('id', ''))
        if not mp_id:
            _logger.warning('BR MP webhook sin payment id: %s', payload)
            return False

        payment = self.search([('mp_payment_id', '=', mp_id)], limit=1)
        if not payment:
            _logger.warning('BR MP webhook: pago %s no encontrado', mp_id)
            return False

        # Guardar response completa
        payment.mp_raw_response = json.dumps(payload)

        # Procesar según tipo de evento
        action = payload.get('action', '')
        mp_status = payload.get('status', '')

        _logger.info(
            'BR MP webhook: pago %s action=%s status=%s current_status=%s',
            mp_id, action, mp_status, payment.status,
        )

        # Evento de autorización (el pago fue autorizado en MP)
        if action == 'payment.authorized' or mp_status == 'authorized':
            if payment.status == 'pending':
                payment.write({'status': 'authorized'})
                payment.order_id.state = 'pago_autorizado'
                _logger.info('BR MP webhook: pago %s → authorized', mp_id)
                return True

        # Evento de captura (el pago fue capturado en MP)
        elif action == 'payment.captured' or mp_status == 'captured':
            if payment.status == 'authorized':
                payment.write({'status': 'captured'})
                payment.order_id.state = 'pago_liberado'
                _logger.info('BR MP webhook: pago %s → captured', mp_id)
                return True

        # Evento de cancelación
        elif action == 'payment.cancelled' or mp_status == 'cancelled':
            if payment.status in ('pending', 'authorized'):
                payment.write({'status': 'cancelled'})
                payment.order_id.state = 'cancelado'
                _logger.info('BR MP webhook: pago %s → cancelled', mp_id)
                return True

        # Evento de reembolso
        elif action == 'payment.refunded' or mp_status == 'refunded':
            if payment.status == 'captured':
                payment.write({'status': 'refunded'})
                _logger.info('BR MP webhook: pago %s → refunded', mp_id)
                return True

        _logger.warning(
            'BR MP webhook: pago %s estado inesperado action=%s status=%s',
            mp_id, action, mp_status,
        )
        return False
