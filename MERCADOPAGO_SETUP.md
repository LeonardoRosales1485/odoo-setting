# Setup de Integración MercadoPago - Guía paso a paso

## 1. Instalación del módulo - Forma simple (UI de Odoo)

### ✅ Recomendado: Instalar desde la interfaz web

**Pasos**:

1. Abre el navegador y ve a tu Odoo:
   - **Local**: http://localhost:8069
   - **GCP**: http://34.39.181.0:8069

2. **Login** con usuario `admin` / `admin`

3. Selecciona la **database** correcta:
   - Local: `botonrojo`
   - GCP: `odoo_br_pilot`

4. Ve a: **Aplicaciones** → **Aplicaciones**

5. Botón: **"Actualizar lista de aplicaciones"** (arriba a la derecha)
   - Espera a que termine (1-2 segundos)

6. Busca: `br_mercadopago`

7. Click en el módulo → Botón **"Instalar"**
   - Odoo cargará las dependencias automáticamente
   - Espera a que termine

8. ¡Listo! El módulo está instalado.

### ¿Qué significa "instalado"?

- Verás un nuevo menú: **Botón Rojo** → **Integración MP**
- Aparecerá un registro "Botón Rojo Principal" con placeholder de credenciales

### Alternativa: Si la instalación falla

Si ves un error tipo `RPC_ERROR`:

1. Ir a: **Aplicaciones** → **Módulos instalados**
2. Buscar: `br_mercadopago`
3. Si está en rojo, click en **Desinstalar**
4. Volver a **Aplicaciones** e intentar instalar de nuevo

## 2. Verificación post-instalación

### Paso 1: Verifica que el módulo está en la lista

1. Ve a: **Aplicaciones** → **Módulos instalados**
2. Busca: `br_mercadopago`
3. Debería estar con estado **"Instalado"** (verde)

### Paso 2: Verifica el menú

1. Ve a: **Botón Rojo** → **Integración MP**
2. Deberías ver una lista con un registro: **"Botón Rojo Principal"**
3. Click en él para abrir y verificar que tiene campos vacíos (placeholders)

### Paso 3: Prueba rápida

1. En el formulario "Botón Rojo Principal", rellena con datos de prueba:
   ```
   Seller ID: 999999999
   Access Token: TEST-TOKEN
   Client ID: TEST-CLIENT
   Client Secret: TEST-SECRET
   ```

2. Botón: **"Probar conexión"**
   - Debería fallar (credenciales inválidas)
   - Pero confirma que el sistema funciona

**Si ves la pantalla sin errores → ✅ Instalación exitosa**

## 3. Configurar credenciales reales de MercadoPago

### Paso 1: Obtener credenciales de MP

**Para SANDBOX (testing, recomendado primero)**:

1. Ve a: https://www.mercadopago.com.ar/developers/es/reference/marketplace-advanced-payments
2. Usa credenciales de prueba:
   ```
   Email: prueba@mercadopago.com
   Password: admin
   ```

3. O crea una cuenta propia:
   - https://www.mercadopago.com.ar/developers
   - Necesitas: email, razón social, CUIT, CBU

4. Una vez loguead, ve a:
   - **Credenciales**: https://www.mercadopago.com.ar/developers/panel/credentials
   - Copia:
     - **User ID** → seller_id
     - **Access Token** → APP_USR-xxxx...
     - **Client ID** → 123456789
     - **Client Secret** → secreto...

### Paso 2: Rellenar en Odoo

1. Ve a: **Botón Rojo** → **Integración MP**
2. Click en: **"Botón Rojo Principal"**
3. Edita los campos:
   ```
   Seller ID       → Copiar de MP Credenciales
   Access Token    → Copiar de MP Credenciales
   Client ID       → Copiar de MP Credenciales
   Client Secret   → Copiar de MP Credenciales
   ```

4. **Deja como está**:
   ```
   API URL         → https://api.mercadopago.com
   Ambiente        → Sin marcar (Sandbox)
   is_active       → Marcado ✓
   is_production   → Sin marcar (es sandbox)
   ```

5. Click: **"Probar conexión"**
   - Si funciona → ✓ Aparecerá un mensaje verde
   - Si falla → Verifica que copiaste bien las credenciales

6. Click: **Guardar**

## 4. Ambiente Sandbox vs. Producción

### Sandbox (Development, por defecto)

- URL: `https://api.mercadopago.com` (mismo para ambos)
- El servidor MP detecta automáticamente el ambiente por el token
- **Credenciales de prueba**:
  - Obtener en: https://www.mercadopago.com.ar/developers/es/reference/marketplace-advanced-payments
  - Usuario: prueba@mercadopago.com / Password: admin

### Producción

- Requiere: Cuenta MercadoPago Marketplace aprobada (2-4 semanas)
- Marcar en Odoo: `is_production = True`
- **Usar credenciales reales**
- **IMPORTANTE**: Cambiar antes de ir a producción

## 5. Primeras pruebas (sin Postman, vía UI)

### Test simple 1: Ver la configuración

1. Ve a: **Botón Rojo** → **Integración MP**
2. Click en: **"Botón Rojo Principal"**
3. Verifica que tiene campos rellenados (credenciales)
4. Click: **"Probar conexión"**
5. Debería salir: ✓ Conexión exitosa

