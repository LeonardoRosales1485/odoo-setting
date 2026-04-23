import logging
import json
import requests
from datetime import datetime

_logger = logging.getLogger(__name__)


class MercadoPagoClient:
    """Cliente para integración con MercadoPago Advanced Payments API."""

    def __init__(self, config):
        """
        Inicializa el cliente MP.

        Args:
            config: Instancia de mp.config
        """
        self.config = config
        self.api_url = config.api_url
        self.seller_id = config.seller_id
        self.access_token = config.access_token
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }

    def authorize_payment(self, order, description='', notification_url=''):
        """
        Autoriza un pago sin capturarlo (authorize only).

        Args:
            order: instancia de br.service.order
            description: descripción del pago
            notification_url: URL para webhook de MP

        Returns:
            dict con respuesta de MP o error
        """
        try:
            if not order.amount or order.amount <= 0:
                return {
                    'success': False,
                    'error': 'Monto inválido para autorización',
                }

            payload = {
                'payer': {
                    'email': order.client_id.email or f'cliente{order.id}@botonrojo.test',
                    'first_name': order.client_id.name or 'Cliente',
                    'identification': {
                        'type': 'DNI',
                        'number': '12345678',  # TODO: obtener del cliente
                    },
                },
                'payments': [
                    {
                        'amount': float(order.amount),
                        'currency_id': 'ARS',
                        'description': description or f'Orden {order.name}',
                        'capture': False,  # IMPORTANTE: authorize only, no capture
                        'installments': 1,
                        'processing_mode': 'aggregator',
                    }
                ],
                'external_reference': order.name,
                'notification_url': notification_url or f'https://botonrojo.test/br/mp/webhooks/notif',
            }

            url = f'{self.api_url}/v1/advanced_payments'
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code in (200, 201):
                data = response.json()
                _logger.info(
                    'MP authorize success: order %s amount %.2f mp_id %s',
                    order.name, order.amount, data.get('id'),
                )
                return {
                    'success': True,
                    'mp_id': str(data.get('id', '')),
                    'status': data.get('status', 'pending'),
                    'raw_response': data,
                }
            else:
                error_msg = response.text
                _logger.error(
                    'MP authorize failed: order %s error %s',
                    order.name, error_msg,
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                'MP authorize exception: order %s error %s',
                order.name, error_msg,
            )
            return {
                'success': False,
                'error': error_msg,
            }

    def capture_payment(self, mp_payment_id):
        """
        Captura un pago previamente autorizado.

        Args:
            mp_payment_id: ID del payment en MP (del response de authorize)

        Returns:
            dict con respuesta de MP o error
        """
        try:
            payload = {}

            url = f'{self.api_url}/v1/advanced_payments/{mp_payment_id}/capture'
            response = requests.put(
                url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code in (200, 201):
                data = response.json()
                _logger.info(
                    'MP capture success: mp_id %s status %s',
                    mp_payment_id, data.get('status'),
                )
                return {
                    'success': True,
                    'status': data.get('status', 'processing'),
                    'raw_response': data,
                }
            else:
                error_msg = response.text
                _logger.error(
                    'MP capture failed: mp_id %s error %s',
                    mp_payment_id, error_msg,
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                'MP capture exception: mp_id %s error %s',
                mp_payment_id, error_msg,
            )
            return {
                'success': False,
                'error': error_msg,
            }

    def cancel_payment(self, mp_payment_id):
        """
        Cancela un pago previamente autorizado.

        Args:
            mp_payment_id: ID del payment en MP

        Returns:
            dict con respuesta de MP o error
        """
        try:
            payload = {'status': 'cancelled'}

            url = f'{self.api_url}/v1/advanced_payments/{mp_payment_id}'
            response = requests.put(
                url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code in (200, 201):
                data = response.json()
                _logger.info(
                    'MP cancel success: mp_id %s status %s',
                    mp_payment_id, data.get('status'),
                )
                return {
                    'success': True,
                    'status': data.get('status', 'cancelled'),
                    'raw_response': data,
                }
            else:
                error_msg = response.text
                _logger.error(
                    'MP cancel failed: mp_id %s error %s',
                    mp_payment_id, error_msg,
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                'MP cancel exception: mp_id %s error %s',
                mp_payment_id, error_msg,
            )
            return {
                'success': False,
                'error': error_msg,
            }

    def get_payment_status(self, mp_payment_id):
        """
        Obtiene el estado actual de un pago.

        Args:
            mp_payment_id: ID del payment en MP

        Returns:
            dict con status del pago
        """
        try:
            url = f'{self.api_url}/v1/advanced_payments/{mp_payment_id}'
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                _logger.info(
                    'MP status check: mp_id %s status %s',
                    mp_payment_id, data.get('status'),
                )
                return {
                    'success': True,
                    'status': data.get('status', 'unknown'),
                    'raw_response': data,
                }
            else:
                error_msg = response.text
                _logger.error(
                    'MP status check failed: mp_id %s error %s',
                    mp_payment_id, error_msg,
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                'MP status check exception: mp_id %s error %s',
                mp_payment_id, error_msg,
            )
            return {
                'success': False,
                'error': error_msg,
            }
