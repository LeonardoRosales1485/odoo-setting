# Ejemplos cURL y Postman - Integración MercadoPago

## Variables globales (configurar en Postman)

```
Environment Variables:
- {{base_url}} = http://localhost:8069
- {{client_token}} = <JWT token válido del cliente>
- {{workspace_key}} = <X-BR-API-Key válida>
- {{order_id}} = BR-0001 (después de crear la orden)
```

---

## 1. Crear orden con método de pago MP

### cURL
```bash
curl -X POST http://localhost:8069/br/api/orders/create \
  -H "Authorization: Bearer <client_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rubro": "plomero",
    "descripcion": "Reparación de cañería en cocina",
    "fecha": "2026-04-25",
    "franja": "manana",
    "payment_method": "mp",
    "amount": 5000.00
  }'
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/orders/create`

**Headers**:
```
Authorization: Bearer {{client_token}}
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "rubro": "plomero",
  "descripcion": "Reparación de cañería en cocina",
  "fecha": "2026-04-25",
  "franja": "manana",
  "payment_method": "mp",
  "amount": 5000.00
}
```

**Response esperada** (201):
```json
{
  "order_id": "BR-0001",
  "state": "solicitud_creada",
  "payment_method": "mp",
  "payment_status": "pending",
  "monto_autorizar": 5000.00,
  "mp_payment_link": null
}
```

---

## 2. Autorizar pago en MercadoPago

**Lo que hace**: Autoriza el pago SIN capturarlo (reserva fondos)

### cURL
```bash
curl -X POST http://localhost:8069/br/api/payments/BR-0001/authorize \
  -H "Authorization: Bearer <client_token>" \
  -H "Content-Type: application/json"
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/payments/{{order_id}}/authorize`

**Headers**:
```
Authorization: Bearer {{client_token}}
Content-Type: application/json
```

**Body**: (vacío)

**Response esperada** (200):
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "authorized",
  "amount": 5000.00
}
```

**¿Qué cambió en Odoo?**
- `br.payment.status`: pending → **authorized**
- `br.payment.mp_payment_id`: null → **123456789**
- `br.service.order.state`: solicitud_creada → **pago_autorizado**

---

## 3. Consultar estado de orden

### cURL
```bash
curl -X GET http://localhost:8069/br/api/orders/BR-0001/status \
  -H "Authorization: Bearer <client_token>" \
  -H "Content-Type: application/json"
```

### Postman

**Method**: GET  
**URL**: `{{base_url}}/br/api/orders/{{order_id}}/status`

**Headers**:
```
Authorization: Bearer {{client_token}}
Content-Type: application/json
```

**Response esperada** (200):
```json
{
  "order_id": "BR-0001",
  "state": "pago_autorizado",
  "rubro": "plomero",
  "amount": 5000.00,
  "payment_method": "mp",
  "provider": null
}
```

---

## 4. Asignar proveedor (desde UI o backend)

**Via UI Odoo**:
1. Ir a: Órdenes de Servicio
2. Abrir orden BR-0001
3. Botón: "Asignar proveedor" → Seleccionar proveedor
4. Guardar

**Via API** (si existe endpoint):
```bash
curl -X POST http://localhost:8069/br/api/orders/BR-0001/assign-provider \
  -H "Authorization: Bearer <workspace_key>" \
  -H "Content-Type: application/json" \
  -d '{"provider_id": 15}'
```

---

## 5. Proveedor sube foto ANTES (foto_before)

### cURL
```bash
# 1. Convertir foto a base64
# Linux/Mac: cat foto.jpg | base64
# Windows: certutil -encode foto.jpg foto.b64

curl -X POST http://localhost:8069/br/api/providers/me/upload-photo \
  -H "Authorization: Bearer <provider_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "photo_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
  }'
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/providers/me/upload-photo`

**Headers**:
```
Authorization: Bearer {{provider_token}}
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "photo_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
}
```

**Para obtener base64 de una foto real**:

**En Postman**:
1. Pre-request Script (tab):
```javascript
const fs = require('fs');
const path = require('path');
const photoPath = '/path/to/photo.jpg';
const base64 = fs.readFileSync(photoPath, 'base64');
pm.environment.set('photo_base64', base64);
```

2. Body:
```json
{
  "photo_base64": "{{photo_base64}}"
}
```

**Response esperada** (200):
```json
{
  "order_id": "BR-0001",
  "photo_uploaded": true
}
```

---

## 6. Proveedor completa trabajo

**Via UI Odoo**:
1. Ir a: Órdenes de Servicio
2. Abrir orden BR-0001
3. Botón: "Trabajo completado" (si la foto ANTES existe)
4. Guardar

**¿Qué pasa?**
- `br.service.order.state`: proveedor_asignado → **trabajo_completado**
- Webhook enviado a mop-core-ng: `{ "event": "work_done", "order_id": "BR-0001" }`

---

## 7. Cliente confirma y califica

### cURL
```bash
curl -X POST http://localhost:8069/br/api/orders/BR-0001/confirm \
  -H "Authorization: Bearer <client_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": "5"
  }'
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/orders/{{order_id}}/confirm`

**Headers**:
```
Authorization: Bearer {{client_token}}
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "rating": "5"
}
```

**Response esperada** (200):
```json
{
  "order_id": "BR-0001",
  "state": "pago_liberado",
  "rating": "5"
}
```

**¿Qué cambió?**
- `br.service.order.state`: trabajo_completado → **pago_liberado**
- `br.service.order.rating`: null → **5**
- Webhook: `{ "event": "payment_released", "order_id": "BR-0001" }`

---

## 8. Capturar pago en MercadoPago

**Lo que hace**: Captura el pago previamente autorizado (toma los fondos)

### cURL
```bash
curl -X POST http://localhost:8069/br/api/payments/BR-0001/capture \
  -H "Authorization: Bearer <client_token>" \
  -H "Content-Type: application/json"
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/payments/{{order_id}}/capture`

**Headers**:
```
Authorization: Bearer {{client_token}}
Content-Type: application/json
```

**Body**: (vacío)

**Response esperada** (200):
```json
{
  "order_id": "BR-0001",
  "payment_id": "123456789",
  "status": "captured",
  "provider_split": 4250.00,
  "br_split": 750.00
}
```

**¿Qué cambió?**
- `br.payment.status`: authorized → **captured**
- `br.payment.provider_split`: 0 → **4250.00** (85%)
- `br.payment.br_split`: 0 → **750.00** (15%)
- Split se calcula automáticamente

---

## 9. Webhook de MercadoPago (simulado)

**Lo que hace**: MercadoPago envía confirmación de captura (optional, para redundancia)

### cURL
```bash
curl -X POST http://localhost:8069/br/api/mp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": "123456789",
    "action": "payment.captured",
    "status": "captured",
    "data": {
      "id": "123456789"
    }
  }'
