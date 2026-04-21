# ⚠️ CAMBIO MANUAL REQUERIDO PARA USAR CHAT DE VOZ ENTRE 2 PCs

El chat de voz funciona, pero **NECESITAS hacer un cambio importante en `tsProject/settings.py`** para que funcione desde otra PC.

---

## 🔴 PROBLEMA

Django por defecto solo acepta conexiones desde `localhost` (la misma PC). Si intentas conectarte desde otra PC a la IP del servidor, recibirás error:

```
❌ HTTP Error 400 - Bad Request
Invalid HTTP_HOST header
```

Esto es por seguridad, pero bloquea que el amigo se conecte desde otra PC.

---

## ✅ SOLUCIÓN

### Archivo: `tsProject/settings.py`

**Buscar esta línea (alrededor de línea 33):**

```python
ALLOWED_HOSTS = []
```

**Cambiar a una de estas opciones:**

#### Opción A: Permitir TODAS las IPs (⚠️ solo desarrollo)

```python
ALLOWED_HOSTS = ['*']
```

**Ventaja:** Funciona inmediatamente, no necesitas saber la IP

**Desventaja:** Inseguro en producción

---

#### Opción B: Permitir IP específica (mejor para desarrollo)

```python
ALLOWED_HOSTS = ['192.168.1.100', 'localhost', '127.0.0.1']
```

Reemplaza `192.168.1.100` con la IP real de tu PC (ver `ipconfig` en terminal)

**Ventaja:** Más seguro

**Desventaja:** Necesitas actualizar si cambias de red

---

#### Opción C: Usar variable de ambiente (mejor para flexibilidad)

```python
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

Luego al ejecutar Django:

```bash
# En Windows:
set ALLOWED_HOSTS=*
python manage.py runserver 0.0.0.0:8000

# O en Linux/Mac:
export ALLOWED_HOSTS='*'
python manage.py runserver 0.0.0.0:8000
```

**Ventaja:** Flexible según el ambiente (dev/producción)

---

## 🚀 DESPUÉS DE HACER EL CAMBIO

1. **Guardar el archivo** `tsProject/settings.py`

2. **Reiniciar Django:**
   ```bash
   # Si está corriendo, presionar Ctrl+C
   # Luego ejecutar de nuevo:
   python manage.py runserver 0.0.0.0:8000
   ```

3. **Verificar que funcione:**
   - Desde la misma PC: http://localhost:8000 ✅
   - Desde otra PC: http://[IP]:8000 ✅ (Debería funcionar ahora)

---

## 📋 Próximos pasos

Una vez hecho este cambio, sigue la guía en **`GUIA_CONECTARSE_VOZCHAT.md`** para:

1. Iniciar Redis
2. Obtener IP del servidor
3. Conectarse desde otra PC
4. Activar chat de voz

---

## 💡 NOTA IMPORTANTE

- ✅ **Para desarrollo:** Usa `ALLOWED_HOSTS = ['*']`
- ❌ **Para producción:** NUNCA uses `['*']`, especifica IPs exactas
- 🔒 **En Django:**  Validar que ALLOWED_HOSTS esté bien seteado antes de deployer

