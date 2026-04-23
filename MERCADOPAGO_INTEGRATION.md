# Integración MercadoPago - Implementación Completada

## Resumen de cambios

Se implementó la integración completa con **MercadoPago Advanced Payments API** para manejar autorización y captura de pagos con split 85/15 entre proveedores y Botón Rojo.

## Nuevos modelos creados

### 1. `mp.config` - Configuración de MercadoPago
**Archivo**: `br_mercadopago/models/mp_config.py`

Almacena las credenciales y configuración de MP:
- `seller_id`: ID de vendedor en MP
- `access_token`: Token de acceso a API MP
- `client_id` / `client_secret`: Credenciales OAuth
- `api_url`: URL base de API (producción o sandbox)
- `webhook_token`: Token para validar webhooks
- `is_active`: Marcador de configuración activa
- `is_production`: Ambiente de producción vs. sandbox
- `br_commission_percentage`: % comisión BR (default 15%)
- `provider_percentage`: % para proveedores (default 85%)
- Método: `test_connection()` para validar credenciales

### 2. `MercadoPagoClient` - Cliente HTTP para API MP
**Archivo**: `br_mercadopago/models/mp_client.py`

Encapsula todas las llamadas HTTP a la API de MP:
- `authorize_payment()`: Autoriza sin capturar (capture=False)
- `capture_payment()`: Captura un pago autorizado
- `cancel_payment()`: Cancela un autorizado
- `get_payment_status()`: Consulta estado actual

Todas las operaciones retornan un diccionario con formato consistente:
```python
{
    'success': True/False,
    'mp_id': '123456',
    'status': 'authorized|captured|cancelled|...',
    'raw_response': {...}  # respuesta cruda de MP
}
```

## Cambios a modelos existentes

### 3. `br.payment` - Modelo de pagos (actualizado)
**Archivo**: `br_mercadopago/models/br_payment.py`

- **Métodos actualizados** (ya no son stubs, ahora usan cliente real MP):
  - `action_authorize()`: Llama a `MercadoPagoClient.authorize_payment()`
  - `action_capture()`: Llama a `MercadoPagoClient.capture_payment()`
  - `action_cancel()`: Llama a `MercadoPagoClient.cancel_payment()`

- **Webhook handler mejorado** `process_mp_webhook()`:
  - Maneja eventos de MP: `payment.authorized`, `payment.captured`, `payment.cancelled`, `payment.refunded`
  - Sincroniza automáticamente estado del pago con orden
  - Idempotente: ejecutar 2 veces el mismo webhook no causa problemas

Estados del pago:
- `pending` → `authorized` → `captured` → liquidación
- `pending/authorized` → `cancelled` (si se cancela)
- `captured` → `refunded` (si se reembolsa)

## Nuevos endpoints en br_api

**Archivo**: `br_api/controllers/main.py`

### POST `/br/api/payments/<order_name>/authorize`
Autoriza un pago en MP sin capturarlo.

**Request**:
```bash
curl -X POST http://localhost:8069/br/api/payments/BR-0001/authorize \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json"
```

**Response** (200):
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "authorized",
  "amount": 5000.00
}
```

### POST `/br/api/payments/<order_name>/capture`
Captura un pago previamente autorizado.

**Request**:
```bash
curl -X POST http://localhost:8069/br/api/payments/BR-0001/capture \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json"
```

**Response** (200):
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "captured",
  "provider_split": 4250.00,
  "br_split": 750.00
}
```

### POST `/br/api/mp/webhook` (ya existía, mejorado)
Recibe webhooks de MercadoPago.

**Eventos soportados**:
- `payment.authorized` - Pago fue autorizado
- `payment.captured` - Pago fue capturado
- `payment.cancelled` - Pago fue cancelado
- `payment.refunded` - Pago fue reembolsado

## Flujo de pago completo