```

### Postman

**Method**: POST  
**URL**: `{{base_url}}/br/api/mp/webhook`

**Headers**:
```
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "id": "123456789",
  "action": "payment.captured",
  "status": "captured",
  "data": {
    "id": "123456789"
  }
}
```

**Response esperada** (200):
```json
{
  "ok": true
}
```

**Nota**: Este webhook es redundante si el capture se hizo vía endpoint. Útil si:
- El capture falló pero MP lo hizo de todas formas
- Sincronización desde otro sistema

---

## 10. Verificar pagos en Odoo (UI)

1. Ir a: **Botón Rojo** → **Finanzas** → **Pagos MP**
2. Ver listado de todos los pagos:
   - Order ID
   - Method (mp/efectivo)
   - Amount
   - Status (pending / authorized / captured / etc.)
   - MP Payment ID
   - Provider split (85%)
   - BR split (15%)

---

## 11. Liquidación semanal (automática jueves 18:00)

**Qué ocurre**:
- Cron task se ejecuta automáticamente
- Agrupa todos los pagos captured de la semana
- Por cada proveedor:
  - Suma: provider_split de todas sus órdenes
  - Crea línea en br.liquidation
  - Transfiere 85% al CBU del proveedor

**Para ver liquidaciones**:
1. Ir a: **Botón Rojo** → **Finanzas** → **Liquidaciones** (si existe menú)
2. O acceder vía base de datos:

```sql
SELECT 
  l.name,
  l.fecha,
  COUNT(DISTINCT ll.proveedor_id) as cantidad_proveedores,
  SUM(ll.monto_proveedor) as total_a_pagar,
  l.estado
FROM br_liquidation l
LEFT JOIN br_liquidation_line ll ON ll.liquidacion_id = l.id
GROUP BY l.id
ORDER BY l.fecha DESC;
```

---

## 12. Flujo completo (testing)

**Time**: ~5 minutos por orden

1. **[Cliente]** Crear orden → `BR-0001` (step 1)
2. **[Sistema]** Pago creado en estado "pending"
3. **[Cliente]** Autorizar → `POST /payments/BR-0001/authorize` (step 2)
4. **[Odoo UI]** Asignar proveedor a la orden (step 4)
5. **[Proveedor]** Subir foto ANTES → `POST /upload-photo` (step 5)
6. **[Odoo UI]** Marcar trabajo completado (step 6)
7. **[Cliente]** Confirmar → `POST /orders/BR-0001/confirm` (step 7)
8. **[Sistema]** Capturar pago → `POST /payments/BR-0001/capture` (step 8)
9. **[Sistema]** Verificar: split 85/15 (step 10)
10. **[Jueves 18:00]** Liquidación automática (step 11)

---

## Errores comunes

### 401 - No autorizado
```json
{"error": "No autorizado"}
```
**Causa**: Token inválido o expirado  
**Solución**: Verificar `Authorization: Bearer {{client_token}}`

### 404 - Orden no encontrada
```json
{"error": "Orden no encontrada"}
```
**Causa**: Order ID no existe en BD  
**Solución**: Verificar que la orden fue creada exitosamente

### 400 - No hay pago pendiente
```json
{"error": "No hay pago pendiente para autorizar"}
```
**Causa**: El pago ya fue autorizado o no existe  
**Solución**: Ejecutar step 1 primero para crear orden

### 400 - Error al autorizar pago
```json
{"error": "Error al autorizar pago: Invalid credentials"}
```
**Causa**: Credenciales MP inválidas  
**Solución**: Verificar en Odoo → Integración MP → "Probar conexión"

---

## Notas de testing

1. **Sandbox vs Producción**: Los tokens de sandbox son diferentes a producción
2. **Moneda**: Todos los montos en ARS (Pesos argentinos)
3. **Precisión**: Máximo 2 decimales (5000.00, no 5000.001)
4. **Idempotencia**: Ejecutar webhook 2 veces no causa problemas
5. **Logs**: Ver `docker logs odoo-br | grep "BR MP"`
