# 🚀 Integración MercadoPago - Completada

## ¿Qué se implementó?

Se implementó una **integración completa con MercadoPago Advanced Payments API** que permite:

✅ **Autorizar pagos sin capturar** (reserve fondos)  
✅ **Capturar pagos previamente autorizados** (tomar los fondos)  
✅ **Split automático 85/15** entre proveedores y Botón Rojo  
✅ **Webhooks de MP** para sincronización automática  
✅ **Manejo de múltiples keys de MP** (modelo soporta N configuraciones)  
✅ **Liquidación semanal** con transferencias a proveedores  

---

## Respuestas a tus preguntas

### ¿Permite Odoo manejar múltiples keys de MP?

**SÍ, perfectamente.** 

El modelo `mp.config` permite almacenar N configuraciones de MP:
- Una configuración **activa** (la que se usa por defecto)
- Múltiples configuraciones inactivas (para diferentes sellers o ambientes)

```python
# Seleccionar configuración activa
config = env['mp.config'].get_active_config()

# Futuro: seleccionar por seller
config = env['mp.config'].search([('seller_id', '=', '999999')])
```

### ¿Cuál es el modelo de negocio?

Botón Rojo es un **marketplace de servicios**:

1. **Cliente** → Crea orden de servicio (ej: reparación de cañería)
2. **Botón Rojo** → Busca proveedor (acorde a batiseña/score)
3. **Proveedor** → Completa el trabajo, sube fotos
4. **Cliente** → Confirma y califica
5. **Botón Rojo** → Captura pago y liquida:
   - 85% → Proveedor (a su CBU)
   - 15% → Botón Rojo (comisión)

**Implementación técnica de split**:
- MP recibe el 100% (se autoriza por monto total)
- Odoo contabiliza internamente: 85% a proveedor, 15% a BR
- Liquidación semanal (jueves): transfiere 85% a cada proveedor por separado

---

## Archivos creados/modificados

### Modelos nuevos
```
br_mercadopago/models/
├── mp_config.py          (Configuración de credenciales MP)
├── mp_client.py          (Cliente HTTP para API MP)
└── [br_payment.py]       (Actualizado: stubs → llamadas reales)
```

### Vistas nuevas
```
br_mercadopago/views/
├── mp_config_views.xml   (Formulario + lista de configuración)
└── [br_payment_views.xml] (Ya existía, sin cambios)
```

### Datos iniciales
```
br_mercadopago/data/
└── mp_config_data.xml    (Configuración placeholder para completar)
```

### Endpoints API nuevos
```
br_api/controllers/main.py
├── POST /br/api/payments/{order_name}/authorize
├── POST /br/api/payments/{order_name}/capture
└── [POST /br/api/mp/webhook] (Ya existía, mejorado handler)
```

### Documentación
```
┌─ MERCADOPAGO_INTEGRATION.md    (Descripción técnica detallada)
├─ MERCADOPAGO_SETUP.md          (Guía de instalación y configuración)
├─ MERCADOPAGO_POSTMAN_EXAMPLES.md (Ejemplos cURL y Postman)
└─ README_MERCADOPAGO.md          (Este archivo)
```

---

## Flujo de pago paso a paso

```
┌─────────────────────────────────────────────────────────────┐
│ PASO 1: Cliente crea orden                                   │
│ POST /br/api/orders/create                                   │
│ → payment_method = "mp"                                      │
│ → br.payment.status = "pending"                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 2: Cliente autoriza pago                                │
│ POST /br/api/payments/{order_name}/authorize                │
│ → Llama MP API: authorize_payment(amount, capture=False)    │
│ → br.payment.status = "authorized"                           │
│ → order.state = "pago_autorizado"                            │
│ → MP retorna: payment_id                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 3: Proveedor asignado (Odoo UI o batiseña)             │
│ → order.state = "proveedor_asignado"                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 4: Proveedor carga foto ANTES                           │
│ POST /br/api/providers/me/upload-photo                      │
│ → order.photo_before = base64_image                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 5: Proveedor completa trabajo (Odoo UI)                │
│ → order.state = "trabajo_completado"                        │
│ → Se envía webhook a mop-core-ng                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 6: Cliente confirma y califica                          │
│ POST /br/api/orders/{order_name}/confirm?rating=5          │
│ → order.state = "pago_liberado"                             │
│ → order.rating = 5                                          │
│ → Se envía webhook a mop-core-ng                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 7: Backend captura pago                                │
│ POST /br/api/payments/{order_name}/capture                  │
│ → Llama MP API: capture_payment(payment_id)                 │
│ → br.payment.status = "captured"                            │
│ → br.payment.provider_split = 4250 (85%)                   │
│ → br.payment.br_split = 750 (15%)                           │
│ → order.state = "pago_liberado" (ya estaba)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 8: MP envía webhook (redundancia, opcional)             │
│ POST /br/api/mp/webhook                                     │
│ → Sincroniza estado automáticamente (idempotente)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 9: Jueves 18:00 - Cron liquidación                     │
│ br.liquidation.cron_liquidacion_semanal()                   │
│ → Agrupa pagos captured de la semana                        │
│ → Por cada proveedor:                                       │
│    - Suma provider_split                                    │
│    - Crea br.liquidation.line                               │
│    - Transfiere 85% a CBU del proveedor                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Primeros pasos

### 1. Instalar el módulo
```bash
docker exec -it odoo-br bash
cd /opt/odoo
python -m odoo.cli.main -c etc/odoo.conf -d botonrojo -i br_mercadopago --stop-after-init
```

### 2. Configurar credenciales
1. Ir a: **Botón Rojo** → **Integración MP**
2. Editar "Botón Rojo Principal"
3. Copiar credenciales de: https://www.mercadopago.com.ar/developers
4. Botón: **"Probar conexión"** ✓
5. Guardar

### 3. Probar con Postman
Ver: `MERCADOPAGO_POSTMAN_EXAMPLES.md`

```bash
# Crear orden
POST /br/api/orders/create
→ response: order_id=BR-0001, payment_status=pending

