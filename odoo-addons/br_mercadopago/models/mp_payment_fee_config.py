from odoo import models, fields, api


class MpPaymentFeeConfig(models.Model):
    _name = 'mp.payment.fee.config'
    _description = 'Configuración de fees de MercadoPago'
    _order = 'payment_method asc'

    payment_method = fields.Selection([
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('transfer', 'Transferencia bancaria'),
        ('wallet', 'Billetera de MP'),
        ('other', 'Otro'),
    ], string='Método de pago', required=True, unique=True)

    fee_percentage = fields.Float(
        string='Fee %',
        default=2.9,
        help='Porcentaje de comisión (ej: 2.9 para 2.9%)',
    )

    fee_fixed = fields.Float(
        string='Fee fijo ($)',
        default=0.30,
        help='Comisión fija en pesos (ej: 0.30)',
    )

    is_active = fields.Boolean(
        string='Activo',
        default=True,
    )

    @api.model
    def get_fee(self, payment_method='credit_card'):
        """
        Obtiene el fee para un método de pago (dinámico, sin cachés).
        Retorna: (fee_percentage, fee_fixed)
        """
        config = self.search([
            ('payment_method', '=', payment_method),
            ('is_active', '=', True),
        ], limit=1)
        if config:
            return config.fee_percentage, config.fee_fixed
        # Defaults si no existe configuración
        return 2.9, 0.30
