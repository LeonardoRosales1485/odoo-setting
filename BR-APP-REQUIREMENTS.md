# Qué necesitamos de la App de Botón Rojo

## 🔌 Integración API

### 1. **Endpoint Webhook (Crítico)**
Tu app debe proveer una URL que reciba `POST` requests cuando el estado de una orden cambia.

```
POST {tu_webhook_url}

Body:
{
  "event": "provider_assigned",
  "order_id": "BR-0042",
  "state": "proveedor_asignado",
  "data": {
    "provider_name": "Juan M.",
    "provider_score": 4.8,
    "provider_photo": "https://...",
    "eta_minutes": 25
  }
}
```

**Eventos que recibirás:**
- `order_queued` — orden en cola, buscando proveedor
- `provider_assigned` — proveedor asignado + ETA
- `provider_arrived` — proveedor llegó
- `work_done` — trabajo terminado
- `payment_released` — pago liberado al proveedor
- `dispute_opened` — cliente abrió reclamo
- `dispute_resolved` — reclamo resuelto

**Responsabilidad de tu app:** Actualizar UI del cliente/proveedor en tiempo real al recibir estos eventos.

---

## 🔐 Autenticación de Usuarios

### 2. **Flujo OTP (Crítico)**
Tu app debe poder:
1. Capturar teléfono del usuario (cliente o proveedor)
2. Enviar OTP vía SMS o WhatsApp
3. Recibir el token JWT que devolvemos

**Opciones:**
- **Opción A:** Tu app envía el SMS/WA y nos pasas el OTP para validar
- **Opción B:** Nosotros enviamos el OTP (necesitas proveedor de SMS: Twilio, AWS SNS, etc.)
- **Opción C:** Nosotros enviamos vía WhatsApp Business (mop-core-ng integrado)

**Recomendación:** Opción C (WhatsApp) — sin costo de SMS, experiencia nativa

---

## 💰 Configuración de Precios

### 3. **Tabla de Precios por Rubro (Crítico)**
Define para cada rubro:

```json
{
  "rubro_id": "plomeria",
  "rubro_nombre": "Plomería",
  "precio_base": 3500,
  "diagnostico_incluido": true,
  "precio_diagnostico": 1500,
  "preguntas_intake": [
    "¿Qué tipo de servicio necesitás?",
    "¿Cuándo lo necesitás?",
    "¿En qué franja horaria?"
  ]
}
```

**Rubros necesarios para piloto:** Mínimo 8 (plomería, electricista, pintor, cerrajero, gasista, climatización, albañil, refrigeración)

---

## 📝 Información de Usuarios

### 4. **Datos de Proveedores (Crítico)**
Para cada proveedor, proporciona:
- Nombre completo
- Número de WhatsApp/teléfono
- DNI / Documento identidad
- Rubros que cubre (multiples)
- Foto de perfil
- Cuenta bancaria (CBU/alias Mercado Pago)
- Seguros (responsabilidad civil)

---

## 🏦 Integración con MercadoPago

### 5. **Cuenta Marketplace (MÁS CRÍTICO AÚN)**
Botón Rojo debe:
1. Solicitar cuenta **MercadoPago Marketplace** (no solo Payment Gateway)
2. Proporcionar las credenciales:
   - **Client ID**
   - **Client Secret**
   - **Access Token**
   - **Seller ID** (ID del vendedor = Botón Rojo)

**Por qué:** Necesitamos hacer split automático 85% al proveedor / 15% a BR.

**Plazo:** Esto tarda 2-4 semanas en aprobarse. **Iniciar HOY.**

---

## 📊 Información Fiscal

### 6. **Modelo Fiscal AFIP**
Botón Rojo es:
- ¿Monotributista?
- ¿IVA Responsable?
- ¿Registrado en Ingresos Brutos?

**Nº de CUIT:** _______________

Esto afecta los journales contables y cómo liquidamos.

---

## 📍 Operativa / Logística

### 7. **Zonas de Cobertura**
Define zonas de servicio (ej: Nordelta = zona 1, La Barra = zona 2, etc.)
- Necesitamos para: asignar proveedores por zona, mapas, ETAs
- Formato: GeoJSON o lista de direcciones base

### 8. **Horarios de Servicio**
- ¿Qué horarios opera Botón Rojo? (ej: 7am-10pm, L-D)
- ¿Hay horarios especiales por rubro?
- ¿Servicios de emergencia 24h?

---

## 🔄 Procesos de Negocio

### 9. **Políticas de Cancelación**
- ¿Puede el cliente cancelar antes de pagar?
- ¿Puede cancelar después de pagar?
- ¿Hay penalización si cancela cerca de la fecha?
- ¿Reembolso automático o manual?

### 10. **Escala de Calificaciones**
- ¿Escala 1-5 estrellas?
- ¿Qué criterios (velocidad, calidad, precio)?
- ¿Visible públicamente o privado?
- ¿Afecta al score del proveedor automáticamente?

### 11. **Política de Disputas**
- ¿Cliente puede reclamar dentro de cuántos días post-trabajo?
- ¿Quién resuelve? (ops, curador externo, arbitraje)
- ¿Reembolso automático o revisión?
- ¿Cliente puede calificar negativo y después reclamar?

---

## 🎯 Checklist: Qué debemos recibir ANTES de empezar

| # | Ítem | Formato | Deadline |
|---|---|---|---|
| 1 | URL webhook de producción | `https://app.botonrojo.com/webhooks/br` | Semana 1 |
| 2 | Tabla de precios (8 rubros) | JSON o CSV | Semana 1 |
| 3 | Preguntas intake por rubro | Texto o JSON | Semana 1 |
| 4 | Credenciales MercadoPago Marketplace | Client ID + Secret | **HOY** |
| 5 | CUIT + modelo fiscal AFIP | Texto | Semana 2 |
| 6 | Decisión: OTP vía SMS, WA, o nosotros | Selección | Semana 1 |
| 7 | Listado de proveedores piloto (mín 5) | CSV: nombre, WA, zona | Semana 1 |
| 8 | Zonas de cobertura | Descripciones o GeoJSON | Semana 1 |
| 9 | Políticas (cancelación, disputas, calificación) | Documento | Semana 2 |

---

## 💬 Soporte Técnico

### **Punto de contacto en Botón Rojo:**
- **Tech:** [Nombre] — integración webhook, credenciales MP
- **Ops:** [Nombre] — precios, rubros, políticas de negocio
- **Admin:** [Nombre] — cuentas bancarias de proveedores, AFIP

### **Punto de contacto en MoP Tech:**
- **Lead Dev:**  Mauri
- **Product:** Gas

---

## 🚀 Resumen

**Lo que entrega MoP Tech:**
- Backend REST API operativo con todos los endpoints
- Webhooks salientes (tiempo real)
- Panel admin completo
- Canal WhatsApp funcionando

**Lo que entrega Botón Rojo (obligatorio para que funcione):**
- URL webhook para recibir eventos
- Tabla de precios y rubros
- Credenciales MercadoPago Marketplace
- Datos de proveedores piloto
- Políticas de negocio (cancelación, disputas, calificación)
- Proveedor de OTP (SMS/WA) o nos dejan que usemos WA Business

**Sin estos datos, no podemos construir un MVP que funcione.**
