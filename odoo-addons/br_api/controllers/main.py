import json
import logging
import urllib.request
import urllib.error

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    return request.make_response(
        json.dumps(data),
        headers=[('Content-Type', 'application/json')],
        status=status,
    )


def _error(msg, status=400):
    return _json_response({'error': msg}, status)


def _auth_jwt(req):
    """Verifica Bearer token. Retorna br.api.token o None."""
    auth = req.httprequest.headers.get('Authorization', '')
    _logger.info('DEBUG _auth_jwt: Authorization header = "%s"', auth)
    if not auth.startswith('Bearer '):
        _logger.info('DEBUG _auth_jwt: No Bearer prefix found')
        return None
    token_str = auth[7:]
    _logger.info('DEBUG _auth_jwt: Extracted token = "%s..."', token_str[:20] if token_str else '')
    result = request.env['br.api.token'].sudo().authenticate(token_str)
    _logger.info('DEBUG _auth_jwt: authenticate() returned %s', bool(result))
    return result


def _auth_api_key(req):
    """Verifica X-BR-API-Key. Retorna br.api.key o None."""
    key = req.httprequest.headers.get('X-BR-API-Key', '')
    if not key:
        return None
    return request.env['br.api.key'].sudo().authenticate(key)


def _require_auth(req):
    """Acepta JWT (app) o API Key (mop-core-ng). Retorna (token_or_key, role, partner_id)."""
    token = _auth_jwt(req)
    if token:
        return token, token.role, token.partner_id.id

    ws = _auth_api_key(req)
    if ws:
        return ws, 'workspace', None

    return None, None, None


def _ensure_sequence(env, code, prefix):
    """Crea la secuencia si no existe."""
    seq = env['ir.sequence'].sudo().search([('code', '=', code)], limit=1)
    if not seq:
        seq = env['ir.sequence'].sudo().create({
            'name': f'Secuencia {code}',
            'code': code,
            'prefix': prefix,
            'padding': 4,
            'number_next': 1,
            'number_increment': 1,
        })
        _logger.info('Creada secuencia %s', code)
    else:
        _logger.info('Secuencia %s ya existe: id=%s', code, seq.id)

    # Verifica que la secuencia se puede usar
    test = env['ir.sequence'].sudo().next_by_code(code)
    _logger.info('Test next_by_code(%s) = %s', code, test)
    return seq


