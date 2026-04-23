# Botón Rojo — Documento de Requerimientos y Entregables

> **Para:** Equipo Botón Rojo (owner de la app)
> **De:** MoP Tech
> **Versión:** Piloto Nordelta — 280h

---

## Resumen Ejecutivo

MoP Tech construye el **backend + API REST** que alimenta la app existente de Botón Rojo y el canal WhatsApp. La app consume nuestra API para el ciclo de vida completo de las órdenes: crear solicitudes, asignar proveedores, gestionar pagos y liquidar. Nosotros no tocamos la UI/UX de la app — eso es responsabilidad de Botón Rojo.

```
 App BR (clientes + proveedores)     WhatsApp (canal alternativo)
             │                              │
             └──────────────┬──────────────┘
                            ▼
                   API REST  ←  entregable MoP Tech
                            │
                    MercadoPago · WhatsApp Business
```

---

## Entregables de MoP Tech

### 1. API REST (`br_api`)
API documentada (OpenAPI / Swagger) con los siguientes grupos de endpoints:

**Autenticación**
| Endpoint | Descripción |
|---|---|
| `POST /br/api/auth/otp/request` | Solicita OTP al teléfono del usuario |
| `POST /br/api/auth/otp/verify` | Verifica OTP → devuelve token JWT + rol |
| `POST /br/api/auth/refresh` | Renueva token expirado |

**Órdenes (clientes autenticados)**
| Endpoint | Descripción |
|---|---|
| `POST /br/api/orders/create` | Crear solicitud de servicio |
| `GET /br/api/orders/{id}/status` | Estado actual + proveedor asignado + ETA |
| `GET /br/api/orders/history` | Historial de órdenes del cliente |
| `POST /br/api/orders/{id}/confirm` | Confirmar trabajo completado + calificación 1-5 |
| `POST /br/api/orders/{id}/dispute` | Abrir reclamo |

**Proveedores (proveedores autenticados)**
| Endpoint | Descripción |
|---|---|
| `GET /br/api/providers/me/queue` | Ver oferta activa (Batiseñal) |
| `POST /br/api/providers/me/accept` | Aceptar trabajo |
| `POST /br/api/providers/me/arrived` | Marcar "Llegué" + foto |
| `POST /br/api/providers/me/done` | Marcar trabajo terminado + foto |
| `GET /br/api/providers/me/history` | Historial de trabajos |
| `GET /br/api/providers/me/earnings` | Próxima liquidación estimada |

**Config**
| Endpoint | Descripción |
|---|---|
| `GET /br/api/config/rubros` | Rubros activos, precios y preguntas de intake |