---

### Test simple 2: Ver los pagos creados

1. Ve a: **Botón Rojo** → **Finanzas** → **Pagos MP**
2. Verás una lista de pagos (vacía al principio)
3. Cuando hagas pruebas con API, aparecerán aquí

---

### Test con Postman/cURL (avanzado)

**Necesitas**:
- Un JWT token válido de cliente (obtén del equipo de backend)
- O una X-BR-API-Key válida (workspace)

Ver archivo: **`MERCADOPAGO_POSTMAN_EXAMPLES.md`** para todos los ejemplos de cURL y Postman

**Flujo resumido**:
1. **Crear orden**: POST /br/api/orders/create → BR-0001
2. **Autorizar**: POST /br/api/payments/BR-0001/authorize
3. **Verificar**: GET /br/api/orders/BR-0001/status
4. **Capturar**: POST /br/api/payments/BR-0001/capture

## 6. Ver el estado de los pagos

### En la UI de Odoo

1. Ve a: **Botón Rojo** → **Finanzas** → **Pagos MP**
2. Verás una tabla con todos los pagos:
   - **Order**: BR-0001, BR-0002, etc.
   - **Amount**: Monto total
   - **Status**: pending / authorized / captured
   - **MP Payment ID**: ID del pago en MercadoPago
   - **Provider split**: 85%
   - **BR split**: 15%

3. Click en un pago para ver más detalles:
   - Pestaña "Respuesta MP": JSON crudo de MercadoPago
   - Historial de cambios

---

### Ver el último error (si algo falla)

1. Ve a: **Botón Rojo** → **Integración MP**
2. Click en: **"Botón Rojo Principal"**
3. Campo: **"Último error"** → Muestra qué falló
4. Campo: **"Última ejecución exitosa"** → Cuándo fue la última que funcionó

## 7. Troubleshooting

### Error 1: "No hay configuración activa de MercadoPago"

**¿Cuándo aparece?** Al intentar autorizar un pago

**Solución**:
1. Ve a: **Botón Rojo** → **Integración MP**
2. Click en "Botón Rojo Principal"
3. Verifica que el campo `is_active` está **marcado ✓**
4. Click: **Guardar**

---

### Error 2: "Error al autorizar pago: Invalid credentials"

**¿Cuándo aparece?** Al hacer POST /br/api/payments/{order}/authorize

**Solución**:
1. Ve a: **Botón Rojo** → **Integración MP**
2. Click en "Botón Rojo Principal"
3. Verifica que copiaste bien:
   - Seller ID (sin espacios)
   - Access Token (completo, empieza con `APP_USR-`)
   - Client ID y Secret (sin espacios)
4. Click: **"Probar conexión"**
   - Si sigue fallando, actualiza los tokens en:
     - https://www.mercadopago.com.ar/developers/panel/credentials

---

### Error 3: "Module loading br_mercadopago failed"

**¿Cuándo aparece?** Al instalar el módulo

**Solución**:
1. Ve a: **Aplicaciones** → **Módulos instalados**
2. Busca: `br_mercadopago`
3. Si está en rojo (error), click: **Desinstalar**
4. Vuelve a: **Aplicaciones** → Busca `br_mercadopago`
5. Click: **Instalar** de nuevo

---

### Error 4: "Orden no encontrada" en API

**¿Cuándo aparece?** Al hacer POST /br/api/payments/BR-XXXX/authorize

**Solución**:
1. Verifica que creaste la orden primero:
   - POST /br/api/orders/create → responde con order_id "BR-0001"
2. Copia exactamente ese order_id para los siguientes requests
3. Usa: `BR-0001` (no `br-0001` ni `BR-1`)

## 8. Información de respaldo

Si necesitas información técnica detallada, ver:
- `MERCADOPAGO_INTEGRATION.md` - Arquitectura y modelos
- `MERCADOPAGO_POSTMAN_EXAMPLES.md` - Ejemplos de API
- `README_MERCADOPAGO.md` - Resumen general

## 9. Checklists de configuración

### ☐ Antes de producción

- [ ] Credenciales reales de MP obtenidas
- [ ] `is_production = True` en mp.config
- [ ] "Probar conexión" ✓ exitosa
- [ ] Webhooks configurados en MP Dashboard
- [ ] Transacción de prueba exitosa (authorize → capture)
- [ ] Cron de liquidación testado (jueves 18:00)
- [ ] Backups configurados
- [ ] Logs configurados para auditoría

### ☐ Pruebas end-to-end

- [ ] Cliente: crear orden
- [ ] Sistema: generar pago autorizado
- [ ] Cliente: confirmar pago (authorize)
- [ ] Proveedor: asignado
- [ ] Proveedor: sube foto ANTES
- [ ] Proveedor: completa trabajo
- [ ] Cliente: confirma y califica
- [ ] Sistema: captura pago
- [ ] Sistema: crea liquidación (jueves)
- [ ] Proveedor: recibe 85%

---

**¿Preguntas?** Revisar: `MERCADOPAGO_INTEGRATION.md`
