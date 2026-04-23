# Botón Rojo — Handoff para editor de código con IA

## Contexto del proyecto

Botón Rojo es un marketplace de servicios para el hogar (piloto Nordelta, Argentina).
MoP Tech construye el backend como módulos custom sobre **Odoo 17 Community**.

### Stack
- **Backend:** Odoo 17 Community (módulos custom Python)
- **Base de datos:** PostgreSQL 15
- **Entorno local:** Docker Desktop en Windows
- **Editor:** VS Code
- **Carpeta de trabajo:** `C:\botonrojo\addons\`

---

## Setup Docker (entorno local)

```powershell
# Levantar base de datos
docker run -d --name odoo-db -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres postgres:15

# Levantar Odoo con carpeta de addons montada
docker run -d --name odoo-br -p 8069:8069 -e HOST=db -e USER=odoo -e PASSWORD=odoo --link odoo-db:db -v C:\botonrojo\addons:/mnt/extra-addons odoo:17

# Verificar que corren
docker ps
```

### Configuración en el contenedor
El archivo `/etc/odoo/odoo.conf` dentro del contenedor tiene:
```
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
admin_passwd = ...
```

### Comandos útiles

```powershell
# Actualizar un módulo específico
docker exec -it odoo-br odoo -d botonrojo --db_host=db --db_user=odoo --db_password=odoo --update=NOMBRE_MODULO --stop-after-init

# Reiniciar Odoo
docker restart odoo-br

# Ver logs
docker logs odoo-br --tail=50

# Acceder a la base de datos
docker exec -it odoo-db psql -U odoo -d botonrojo
```

### URL de acceso
- Normal: `http://localhost:8069`
- Con debug: `http://localhost:8069/web?debug=1`
- Base de datos: `botonrojo`

---

## Módulos construidos hasta ahora

### 1. `br_provider_score` ✅ INSTALADO

Agrega campos de proveedor BR al modelo `res.partner` (contactos).

**Estructura:**
```
br_provider_score/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── res_partner.py
└── views/
    └── res_partner_views.xml
```

**Campos agregados a `res.partner`:**
| Campo | Tipo | Descripción |
|---|---|---|
| `br_score` | Float | Score dinámico (0-5) |
| `br_level` | Selection | Registrado / Activo / Verificado / Referenciado |
| `br_suspended` | Boolean | Si está suspendido |
| `br_rubros` | Char | Rubros que cubre |
| `br_whatsapp` | Char | Número WhatsApp para Batiseñal |
| `br_zona` | Char | Zona de cobertura |
| `br_jobs_completed` | Integer | Trabajos completados |
| `br_is_provider` | Boolean | Es proveedor BR |

**Nota importante:** No tiene `security/ir.model.access.csv` porque hereda de `res.partner` que ya tiene permisos. Si da error de acceso, agregar el archivo de seguridad.

---

### 2. `br_service_order` ✅ INSTALADO

Módulo central. Define las órdenes de servicio con FSM de 9 estados.

**Estructura:**
```
br_service_order/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── models/
│   ├── __init__.py
│   └── br_service_order.py
└── views/
    ├── br_service_order_views.xml
    └── br_service_order_menus.xml
```

**Modelo: `br.service.order`**

Hereda de `mail.thread` y `mail.activity.mixin` para tener chatter y log de cambios.

**Estados FSM (en orden):**
```
solicitud_creada → pago_autorizado → buscando_proveedor → proveedor_asignado
→ en_camino → llego → trabajo_completado → pago_liberado → completado
```

**Estados alternativos:**
- `sin_match` — nadie aceptó en 18 min
- `cancelado` — cliente canceló
- `disputa_abierta` — cliente reclamó
- `pendiente_cobro_efvo` — pago en efectivo pendiente

**Campos principales:**
| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Número automático BR-0001, BR-0002... |
| `client_id` | Many2one(res.partner) | Cliente |
| `provider_id` | Many2one(res.partner) | Proveedor (filtrado por br_is_provider=True) |
| `rubro` | Selection | plomero, electricista, limpieza, jardinero, piletero, parrillero, ninyera, lava_autos |
| `service_type` | Selection | directo, diagnostico, recurrente |
| `amount` | Float | Monto del servicio |
| `payment_method` | Selection | mp, efectivo |
| `scheduled_date` | Date | Fecha programada |
| `franja` | Selection | manana, mediodia, tarde |
| `state` | Selection | Ver FSM arriba |
| `photo_before` | Binary | Foto ANTES (obligatoria) |
| `photo_after` | Binary | Foto DESPUÉS |
| `rating` | Selection | 1-5 estrellas |

