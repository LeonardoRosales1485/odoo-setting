# Setup de MercadoPago en GCP - Paso a paso simple

## ✅ Acceso GCP

```
URL: http://34.39.181.0:8069
Usuario: admin
Contraseña: admin
Database: odoo_br_pilot
```

---

## 📋 Pasos (3 minutos)

### 1️⃣ Abre Odoo en GCP

Ve a: **http://34.39.181.0:8069**

Login: `admin` / `admin`

Selecciona database: `odoo_br_pilot`

---

### 2️⃣ Instala el módulo br_mercadopago

Menú: **Aplicaciones** → **Aplicaciones**

Botón: **"Actualizar lista de aplicaciones"** (espera 2 segundos)

Busca: `br_mercadopago`

Click: **Instalar**

Espera a que termine...

---

### 3️⃣ Verifica que se instaló

Menú: **Botón Rojo** → **Integración MP**

Deberías ver: **"Botón Rojo Principal"**

---

### 4️⃣ Obtén credenciales de MercadoPago

Ve a: https://www.mercadopago.com.ar/developers/panel/credentials

**Copia** estos 4 valores:
- **User ID** → será `Seller ID`
- **Access Token** → será `Access Token`
- **Client ID** → será `Client ID`
- **Client Secret** → será `Client Secret`

---

### 5️⃣ Rellena credenciales en Odoo

De vuelta en Odoo:

Menú: **Botón Rojo** → **Integración MP**

Click en: **"Botón Rojo Principal"**

Rellena los 4 campos con lo que copiaste de MP

```
Seller ID       → [pegar]
Access Token    → [pegar]
Client ID       → [pegar]
Client Secret   → [pegar]
```

---

### 6️⃣ Prueba la conexión

Botón: **"Probar conexión"**

Debería mostrar:
```
✓ Conexión a MercadoPago exitosa
```

Si no, verifica que copiaste bien sin espacios extra.

---

### 7️⃣ Marca como activo

Campo: **is_active** → Debe estar ✓ marcado

Botón: **Guardar**

---

## ✅ ¡Listo!

Ahora puedes:

1. **Crear órdenes** con método de pago MP
2. **Autorizar pagos** (reserva fondos)
3. **Capturar pagos** (tomar los fondos)

**Ver ejemplo completo**: `MERCADOPAGO_POSTMAN_EXAMPLES.md`

---

## ❓ Problemas?

### "Error al probar conexión"

→ Verifica que copiaste bien las credenciales sin espacios

### "Module loading br_mercadopago failed"

→ Desinstala → Instala de nuevo

### "No hay configuración activa"

→ Verifica que `is_active` está marcado ✓

---

**¿Necesitas help?** Revisa: `MERCADOPAGO_SETUP.md`