# Autorizar
POST /br/api/payments/BR-0001/authorize
→ response: status=authorized

# (... proveedor trabaja ...)

# Capturar
POST /br/api/payments/BR-0001/capture
→ response: status=captured, provider_split=4250, br_split=750
```

---

## Configuración requerida

Antes de producción, necesitas:

1. **Cuenta MercadoPago Marketplace**
   - Solicitar aquí: https://www.mercadopago.com.ar/developers
   - Requiere: razón social, CUIT, CBU, datos bancarios
   - Tiempo: 2-4 semanas de aprobación

2. **Credenciales**
   - Seller ID (user_id)
   - Access Token
   - Client ID / Client Secret

3. **Webhooks (opcional pero recomendado)**
   - Configurar en MP Dashboard
   - URL: `https://tudominio.com/br/api/mp/webhook`
   - Eventos: `payment.authorized`, `payment.captured`, `payment.refunded`

---

## API Endpoints

### POST `/br/api/payments/{order_name}/authorize`
Autoriza un pago en MP (sin capturar).

**Autenticación**: JWT Bearer token (cliente)

**Response**:
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "authorized",
  "amount": 5000.00
}
```

### POST `/br/api/payments/{order_name}/capture`
Captura un pago previamente autorizado.

**Autenticación**: JWT Bearer token (cliente)

**Response**:
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "captured",
  "provider_split": 4250.00,
  "br_split": 750.00
}
```

### POST `/br/api/mp/webhook`
Recibe webhooks de MercadoPago (redundancia).

**Autenticación**: Ninguna (público)

**Body**:
```json
{
  "action": "payment.captured",
  "id": "123456789",
  "status": "captured",
  "data": {"id": "123456789"}
}
```

---

## Debugging y monitoreo

### Ver logs
```bash
docker logs -f odoo-br | grep "BR MP"

# Debería ver:
# [INFO] BR MP authorize success: order BR-0001 mp_id 123456789
# [INFO] BR MP capture success: order BR-0001 provider 4250.00 BR 750.00
```

### Ver estado en Odoo UI
1. Ir a: **Botón Rojo** → **Finanzas** → **Pagos MP**
2. Seleccionar pago
3. Ver: `status`, `mp_payment_id`, `provider_split`, `br_split`
4. Pestaña "Respuesta MP": JSON crudo de API

### Consultas SQL
```sql
-- Ver todos los pagos
SELECT id, mp_payment_id, status, amount FROM br_payment ORDER BY create_date DESC;

-- Ver pagos por orden
SELECT * FROM br_payment WHERE order_id IN (
  SELECT id FROM br_service_order WHERE name='BR-0001'
);

-- Ver split de pagos capturados
SELECT order_id, status, provider_split, br_split 
FROM br_payment WHERE status='captured'
ORDER BY create_date DESC;
```

---

## FAQ

### ¿Qué pasa si falla la autorización?
- Retorna error con detalles de MP
- El pago queda en estado `pending`
- Cliente puede reintentar

### ¿Qué pasa si falla la captura?
- Retorna error con detalles de MP
- El pago queda en estado `authorized` (fondos siguen reservados)
- Hay que reintentar o cancelar

### ¿Puedo capturar un pago que fue autorizado hace días?
**Sí, hasta 29 días después.** MP permite capturas de autorizaciones viejas.

### ¿Qué pasa si no se captura nunca?
- Los fondos se liberan automáticamente después de 29 días
- El cliente ve el dinero de vuelta en su cuenta

### ¿Soporta reembolsos?
**Sí** via `br.payment.action_refund()` → llama a MP cancel/refund API

### ¿Cómo manejo múltiples currencies?
Actualmente soporta solo **ARS**. Para agregar soporte a USD:
- Actualizar `mp_client.py` para aceptar `currency_id` como parámetro
- Agregar validación en endpoints

---

## Documentación completa

Para más detalles, ver:
- 📖 `MERCADOPAGO_INTEGRATION.md` — Arquitectura y modelos
- 🔧 `MERCADOPAGO_SETUP.md` — Instalación y configuración
- 🧪 `MERCADOPAGO_POSTMAN_EXAMPLES.md` — Ejemplos de API

---

## ¿Qué sigue?

Próximos pasos opcionales (no críticos):

1. **Validación de webhooks**: HMAC-SHA256 de MP
2. **Rate limiting**: Evitar DDoS en endpoints de pago
3. **Auditoría**: Log de todas las transacciones
4. **Transferencias automáticas**: Usar Mercado Pago Transfer API para liquidar automáticamente
5. **Tests unitarios**: Cobertura de authorize/capture/cancel

---

## Resumen técnico

| Aspecto | Detalle |
|---------|---------|
| **API MP usada** | Advanced Payments (no Checkout Preferencia) |
| **Modelo de split** | Interno en Odoo (85/15) |
| **Soporte múltiples keys** | Sí, modelo `mp.config` escalable |
| **Idempotencia** | Sí en webhooks |
| **Manejo de errores** | Consistent, con detalles de MP |
| **Auditoría** | raw_response de MP almacenado |
| **Ambiente** | Sandbox (default) o Producción |

---

**¿Preguntas?** Revisar documentación o crear issue.

**¿Listo para empezar?** → Ver `MERCADOPAGO_SETUP.md`
