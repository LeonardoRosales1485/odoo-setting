import random
import string
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class BrOtp(models.Model):
    _name = 'br.otp'
    _description = 'OTP de autenticación'
    _order = 'create_date desc'

    phone = fields.Char(string='Teléfono', required=True)
    otp_code = fields.Char(string='Código OTP', required=True)
    expires_at = fields.Datetime(string='Expira')
    used = fields.Boolean(string='Usado', default=False)

    @api.model
    def generate(self, phone):
        # Invalida OTPs anteriores del mismo teléfono
        old = self.search([('phone', '=', phone), ('used', '=', False)])
        old.write({'used': True})

        code = ''.join(random.choices(string.digits, k=6))
        otp = self.create({
            'phone': phone,
            'otp_code': code,
            'expires_at': fields.Datetime.now() + timedelta(minutes=10),
        })
        return otp

    @api.model
    def verify(self, phone, code):
        otp = self.search([
            ('phone', '=', phone),
            ('otp_code', '=', code),
            ('used', '=', False),
            ('expires_at', '>=', fields.Datetime.now()),
        ], limit=1)

        if not otp:
            return False

        otp.used = True
        return True