### 2. Webhooks en tiempo real (Odoo → App BR)
Botón Rojo registra una URL en la configuración. Cuando el estado FSM de una orden cambia, nuestro backend hace `POST` a esa URL con:
```json
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

**Eventos disponibles:**
`order_queued` · `provider_assigned` · `provider_arrived` · `work_done` · `payment_released` · `dispute_opened` · `dispute_resolved`

### 3. Panel de Administración (Odoo)
- **Ops:** Kanban de órdenes activas por estado, cola Batiseñal en tiempo real, gestión de disputas
- **Finanzas:** Dashboard de liquidaciones semanales, deudas de efectivo, reembolsos
- **Proveedores:** Onboarding 4 pasos, score en tiempo real, suspensiones

### 4. Canal WhatsApp (mop-core-ng)
- Bot Voiceflow para intake guiado (rubro, fecha, franja, método de pago)
- Notificaciones automáticas de estado al cliente y al proveedor
- Timer Batiseñal de 60 segundos gestionado por el canal

---

## Requerimientos a Botón Rojo

> Estos ítems son **bloqueantes** para poder construir. Sin ellos no podemos avanzar.

### Críticos (deben estar antes de iniciar)

| # | Requerimiento | Para qué lo necesitamos | Responsable BR |
|---|---|---|---|
| R1 | **Cuenta MercadoPago Marketplace** aprobada | Split automático 85/15 proveedor/BR. Tarda 2-4 semanas en aprobarse. | CEO |
| R2 | **URL de webhook** de la app de BR | Enviar eventos FSM en tiempo real a la app | Tech BR |
| R3 | **Tabla de precios por rubro** (8 rubros mínimo) | Populate de `GET /config/rubros` y validación de presupuestos | CEO + Ops |
| R4 | **Preguntas de intake por rubro** | Bot Voiceflow + creación de órdenes con contexto | CEO + Ops |

### Altos (antes de Semana 3)

| # | Requerimiento | Para qué | Responsable BR |
|---|---|---|---|
| R5 | **Proveedor de OTP** (SMS o WhatsApp) | Login de usuarios en la app. Opciones: Twilio, AWS SNS, o MoP puede proveer vía WA Business | Tech BR |
| R6 | **Modelo fiscal AFIP** (monotributo vs IVA responsable) | Configuración journales contables l10n_ar | Jorge + Flor |
| R7 | **Cuentas bancarias de proveedores** para liquidación | Transferencias semanales desde Odoo | Ops BR |

### Medios (antes de Semana 5)

| # | Requerimiento | Para qué | Responsable BR |
|---|---|---|---|
| R8 | **Precios de referencia por diagnóstico** | Umbral 30% para curador en Flujo Con Diagnóstico | CEO + Ops |
| R9 | **Criterios de onboarding de proveedor** | Definir los 4 pasos del wizard (qué documentos, qué validaciones) | Ops BR |

---

## Lo que NO entregamos (fuera de scope del piloto)

| Ítem | Quién lo hace |
|---|---|
| UI/UX de la app cliente | Botón Rojo |
| UI/UX de la app proveedor | Botón Rojo |
| App móvil iOS/Android | Botón Rojo (o segunda fase) |
| Pago Fácil / Rapipago API | Fase 2 post-piloto |
| Anti-bypass con IA | Post-piloto |
| Portal cliente web (Next.js/Nuxt) | Post-piloto |

---

## Hitos y Timeline (~280h / 5.5 semanas)

| Semana | Hito | Qué puede probar BR |
|---|---|---|
| 1 | Infra + Odoo levantado | Panel Odoo accesible |
| 2-3 | **Flujo Directo E2E** | Crear orden por WhatsApp + ver estado en app |
| 3-4 | **Pagos reales** | Pagar con MP, proveedor recibe liquidación |
| 4-5 | **Proveedores + Score** | Onboarding, score dinámico, disputas |
| 5-6 | **Recurrentes + Efectivo** | Suscripción mensual + cobrador activo |

---


---

---
# Plan Técnico Interno (MoP Tech)

## Contexto

Botón Rojo es un marketplace de servicios para el hogar (piloto Nordelta). **mop-core-ng es el API layer**: recibe WhatsApp, guía al usuario por Voiceflow, y llama a `br_api` (módulo REST en Odoo 17 Community). Sin GHL.

Odoo 17 Community reemplaza todo el backend de negocio. Las funcionalidades Enterprise faltantes se cubren con módulos custom + OCA.

---

## Arquitectura

```
 App BR (existe)            WhatsApp (canal alternativo)
 Clientes + Proveedores     mop-core-ng (API Layer)
        │                          │
        │ JWT (Bearer token)        │ X-BR-API-Key (workspace)
        └──────────────┬────────────┘
                       ▼
             br_api  (Odoo http.Controller)
                       │
                       ▼
             Odoo 17 Community
             ├── br_service_order   FSM 9 estados
             ├── br_batisena        Cola inteligente + timers
             ├── br_provider_score  Score + onboarding
             ├── br_mercadopago     Escrow + split 85/15
             ├── br_subscription    Recurrentes
             ├── br_disputes        SLA 48h
             ├── br_liquidation     Batch jueves
             └── br_api             REST + webhooks salientes
                       │
                       ▼
             MercadoPago Advanced Payments API