**Métodos de transición:**
```python
action_autorizar_pago()
action_buscar_proveedor()
action_asignar_proveedor()   # valida que haya provider_id
action_en_camino()
action_llego()
action_trabajo_completado()  # valida que haya photo_before
action_liberar_pago()
action_completar()
action_cancelar()
action_abrir_disputa()
action_sin_match()
```

**Secuencia automática:** prefijo `BR-`, padding 4 → BR-0001, BR-0002...

**Vistas:** Kanban (agrupado por state), Lista, Formulario con header de botones y statusbar.

**Menú:** `Botón Rojo > Órdenes de Servicio`

**Problema conocido con el menú:**
El menú raíz "Botón Rojo" no aparece automáticamente en la barra de navegación por un bug de caché/registro. Se insertó manualmente en la base de datos. Si se reinstala desde cero, ejecutar este script Python:

```python
# fix_menu.py — copiar al contenedor y ejecutar
import psycopg2
import json

conn = psycopg2.connect(host='db', dbname='botonrojo', user='odoo', password='odoo')
cur = conn.cursor()

# Obtener IDs actuales
cur.execute("SELECT id FROM ir_ui_menu WHERE name::text LIKE '%Bot%'")
root_menu = cur.fetchone()

cur.execute("SELECT id FROM ir_act_window WHERE res_model = 'br.service.order'")
action = cur.fetchone()

if root_menu and action:
    name = json.dumps({"en_US": "Ordenes de Servicio"})
    cur.execute(
        "INSERT INTO ir_ui_menu (name, parent_id, action, sequence) VALUES (%s::jsonb, %s, %s, %s)",
        (name, root_menu[0], f'ir.actions.act_window,{action[0]}', 10)
    )
    conn.commit()
    print('Menu insertado OK')

cur.close()
conn.close()
```

```powershell
docker cp fix_menu.py odoo-br:/tmp/fix_menu.py
docker exec -it odoo-br python3 /tmp/fix_menu.py
docker restart odoo-br
```

**Acceso directo al módulo (sin menú):**
```
http://localhost:8069/web#action=344
```
(El ID 344 puede variar si se reinstala la base — verificar con: `SELECT id FROM ir_act_window WHERE res_model = 'br.service.order';`)

---

### 3. `br_batisena` ⏳ DESCARGADO, PENDIENTE INSTALAR

Cola inteligente de asignación de proveedores.

**Estructura:**
```
br_batisena/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── models/
│   ├── __init__.py
│   └── br_batisena.py
└── views/
    ├── br_batisena_views.xml
    └── br_batisena_menus.xml
```

**Modelo: `br.queue.entry`**

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | Many2one(br.service.order) | Orden asociada |
| `provider_id` | Many2one(res.partner) | Proveedor notificado |
| `offered_at` | Datetime | Cuándo se envió la oferta |
| `expires_at` | Datetime | Cuándo expira (60s después) |
| `provider_score` | Float | Score al momento de la oferta |
| `priority_score` | Float | score×0.7 + jobs×0.3 |
| `status` | Selection | waiting, accepted, expired, skipped |

**Métodos:**
```python
create_queue_for_order(order_id)  # crea entradas para todos los proveedores disponibles
action_accept()                    # proveedor acepta, actualiza orden a proveedor_asignado
action_expire()                    # timer expiró
get_active_queue(order_id)         # retorna cola activa
```

**Algoritmo de prioridad:**
```python
priority_score = (br_score * 0.7) + (br_jobs_completed * 0.3)
```
Los pesos son configurables. En producción el segundo factor será "tiempo sin recibir trabajo".

**Menú:** `Botón Rojo > Cola Batiseñal` (sequence=20, después de Órdenes de Servicio)

**Para instalar:**
```powershell
docker exec -it odoo-br odoo -d botonrojo --db_host=db --db_user=odoo --db_password=odoo --update=br_batisena --stop-after-init
docker restart odoo-br
```

---

## Módulos pendientes de construir

### 4. `br_mercadopago` (P0)
- Base: módulo OCA `payment_mercadopago`
- Agregar: `capture=false` (authorize-only / escrow)
- Agregar: MP Advanced Payments API split 85/15
- Flujo B efectivo: recargo 5%, dashboard cobrador
- Modelo: extender `payment.transaction`

### 5. `br_disputes` (P1)
- Modelo: `br.dispute`
- Campos: order_id, cliente, motivo, estado, asignado_a, SLA
- Bloquea auto-liberación de pago
- Alerta a 42h si no resuelta (SLA 48h)
- Resoluciones: reembolso / sin reembolso / re-servicio

### 6. `br_liquidation` (P1)
- Cron jueves 18:00 UTC-3
- Agrupa órdenes `completado` de la semana
- Genera vendor bill por proveedor (85%)
- Exporta CSV para banco