class BrApiController(http.Controller):

    # ────────────────────────────────────────────────────────────
    # AUTH
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/auth/otp/request', type='http', auth='none',
                methods=['POST'], csrf=False)
    def otp_request(self, **_kwargs):
        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        phone = (data.get('phone') or '').strip()
        if not phone:
            return _error('phone requerido')

        otp = request.env['br.otp'].sudo().generate(phone)

        # TODO: enviar OTP por WA/SMS. Por ahora lo logueamos.
        _logger.info('BR OTP %s → %s', phone, otp.otp_code)

        return _json_response({'message': 'OTP enviado', 'phone': phone})

    @http.route('/br/api/auth/otp/verify', type='http', auth='none',
                methods=['POST'], csrf=False)
    def otp_verify(self, **_kwargs):
        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        phone = (data.get('phone') or '').strip()
        code = (data.get('otp') or '').strip()
        if not phone or not code:
            return _error('phone y otp requeridos')

        ok = request.env['br.otp'].sudo().verify(phone, code)
        if not ok:
            return _error('OTP inválido o expirado', 401)

        # Busca o crea partner por teléfono
        partner = request.env['res.partner'].sudo().search(
            [('phone', '=', phone)], limit=1
        )
        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': phone,
                'phone': phone,
            })

        role = 'provider' if partner.br_is_provider else 'client'
        token = request.env['br.api.token'].sudo().create_for_partner(partner.id, role)

        return _json_response({
            'token': token.token,
            'role': role,
            'partner_id': partner.id,
            'expires_at': token.expires_at and fields.Datetime.to_string(token.expires_at),
        })

    @http.route('/br/api/auth/refresh', type='http', auth='none',
                methods=['POST'], csrf=False)
    def token_refresh(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role == 'workspace':
            return _error('Token inválido', 401)

        new_token = request.env['br.api.token'].sudo().create_for_partner(partner_id, role)
        return _json_response({
            'token': new_token.token,
            'role': role,
            'expires_at': new_token.expires_at and fields.Datetime.to_string(new_token.expires_at),
        })

    # ────────────────────────────────────────────────────────────
    # ÓRDENES — clientes autenticados o mop-core-ng
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/orders/create', type='http', auth='none',
                methods=['POST'], csrf=False)
    def orders_create(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        required = ['rubro', 'descripcion', 'fecha', 'franja', 'payment_method']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return _error('Campos requeridos: %s' % ', '.join(missing))

        # En workspace el cliente viene en el body como wa_id/phone
        if role == 'workspace':
            phone = data.get('wa_id') or data.get('phone', '')
            client = request.env['res.partner'].sudo().search(
                [('phone', '=', phone)], limit=1
            )
            if not client:
                client = request.env['res.partner'].sudo().create({
                    'name': phone, 'phone': phone,
                })
        else:
            client = request.env['res.partner'].sudo().browse(partner_id)

        # Buscar el último ID de orden para generar el siguiente
        last_order = request.env['br.service.order'].sudo().search(
            [], order='id desc', limit=1
        )
        next_number = (last_order.id + 1) if last_order else 1
        order_name = f'BR-{next_number:04d}'

        vals = {
            'client_id': client.id,
            'rubro': data['rubro'],
            'description': data['descripcion'],
            'scheduled_date': data['fecha'],
            'franja': data['franja'],
            'payment_method': data['payment_method'],
            'amount': data.get('amount', 0.0),
            'name': order_name,  # Asignar el nombre generado
        }

        order = request.env['br.service.order'].sudo().create(vals)

        response = {
            'order_id': order.name,
            'state': order.state,
            'payment_method': order.payment_method,
        }

        if order.payment_method == 'mp':
            # Crea pago en estado pending
            payment = request.env['br.payment'].sudo().create({'order_id': order.id})
            response['mp_payment_link'] = payment.mp_payment_link or ''
            response['monto_autorizar'] = order.amount
            response['payment_status'] = payment.status
            # Nota: Cliente debe llamar a /br/api/payments/{order_name}/authorize para autorizar
        else:
            # Efectivo: pasar a estado pendiente cobro
            order.state = 'pendiente_cobro_efvo'
            response['recargo_efectivo'] = round(order.amount * 0.05, 2)

        return _json_response(response, 201)

    @http.route('/br/api/payments/<string:order_name>/authorize', type='http', auth='none',
                methods=['POST'], csrf=False)
    def payment_authorize(self, order_name, **_kwargs):
        """Autoriza un pago en MercadoPago (sin capturar aún)."""
        _logger.info('payment_authorize called with order_name=%s', order_name)
        auth, _, _ = _require_auth(request)
        _logger.info('payment_authorize: _require_auth returned auth=%s', bool(auth))
        if not auth:
            _logger.warning('payment_authorize: No auth found in request')
            return _error('No autorizado', 401)

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        if order.payment_method != 'mp':
            return _error('La orden no es de pago con MercadoPago', 400)

        # Buscar pago existente en estado pending
        payment = order.payment_ids.filtered(lambda p: p.status == 'pending')
        if not payment:
            return _error('No hay pago pendiente para autorizar', 400)

        try:
            payment.action_authorize()
            return _json_response({
                'order_id': order.name,
                'payment_id': payment.mp_payment_id,
                'status': payment.status,
                'amount': order.amount,
            })
        except Exception as e:
            _logger.error('Error al autorizar pago: %s', str(e))
            return _error(str(e), 400)

    @http.route('/br/api/payments/<string:order_name>/capture', type='http', auth='none',
                methods=['POST'], csrf=False)
    def payment_capture(self, order_name, **_kwargs):
        """Captura un pago previamente autorizado en MercadoPago."""
        auth, _, _ = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        if order.payment_method != 'mp':
            return _error('La orden no es de pago con MercadoPago', 400)

        # Buscar pago existente en estado authorized
        payment = order.payment_ids.filtered(lambda p: p.status == 'authorized')
        if not payment:
            return _error('No hay pago autorizado para capturar', 400)

        try:
            payment.action_capture()
            return _json_response({
                'order_id': order.name,
                'payment_id': payment.mp_payment_id,
                'status': payment.status,
                'provider_split': payment.provider_split,
                'br_split': payment.br_split,
            })
        except Exception as e:
            _logger.error('Error al capturar pago: %s', str(e))
            return _error(str(e), 400)

    @http.route('/br/api/orders/<string:order_name>/status', type='http', auth='none',
                methods=['GET'], csrf=False)
    def order_status(self, order_name, **_kwargs):
        auth, _, _ = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        data = {
            'order_id': order.name,
            'state': order.state,
            'rubro': order.rubro,
            'amount': order.amount,
            'payment_method': order.payment_method,
            'provider': None,
        }
        if order.provider_id:
            data['provider'] = {
                'name': order.provider_id.name,
                'score': order.provider_id.br_score,
                'phone': order.provider_id.br_whatsapp,
            }
        return _json_response(data)

    @http.route('/br/api/orders/history', type='http', auth='none',
                methods=['GET'], csrf=False)
    def order_history(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role not in ('client',):
            return _error('No autorizado', 401)

        orders = request.env['br.service.order'].sudo().search(
            [('client_id', '=', partner_id)],
            order='create_date desc', limit=50,
        )
        return _json_response([{
            'order_id': o.name,
            'state': o.state,
            'rubro': o.rubro,
            'amount': o.amount,
            'scheduled_date': o.scheduled_date and str(o.scheduled_date),
        } for o in orders])

    # ────────────────────────────────────────────────────────────
    # WEBHOOKS — MercadoPago (sin autenticación, solo validación de token)
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/webhooks/mercadopago', type='http', auth='none',
                methods=['POST'], csrf=False)
    def webhook_mercadopago(self, **_kwargs):
        """
        Recibe webhooks de MercadoPago.

        MercadoPago envía eventos como:
        - payment.authorized
        - payment.captured
        - payment.cancelled
        - payment.refunded
        """
        try:
            payload = json.loads(request.httprequest.data)
        except Exception as e:
            _logger.error('webhook_mercadopago: JSON inválido: %s', str(e))
            return _json_response({'error': 'JSON inválido'}, 400)

        _logger.info('webhook_mercadopago: received payload: %s', json.dumps(payload)[:200])

        # TODO: Validar signature de MercadoPago cuando tengamos credenciales reales
        # Por ahora, procesar el evento directamente
        try:
            result = request.env['br.payment'].sudo().process_mp_webhook(payload)
            if result:
                return _json_response({'status': 'processed'}, 200)
            else:
                return _json_response({'status': 'ignored'}, 200)
        except Exception as e:
            _logger.error('webhook_mercadopago: error processing: %s', str(e))
            return _json_response({'error': str(e)}, 500)

    @http.route('/br/api/orders/<string:order_name>/confirm', type='http', auth='none',
                methods=['POST'], csrf=False)
    def order_confirm(self, order_name, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        rating = str(data.get('rating', ''))
        if rating not in ('1', '2', '3', '4', '5'):
            return _error('rating debe ser 1-5')

        order.write({'rating': rating})

        # Liberar pago si está en trabajo_completado
        if order.state == 'trabajo_completado':
            order.state = 'pago_liberado'
            # La captura debe ocurrir via MercadoPago webhook, no aquí

        _send_webhook(request.env, order, 'payment_released')

        return _json_response({'order_id': order.name, 'state': order.state, 'rating': rating})

    @http.route('/br/api/orders/<string:order_name>/dispute', type='http', auth='none',
                methods=['POST'], csrf=False)
    def order_dispute(self, order_name, **_kwargs):
        auth, _, _ = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        order.action_abrir_disputa()
        _send_webhook(request.env, order, 'dispute_opened', {'motivo': data.get('motivo', '')})

        return _json_response({'order_id': order.name, 'state': order.state})

    @http.route('/br/api/orders/<string:order_name>/cash-collected', type='http',
                auth='none', methods=['POST'], csrf=False)
    def cash_collected(self, order_name, **_kwargs):
        auth, _, _ = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        cobrador_id = data.get('cobrador_id')
        monto = data.get('monto_cobrado', order.amount)

        try:
            order.action_cash_collected(cobrador_id, monto)
        except Exception as e:
            return _error(str(e))

        _send_webhook(request.env, order, 'payment_released')
        return _json_response({'order_id': order.name, 'state': order.state})

    # ────────────────────────────────────────────────────────────
    # PROVEEDORES
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/providers/me/queue', type='http', auth='none',
                methods=['GET'], csrf=False)
    def provider_queue(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        entries = request.env['br.queue.entry'].sudo().search([
            ('provider_id', '=', partner_id),
            ('status', '=', 'waiting'),
        ], limit=1)

        if not entries:
            return _json_response({'offer': None})

        e = entries[0]
        return _json_response({
            'offer': {
                'entry_id': e.id,
                'order_id': e.order_id.name,
                'rubro': e.order_rubro,
                'amount': e.order_amount,
                'expires_at': e.expires_at and fields.Datetime.to_string(e.expires_at),
                'priority_score': e.priority_score,
            }
        })

    @http.route('/br/api/providers/me/accept', type='http', auth='none',
                methods=['POST'], csrf=False)
    def provider_accept(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order_name = data.get('order_id', '')
        entry = request.env['br.queue.entry'].sudo().search([
            ('provider_id', '=', partner_id),
            ('order_id.name', '=', order_name),
            ('status', '=', 'waiting'),
        ], limit=1)

        if not entry:
            return _error('Oferta no encontrada o expirada', 404)

        try:
            entry.action_accept()
        except Exception as e:
            return _error(str(e))

        _send_webhook(request.env, entry.order_id, 'provider_assigned', {
            'provider_name': entry.provider_id.name,
            'provider_score': entry.provider_id.br_score,
            'provider_photo': '',
            'eta_minutes': 25,
        })

        return _json_response({'order_id': order_name, 'state': entry.order_id.state})

    @http.route('/br/api/providers/me/arrived', type='http', auth='none',
                methods=['POST'], csrf=False)
    def provider_arrived(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order = request.env['br.service.order'].sudo().search([
            ('name', '=', data.get('order_id', '')),
            ('provider_id', '=', partner_id),
        ], limit=1)
        if not order:
            return _error('Orden no encontrada', 404)

        order.action_llego()
        _send_webhook(request.env, order, 'provider_arrived')

        return _json_response({'order_id': order.name, 'state': order.state})

    @http.route('/br/api/providers/me/upload-photo', type='http', auth='none',
                methods=['POST'], csrf=False)
    def provider_upload_photo(self, **_kwargs):
        """Sube foto ANTES del trabajo para una orden."""
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order_name = data.get('order_id', '')
        photo_base64 = data.get('photo_base64', '')  # Foto en base64

        if not photo_base64:
            return _error('photo_base64 requerido')

        order = request.env['br.service.order'].sudo().search([
            ('name', '=', order_name),
            ('provider_id', '=', partner_id),
        ], limit=1)
        if not order:
            return _error('Orden no encontrada', 404)

        try:
            # Decodificar base64 y guardar en photo_before
            import base64
            photo_binary = base64.b64decode(photo_base64)
            order.photo_before = photo_binary
        except Exception as e:
            return _error(f'Error al procesar foto: {str(e)}')

        return _json_response({'order_id': order.name, 'photo_uploaded': True})

    @http.route('/br/api/providers/me/done', type='http', auth='none',
                methods=['POST'], csrf=False)
    def provider_done(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order = request.env['br.service.order'].sudo().search([
            ('name', '=', data.get('order_id', '')),
            ('provider_id', '=', partner_id),
        ], limit=1)
        if not order:
            return _error('Orden no encontrada', 404)

        order.action_trabajo_completado()

        # TODO: Solicitar captura a MercadoPago aquí
        # payment = order.payment_ids.filtered(lambda p: p.status == 'authorized')
        # if payment:
        #     mp_api.capture(payment[0].mp_payment_id)
        # La respuesta de MP llegará via webhook

        _send_webhook(request.env, order, 'work_done')

        return _json_response({'order_id': order.name, 'state': order.state})

    @http.route('/br/api/providers/me/history', type='http', auth='none',
                methods=['GET'], csrf=False)
    def provider_history(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        orders = request.env['br.service.order'].sudo().search(
            [('provider_id', '=', partner_id)],
            order='create_date desc', limit=50,
        )
        return _json_response([{
            'order_id': o.name,
            'state': o.state,
            'rubro': o.rubro,
            'amount': o.amount,
            'scheduled_date': o.scheduled_date and str(o.scheduled_date),
        } for o in orders])

    @http.route('/br/api/providers/me/earnings', type='http', auth='none',
                methods=['GET'], csrf=False)
    def provider_earnings(self, **_kwargs):
        auth, role, partner_id = _require_auth(request)
        if not auth or role != 'provider':
            return _error('No autorizado', 401)

        payments = request.env['br.payment'].sudo().search([
            ('order_id.provider_id', '=', partner_id),
            ('status', '=', 'captured'),
        ])
        total = sum(payments.mapped('provider_split'))

        return _json_response({
            'proxima_liquidacion': 'Jueves',
            'monto_estimado': total,
            'cantidad_ordenes': len(payments),
        })

    # ────────────────────────────────────────────────────────────
    # BATISEÑAL
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/batisena/next', type='http', auth='none',
                methods=['POST'], csrf=False)
    def batisena_next(self, **_kwargs):
        auth, _, _ = _require_auth(request)
        if not auth:
            return _error('No autorizado', 401)

        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        order_name = data.get('order_id', '')
        order = request.env['br.service.order'].sudo().search(
            [('name', '=', order_name)], limit=1
        )
        if not order:
            return _error('Orden no encontrada', 404)

        # Marca la entrada activa como expirada
        active_entry = request.env['br.queue.entry'].sudo().search([
            ('order_id', '=', order.id),
            ('status', '=', 'waiting'),
        ], order='priority_score desc', limit=1)

        if active_entry:
            active_entry.action_expire()

        # Verifica si hay más proveedores en espera
        next_entry = request.env['br.queue.entry'].sudo().search([
            ('order_id', '=', order.id),
            ('status', '=', 'waiting'),
        ], order='priority_score desc', limit=1)

        if next_entry:
            _send_webhook(request.env, order, 'batisena_offer', {
                'provider_wa_id': next_entry.provider_id.br_whatsapp,
                'entry_id': next_entry.id,
                'rubro': order.rubro,
                'monto': order.amount,
            })
            return _json_response({'status': 'next_offered', 'provider': next_entry.provider_id.name})

        # Sin más proveedores
        order.action_sin_match()
        _send_webhook(request.env, order, 'sin_match')
        return _json_response({'status': 'sin_match', 'order_id': order_name})

    # ────────────────────────────────────────────────────────────
    # CONFIG
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/config/rubros', type='http', auth='none',
                methods=['GET'], csrf=False)
    def config_rubros(self, **_kwargs):
        rubros = [
            {'rubro_id': 'plomero',      'rubro_nombre': 'Plomero',       'precio_base': 3500},
            {'rubro_id': 'electricista', 'rubro_nombre': 'Electricista',  'precio_base': 4000},
            {'rubro_id': 'limpieza',     'rubro_nombre': 'Limpieza',      'precio_base': 2500},
            {'rubro_id': 'jardinero',    'rubro_nombre': 'Jardinero',     'precio_base': 3000},
            {'rubro_id': 'piletero',     'rubro_nombre': 'Piletero',      'precio_base': 3500},
            {'rubro_id': 'parrillero',   'rubro_nombre': 'Parrillero',    'precio_base': 2000},
            {'rubro_id': 'ninyera',      'rubro_nombre': 'Niñera',        'precio_base': 2500},
            {'rubro_id': 'lava_autos',   'rubro_nombre': 'Lava-autos',    'precio_base': 1500},
        ]
        return _json_response(rubros)

    # ────────────────────────────────────────────────────────────
    # WEBHOOK MP ENTRANTE
    # ────────────────────────────────────────────────────────────

    @http.route('/br/api/mp/webhook', type='http', auth='none',
                methods=['POST'], csrf=False)
    def mp_webhook(self, **_kwargs):
        try:
            payload = json.loads(request.httprequest.data)
        except Exception:
            return _error('JSON inválido')

        request.env['br.payment'].sudo().process_mp_webhook(payload)
        return _json_response({'ok': True})


# ────────────────────────────────────────────────────────────────
# Helper — webhook saliente a mop-core-ng
# ────────────────────────────────────────────────────────────────

def _send_webhook(env, order, event, extra_data=None):
    """
    Envía un POST a la URL configurada en el workspace activo (br.api.key.webhook_url).
    No bloquea si falla — solo loguea el error.
    """
    workspace = env['br.api.key'].sudo().search([('is_active', '=', True)], limit=1)
    if not workspace or not workspace.webhook_url:
        return

    payload = {
        'event': event,
        'order_id': order.name,
        'state': order.state,
        'data': extra_data or {},
    }

    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            workspace.webhook_url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        _logger.warning('BR webhook %s → %s falló: %s', event, workspace.webhook_url, e)