```

### Dos clientes, un mismo API

| Cliente | Auth | Canal |
|---|---|---|
| App BR (existente) | JWT Bearer token (login con teléfono + OTP) | Web / Mobile |
| mop-core-ng | `X-BR-API-Key` por workspace | WhatsApp |

`br_api` maneja los dos modelos de auth. El JWT identifica al usuario final (cliente o proveedor) para aplicar permisos por rol. La API Key identifica al workspace de mop-core-ng y actúa en nombre de cualquier usuario.

---

---

## Nota: OCA `payment_mercadopago`

OCA tiene módulo `payment_mercadopago` en el repo `OCA/payment-provider`. Cubre el flujo estándar de MP (`POST /v1/payments`). **No incluye**:
- `capture=false` (authorize-only / escrow)
- MP Marketplace API (split 85/15 entre proveedor y BR)

**Plan**: usar el módulo OCA como punto de partida para la autenticación y webhooks, pero extender con la lógica de authorize+capture y Marketplace split en `br_mercadopago`. Ahorra ~10h vs partir desde cero.

---

## Endpoints br_api (mop-core-ng → Odoo)

```
# Órdenes (llamados por mop-core-ng)
POST /br/api/orders/create              # Voiceflow termina intake → crea orden
GET  /br/api/orders/{id}/status         # Polling estado FSM + datos proveedor asignado
POST /br/api/orders/{id}/confirm        # Cliente confirma + calificación (1-5)

# Batiseñal (mop-core-ng maneja timers de 60s)
POST /br/api/batisena/next              # Timer 60s expiró → pasar al siguiente proveedor

# Proveedor (botones WA → mop-core-ng → aquí)
POST /br/api/providers/{id}/accept      # Proveedor aceptó la oferta
POST /br/api/providers/{id}/arrived     # Llegó al domicilio + foto_url
POST /br/api/providers/{id}/done        # Trabajo terminado + foto_url

# Webhooks salientes (Odoo → mop-core-ng)
POST {mop_core_url}/br/event            # FSM cambió estado → mop-core-ng envía WA

# Config y pagos
GET  /br/api/config/rubros              # Rubros activos, precios, preguntas de intake
POST /br/api/mp/webhook                 # MercadoPago notifica pago autorizado/capturado
POST /br/api/orders/{id}/cash-collected # Cobrador marcó cobrado (Flujo B)
```

---

## Flows de Usuario (perspectiva API Layer)

### CLIENTE (WhatsApp)

```
1. Cliente escribe → Meta → mop-core-ng /whatsapp/webhook
2. mop-core-ng identifica workspace 'boton_rojo'
3. Voiceflow intake: rubro, descripción, fecha, franja, método de pago
   └── GET /br/api/config/rubros  (mop-core-ng carga preguntas dinámicas por rubro)
4. Al finalizar intake:
   └── POST /br/api/orders/create
       body: { wa_id, rubro_id, descripcion, fecha, franja, payment_method }
       resp: { order_id, mp_payment_link, monto_autorizar }
5. mop-core-ng envía link MP al cliente por WA (template WA-C01)
6. Cliente paga → MP → POST /br/api/mp/webhook
   └── Odoo: estado solicitud_creada → pago_autorizado → dispara br_batisena
7. Odoo → POST {mop_core}/br/event { event: 'order_queued', order_id }
   └── mop-core-ng → WA-C04: "Tu solicitud está en proceso, buscando proveedor"
8. [Batiseñal asigna proveedor]
   Odoo → POST {mop_core}/br/event { event: 'provider_assigned', provider_name, eta }
   └── mop-core-ng → WA-C05: "Juan M. (plomero ⭐4.8) está en camino"
9. Proveedor llega
   Odoo → POST {mop_core}/br/event { event: 'provider_arrived' }
   └── mop-core-ng → WA-C06: "El proveedor llegó a tu domicilio"
10. Trabajo finalizado
    Odoo → POST {mop_core}/br/event { event: 'work_done' }
    └── mop-core-ng → WA-C07: "¿Cómo salió el servicio? Respondé del 1 al 5"