```
1. Cliente crea orden
   POST /br/api/orders/create
   → response: { "payment_status": "pending", "monto_autorizar": 5000 }

2. Cliente autoriza pago en MP
   POST /br/api/payments/BR-0001/authorize
   → MP retorna payment_id
   → br.payment.status = "authorized"
   → order.state = "pago_autorizado"

3. Proveedor completa trabajo y sube foto
   POST /br/api/providers/me/upload-photo
   → order.state = "trabajo_completado"

4. Cliente confirma y califica
   POST /br/api/orders/BR-0001/confirm
   → order.state = "pago_liberado"

5. Backend captura el pago
   POST /br/api/payments/BR-0001/capture
   → MP retorna status = "captured"
   → br.payment.status = "captured"
   → Split: 85% a proveedor, 15% a BR

6. MP envía webhook de confirmación (opcional, para redundancia)
   POST /br/api/mp/webhook
   → Sincroniza estado (idempotente)

7. Jueves 18:00 - Cron de liquidación semanal
   → Agrupa órdenes en estado "pago_liberado" de la semana
   → Crea br.liquidation con líneas por proveedor
   → Calcula: monto_proveedor = sum(payment.provider_split)
   → Transfiere 85% a CBU de cada proveedor
```

## Configuración requerida

1. **Crear cuenta MercadoPago Marketplace**
   - Solicitud en: https://www.mercadopago.com/developers
   - Requiere: Razón social, CUIT, CBU, datos bancarios
   - Tiempo de aprobación: 2-4 semanas
   - Obtener: seller_id (user_id), access_token, client_id, client_secret

2. **Configurar en Odoo**
   - Ir a: Botón Rojo → Integración MP
   - Crear registro con credenciales
   - Botón: "Probar conexión" valida que los tokens sean válidos
   - Activar: `is_active = True`
   - Ambiente: `is_production = False` para sandbox

3. **Configurar Webhooks en MP**
   - URL de webhook (pública): `https://tudominio.com/br/api/mp/webhook`
   - Eventos: `payment.authorized`, `payment.captured`, `payment.refunded`
   - Nota: Los webhooks son opcionales (redundancia), el sistema funciona sin ellos

## Observaciones técnicas

### ¿Cómo maneja Odoo múltiples keys de MP?

**Sí, perfectamente**. El modelo `mp.config` permite almacenar múltiples configuraciones:

```python
# Para seleccionar la configuración activa:
config = env['mp.config'].get_active_config()  # Retorna la con is_active=True

# Para marketplace con múltiples sellers (futuro):
# Cada seller podría tener su propia configuración
# selector = env['mp.config'].search([('seller_id', '=', seller_id)])
```

### Split de pagos (85/15)

Se realiza **enteramente en Odoo**, no en la API de MP:

```python
# En br.payment:
@api.depends('order_id.amount')
def _compute_splits(self):
    for rec in self:
        rec.provider_split = round((rec.order_id.amount or 0.0) * 0.85, 2)
        rec.br_split = round((rec.order_id.amount or 0.0) * 0.15, 2)

# En br.liquidation (semanal):
# Se suman los provider_split y se transfieren a CBU de cada proveedor
```

### ¿Por qué authorize sin capture?

Para soportar el flujo de BotonRojo:
1. **Autorizar**: Cliente confirma el pago (se reservan fondos en MP)
2. **Proveedor trabaja**: Realiza el servicio, sube fotos
3. **Capturar**: Solo cuando el cliente confirma que trabajó bien

Si se capturara inmediatamente, no habría forma de hacer un chargeback si el proveedor falla.

## Manejo de errores

Todos los endpoints retornan errores consistentes:

```json
{
  "error": "Descripción del error"
}
```

Con HTTP status apropiad (400, 401, 404, 500).

El modelo `mp.config` almacena `last_error` y `last_success` para auditoría.

## Próximos pasos (opcionales)

1. **Integraciones avanzadas de MP**:
   - Refunds automáticos en disputas
   - Webhooks de pago (ya soportado, pero opcional)
   - Transferencias de comisión a BR automáticas

2. **Liquidación mejorada**:
   - Integración con transferencias bancarias automáticas via Mercado Pago Transfer API
   - Reporte de liquidación con comprobante de transferencia

3. **Validaciones de seguridad**:
   - Validación de firma en webhooks (HMAC-SHA256)
   - Rate limiting en endpoints de pago
   - Auditoría de todas las transacciones