### 7. `br_subscription` (P1)
- Modelo: `br.subscription`
- Cron mensual/anual: crea órdenes automáticas
- Prioriza proveedor asignado en Batiseñal

### 8. `br_api` (P0)
- Controladores REST (`http.Controller`)
- Auth dual: JWT (app BR) + API Key (mop-core-ng/WhatsApp)
- Webhooks salientes a mop-core-ng al cambiar estado FSM
- Rate limiting básico

---

## Endpoints REST planificados (br_api)

```
# Auth
POST /br/api/auth/otp/request
POST /br/api/auth/otp/verify      → JWT + rol
POST /br/api/auth/refresh

# Órdenes (clientes)
POST /br/api/orders/create
GET  /br/api/orders/{id}/status
GET  /br/api/orders/history
POST /br/api/orders/{id}/confirm  → calificación 1-5
POST /br/api/orders/{id}/dispute

# Proveedores
GET  /br/api/providers/me/queue
POST /br/api/providers/me/accept
POST /br/api/providers/me/arrived  → foto_url
POST /br/api/providers/me/done     → foto_url
GET  /br/api/providers/me/history
GET  /br/api/providers/me/earnings

# Batiseñal
POST /br/api/batisena/next         → timer 60s expiró

# Config y pagos
GET  /br/api/config/rubros
POST /br/api/mp/webhook            → MercadoPago notifica
POST /br/api/orders/{id}/cash-collected

# Webhooks salientes (Odoo → mop-core-ng)
POST {mop_core_url}/br/event
```

**Eventos webhook salientes:**
```json
{
  "event": "provider_assigned",
  "order_id": "BR-0042",
  "state": "proveedor_asignado",
  "data": {
    "provider_name": "Juan M.",
    "provider_score": 4.8,
    "eta_minutes": 25
  }
}
```

Eventos disponibles: `order_queued`, `provider_assigned`, `provider_arrived`, `work_done`, `payment_released`, `dispute_opened`, `dispute_resolved`

---

## Reglas importantes de Odoo 17

Cosas que cambiaron en Odoo 17 y generaron errores durante el desarrollo:

| Problema | Solución |
|---|---|
| Atributo `states` en botones deprecado | Usar `invisible="state != 'x'"` |
| Vista lista con `<list>` da error de schema | Usar `<tree>` dentro del arch (el tag externo sigue siendo tree) |
| Chatter con `<div class="oe_chatter">` | Usar `<chatter/>` en Odoo 17 |
| Módulo sin `security/ir.model.access.csv` | Access Error al intentar abrir el modelo |
| Menú raíz sin submenús no aparece | Necesita al menos un submenú con action válido |

---

## Datos de prueba cargados

**Proveedor:** Juan Martinez
- CUIT: 20397665225
- AFIP: Responsable Monotributo
- Tags: plomero, zona-nordelta
- br_is_provider: True
- br_level: Activo (1_active)
- br_score: 4.80
- br_jobs_completed: 12
- br_whatsapp: 1155667788
- br_zona: Nordelta

**Orden de prueba:** BR-0001
- Cliente: Juan Martinez
- Proveedor: Juan Martinez
- Rubro: Plomero
- Tipo: Directo
- Monto: $3.500
- Estado: Completado (recorrió todos los estados)

---

## Usuarios creados en Odoo

| Usuario | Email | Rol | Permisos |
|---|---|---|---|
| Administrator | leonardorosales1485@gmail.com | Admin | Todo |
| Operador Test | ...+operadortest@gmail.com | Ops | Project: User |
| Finanzas Test | — | Finanzas | Project: User, Invoicing: Billing Admin |
| Cobrador Test | — | Cobrador | Project: User |
| Admin Test | — | CEO | Project: Admin, Invoicing: Billing Admin, Administration: Access Rights |

---

## Modelo de negocio (referencia rápida)

| Concepto | Valor |
|---|---|
| Comisión BR piloto | 15% |
| Split proveedor | 85% |
| Fee MercadoPago | 4.10% (lo paga el cliente) |
| Recargo efectivo | +5% |
| Liquidación | Jueves 18:00 |
| Timer Batiseñal | 60 segundos por proveedor |
| Timer global | 18 minutos (luego → sin_match) |
| Score mínimo activo | 3.0 (abajo → suspensión automática) |
| Score para rubro extra | ≥ 3.5 |

---

## Archivos de referencia del proyecto

- `BOTON-ROJO-PLAN.md` — Plan técnico interno MoP Tech
- `BR-APP-REQUIREMENTS.md` — Requerimientos a Botón Rojo
- `Boton_Rojo_PRD.pdf` — Product Requirements Document completo