11. Cliente califica
    └── POST /br/api/orders/{id}/confirm { rating: 5 }
12. Pago se libera (confirm inmediato o auto 24h)
    └── mop-core-ng → WA-C08: "¡Listo! Gracias por usar Botón Rojo"
```

### PROVEEDOR (WhatsApp)

```
1. [br_batisena calcula prioridad: score × 0.7 + tiempo_en_fila × 0.3]
2. Odoo → POST {mop_core}/br/event { event: 'batisena_offer', provider_wa_id, order_id, rubro, monto, direccion }
   └── mop-core-ng → WA-P01: "🔔 Nuevo trabajo: Plomería en Nordelta ARS 3.500. ¿Aceptás? [botón]"
3A. Proveedor toca "Aceptar" (dentro de 60s)
    └── POST /br/api/providers/{provider_id}/accept { order_id }
        Odoo: estado buscando_proveedor → proveedor_asignado
    └── mop-core-ng → WA-P02: "Trabajo confirmado. Av. Los Sauces 123, cliente: María G."
3B. No responde en 60s
    └── mop-core-ng setInterval(60000) expira → POST /br/api/batisena/next { order_id }
        Odoo: pasa al siguiente proveedor en cola (o estado sin_match si lista vacía)
4. Proveedor llega al domicilio, toca botón en WA
   └── POST /br/api/providers/{id}/arrived { order_id, photo_url }
       Odoo: estado → llegó
5. Trabajo finalizado, proveedor envía foto
   └── POST /br/api/providers/{id}/done { order_id, photo_url }
       Odoo: estado → trabajo_completado → inicia timer 24h auto-liberación
6. [Jueves] cron br_liquidation → vendor bill 85% → transferencia bancaria
   └── mop-core-ng → WA-P03: "Tu pago de ARS 2.975 fue acreditado"
```

### OPERADOR / OPS (Odoo Admin)

```
- Dashboard Kanban: órdenes activas por estado FSM en tiempo real
- Cola Batiseñal: qué proveedor tiene la oportunidad activa ahora
- Alerta automática: sin_match (>18 min sin proveedor) → notificación a Ops → intervención manual
- Onboarding proveedor: wizard 4 pasos (identidad, rubros, foto, aprobación)
- Disputas: si cliente abre reclamo → br.dispute asignada a Ops → SLA 48h
  └── A las 42h sin resolución → alerta escalada a Jefe de Ops
- Score: proveedores con score <3.0 → suspensión automática + notificación a Ops para revisión/reactivación
```

### COBRADOR (Flujo B — incluido en 280h)

```
1. Cliente eligió "efectivo" en intake (+5% recargo, mop-core-ng informa el total)
2. Orden creada en Odoo con estado pendiente_cobro_efvo (sin autorización MP)
3. Cobrador ve en dashboard Odoo: lista de órdenes por zona, dirección, monto con recargo
4. Cobrador va al domicilio → cobra en mano
5. Marca cobrado en Odoo:
   └── POST /br/api/orders/{id}/cash-collected { cobrador_id, monto_cobrado }
6. Odoo: estado → completado → libera 85% al proveedor en próxima liquidación
7. BR retiene: comisión 15% + recargo 5% (sobre el total)
8. mop-core-ng → WA-C08: "¡Listo! Tu servicio fue registrado como cobrado"
```

### FINANZAS (Odoo Admin)

```
- Jueves 18:00 UTC-3: ir.cron ejecuta br_liquidation
- Dashboard Finanzas: totales por proveedor, método de cobro, estado transferencia
- Exporta CSV para banco (post-piloto: auto via Pago Fácil API)
- Reembolsos desde br.dispute → account.move reversa automática
- Reporte: comisión BR 15% por rubro, ingresos netos semanales
```

---

## Módulos Custom (piloto 280h)

### 1. `br_service_order` (P0)
- Hereda de `project.task` + `mail.thread`
- FSM **9 estados core**: `solicitud_creada → pago_autorizado → buscando_proveedor → proveedor_asignado → en_camino → llegó → trabajo_completado → pago_liberado → completado`
- Estados alternativos: `sin_match`, `cancelado`, `en_disputa`
- 2 tipos de servicio en piloto: Directo + Con Diagnóstico (Recurrente → post-piloto)
- Auto-liberación 24h (ir.cron), con check de disputa abierta antes de liberar
- Log de transiciones: timestamp, actor, metadata JSON
- Webhooks salientes al cambiar estado → mop-core-ng

### 2. `br_batisena` (P0)
- Modelo `br.queue.entry`: provider_id, order_id, offered_at, expires_at, priority_score, status
- Prioridad: `score × 0.7 + tiempo_sin_trabajo × 0.3` (pesos configurables por rubro)
- **Timer 60s**: lo maneja mop-core-ng (setInterval → POST /br/api/batisena/next)
- Timer global 18 min: ir.cron → estado `sin_match` → alerta Ops
- Vista Kanban admin: cola activa en tiempo real

### 3. `br_provider_score` (P1)
- Campos en `res.partner`: `br_score`, `br_level`, `br_suspended`
- Score = calificación(40%) + tasa_aceptación(30%) + confiabilidad(20%) + cantidad(10%)
- Hourly cron: recalcula score
- Score <3.0 → **suspensión automática** (`br_suspended=True`) + notificación automática a Ops vía mail + alerta en dashboard
- Reactivación manual por Ops (score se recalcula, Ops confirma)
- Onboarding wizard 4 pasos: identidad (DNI+foto), rubros, seguro básico, aprobación

### 4. `br_subscription` (P1 — recurrentes)
- Modelo `br.subscription`: cliente_id, rubro_id, proveedor_asignado, precio_fijo, frecuencia (mensual/anual), próximo_vencimiento, estado
- `ir.cron` mensual: al vencer → crea automáticamente `br.service.order` tipo Recurrente para el período siguiente
- Al crear la orden recurrente → dispara br_batisena al proveedor asignado preferentemente
- Cancelación: mes en curso se cobra completo
- Fallo de pago: servicio CONTINÚA, alerta a Finanzas para cobro manual

### 5. `br_mercadopago` (P0)
- Base: OCA `payment_mercadopago` para auth + webhooks
- Extender con: `capture=false` (authorize-only) + `capture=true` (al liberar)
- MP Advanced Payments API: split 85% proveedor / 15% BR automático
- **Flujo B (efectivo)**: cliente elige "efectivo" → recargo 5%, estado `pendiente_cobro_efvo`
  - Dashboard cobrador en Odoo: lista órdenes pendientes de cobro en su zona
  - Cobrador marca cobrado: POST /br/api/orders/{id}/cash-collected { cobrador_id, monto }
  - Odoo actualiza estado → libera pago al proveedor (85% del neto sin recargo)

### 6. `br_disputes` (P1 básico)
- Modelo `br.dispute` simple (sin OCA helpdesk): order_id, cliente, motivo, estado, asignado_a
- SLA: alerta a 42h si no resuelta
- Resoluciones: reembolso / sin reembolso / re-servicio
- Bloquea auto-liberación de pago mientras disputa esté abierta

### 7. `br_liquidation` (P1)
- Cron jueves: agrupa órdenes `completado` de la semana
- Genera vendor bill por proveedor (85%)
- Método: transferencia bancaria directa (CSV export / manual)
- Pago Fácil API → post-piloto

### 8. `br_api` (P0)
- Controladores Odoo (http.Controller) con todos los endpoints listados arriba
- Middleware API Key (`X-BR-API-Key`)
- Webhooks salientes a mop-core-ng al cambiar estado FSM
- Rate limiting básico (counter en Redis o tabla Odoo)

---

## Presupuesto 280h

| Fase | Componente | Horas |
|---|---|---|
| **Fase 0: Infra** | VPS + Odoo + PostgreSQL + nginx + SSL + l10n_ar | 16h |
| **Fase 1: Núcleo** | `br_service_order` FSM + logs + vistas | 20h |
| | `br_batisena` cola + cron + admin | 24h |
| | `br_api` endpoints + auth dual (JWT + API Key) + webhooks salientes | 20h |
| | mop-core-ng: adapter `wa2br` + routing workspace | 16h |
| | 8 templates WA críticos | 6h |
| | 8 rubros + precios + intake Voiceflow | 6h |
| | Testing E2E Flujo Directo (app + WA) | 12h |
| **Subtotal Fase 1** | | **104h** |
| **Fase 2: Pagos** | `br_mercadopago` (OCA base + escrow + split) | 28h |
| | Flujo B efectivo + dashboard cobrador | 16h |
| | `br_liquidation` (batch jueves + bank transfer) | 14h |
| | Journales contables l10n_ar básicos | 6h |
| | Testing sandbox MP (Flujo A + B) | 8h |
| **Subtotal Fase 2** | | **72h** |
| **Fase 3: Proveedores** | `br_provider_score` + auto-suspensión score <3.0 | 28h |
| | Flujo Con Diagnóstico + curador umbral 30% | 12h |
| | `br_disputes` modelo simple + SLA alerta | 12h |
| | Templates WA adicionales (P01-P03, C05-C08) | 8h |
| **Subtotal Fase 3** | | **60h** |
| **Fase 4: Recurrentes** | `br_subscription` modelo + cron + auto-orden | 16h |
| **Buffer integración** | | **12h** |
| **TOTAL** | | **280h (~2 devs × 5.5 semanas)** |

### Diferido a post-piloto (no incluido)
| Componente | Horas |
|---|---|
| Score strikes 3x + reset 6 meses | 16h |
| `br_liquidation` Pago Fácil API | 10h |
| Portal PWA cliente (Next.js) | 320h |
| App móvil proveedor | 400h |
| `br_anti_bypass` IA + embeddings | 40h |

---

## Cambios en mop-core-ng

### Archivos a modificar
- `plugins/agents.js` — workspace tipo `boton_rojo`: campos `odoo_api_url` + `odoo_api_key`
- `plugins/adapter.js` — nuevo adaptador `wa2br` (WA input → payload `br_api`)
- `modules/whatsapp/whatsapp.controller.js` — si `workspace.type === 'boton_rojo'` → flujo BR
- nuevo `modules/botonrojo/br.controller.js` — handler webhook entrante de Odoo → envía WA
- `.env` — `ODOO_API_URL`, `ODOO_API_KEY`

### Timer Batiseñal (en mop-core-ng)
```js
// Al recibir event 'batisena_offer' de Odoo:
const timer = setTimeout(async () => {
  await brApi.post('/batisena/next', { order_id });
}, 60_000);
activeTimers.set(order_id, timer);

// Al recibir event 'provider_accepted':
clearTimeout(activeTimers.get(order_id));
activeTimers.delete(order_id);
```

---

---

## Repositorio

```
boton-rojo/
├── odoo-addons/
│   ├── br_base/           # Config, API Key management
│   ├── br_service_order/  # FSM, tipos de servicio
│   ├── br_batisena/       # Cola inteligente
│   ├── br_provider_score/ # Score + onboarding
│   ├── br_mercadopago/    # Escrow + split + flujo B (extiende OCA)
│   ├── br_subscription/   # Recurrentes (custom)
│   ├── br_disputes/       # Disputas SLA básico
│   ├── br_liquidation/    # Liquidación semanal
│   └── br_api/            # API REST + webhooks
└── mop-core-ng/           # Submódulo (adapter wa2br + timer batiseñal)
```

---

## Infraestructura

| Item | Costo mensual (USD) |
|---|---|
| VPS sa-east-1 (8GB RAM, 4 vCPU, SSD) | $80-150 |
| Odoo 17 Community | **$0** |
| MercadoPago comisión (4.10%) | Variable (paga el cliente) |
| Backup / CDN | ~$20 |
| **Total** | **~$100-170/mes** |
