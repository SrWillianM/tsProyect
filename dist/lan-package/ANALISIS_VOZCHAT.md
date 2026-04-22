# ANALISIS TÉCNICO: Chat de Voz WebRTC + Django Channels

## 📋 Resumen Ejecutivo

Análisis de la implementación de chat de voz en tiempo real usando **SimplePeer (WebRTC) + Django Channels** para MVP TeamSpeak.

**Estado:** Funcional pero con problemas de configuración y resiliencia.

---

## 🏗️ Arquitectura General

```
┌─────────────────────┐
│   Cliente PC1       │
│  (browser + audio)  │
│   │                 │
│   ├─ SimplePeer JS  │
│   └─ WebSocket /ws/voice/
│
│       (P2P WebRTC)
│         ↓ ↑
│       (NAT/STUN)
│
│   ├─ WebSocket /ws/voice/
│   └─ Django Channels
│       (Redis fallback)
│
┌─────────────────────┐
│   Cliente PC2       │
│  (browser + audio)  │
└─────────────────────┘
```

### Flujo de Señalización

1. **PC1 connects** → WebSocket `/ws/voice/?alias=PC1` → `VoiceSignalingConsumer` registra en Redis
2. **PC1 requests users** → Recibe lista vacía (es el primero)
3. **PC2 connects** → WebSocket `/ws/voice/?alias=PC2` → Registra en Redis
4. **PC2 requests users** → Recibe `[PC1]` → Inicia conexión P2P como *initiator*
5. **PC1 recibe evento** "user_joined" → Crea conexión como *receiver*
6. **Intercambio SDP:**
   - PC2 (initiator) envía `offer` → PC1 recibe
   - PC1 (receiver) envía `answer` → PC2 recibe
7. **Intercambio ICE:**
   - Ambos intercambian candidatos para conectividad (STUN)
8. **P2P Connect:** Audio fluye directamente entre PCs

### Almacenamiento de Presencia

- **Redis Hash:** `voice_presence:room_name` → `{alias: '{"connected": true, "muted": true}'}`
- **Fallback:** En memoria si Redis no está disponible

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. **CRÍTICO: ALLOWED_HOSTS bloqueando inter-PC** 

**Ubicación:** `tsProject/settings.py` línea ~33

```python
ALLOWED_HOSTS = []  # ← BLOQUEA solicitudes desde otra PC
```

**Síntoma:** 
```
PC1 accede OK: http://127.0.0.1:8000/ ✅
PC2 intenta: http://192.168.x.x:8000/ → Error 400 Bad Request ❌
```

**Causa:** Django rechaza hosts que no están en `ALLOWED_HOSTS`

**Impacto:** ⛔ **No se puede conectar desde otra PC** (bloqueador #1)

**Solución:** 
```python
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
# O para desarrollo: ALLOWED_HOSTS = ['*']
```

---

### 2. **CRÍTICO: Redis sin manejo de errores**

**Ubicación:** `chat/consumers_voice.py` método `get_redis()`

```python
# ❌ PROBLEMATICO
@classmethod
def get_redis(cls):
    if cls._redis is None:
        cls._redis = redis.Redis(...)  # Sin try/except
        # Si Redis no está corriendo → CRASH
    return cls._redis
```

**Síntoma:**
```
$ python manage.py runserver
...
CRITICAL: Connection refused (Redis no running)
```

**Impacto:** ⛔ **Chat de voz no inicia si Redis no está disponible**

**Solución:**
```python
try:
    cls._redis = redis.Redis(...)
    cls._redis.ping()
    logger.info('Redis OK')
except Exception as e:
    logger.warning(f'Redis unavailable: {e}, usando fallback')
    cls._redis = None
```

---

### 3. **ALTO: Alias auto-generado muy largo**

**Ubicación:** `chat/routing.py` línea que genera alias

**Síntoma:**
```javascript
// Cliente recibe
alias: "user_12345678901234567890_abcdef"  // Demasiado largo
```

**Impacto:** 🟠 **Interfaz de usuario se vuelve fea, nombres no legibles**

**Solución:** Permitir al usuario ingresar alias corto (max 15 caracteres)

---

### 4. **ALTO: Manejo débil de errores Redis en operaciones**

**Ubicación:** `chat/consumers_voice.py` métodos `_register_voice_user`, `send_voice_users`

```python
# ❌ Sin try/except
user_data = r.hset(key, alias, data)  
all_users = r.hgetall(key)  
```

**Impacto:** 🟠 **Si Redis falla mid-operation, consumer crash**

**Solución:** Envolver todas ops Redis en try/except con fallback dict

---

### 5. **ALTO: Falta de tests para WebRTC**

**Ubicación:** `chat/tests.py` (línea ~100)

**Síntoma:**
```
pytest chat/tests.py -v
... 7 tests passed (pero 0 para WebRTC)
```

**Impacto:** 🟠 **Cambios en VoiceSignalingConsumer pueden romper sin noticia**

**Solución:** Agregar 3-5 tests de WebSocket para voz:
- Test conexión de usuario
- Test envío de señal
- Test desconexión

---

### 6. **MEDIO: STUN servers solo públicos (sin TURN)**

**Ubicación:** `static/js/voice-chat.js` línea ~50

```javascript
iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:global.stun.twilio.com:3478' }
    // ❌ Sin TURN server
]
```

**Impacto:** 🟡 **Si ambos clientes están tras NAT simétrico → no conectan**

**Solución:** Agregar TURN server (ej. coturn) para producción

---

### 7. **MEDIO: Audio no pide permiso explícito**

**Ubicación:** `static/js/voice-chat.js` línea ~80

```javascript
navigator.mediaDevices.getUserMedia({ audio: true })
// Sin mostrar UI de permiso explícito
```

**Impacto:** 🟡 **Algunos navegadores bloquean, usuario confundido**

**Solución:** Mostrar modal "Permitir micrófono" antes de conectar

---

### 8. **MEDIO: Presencia sincronizada pero sin validación**

**Ubicación:** `chat/consumers_voice.py` método `send_voice_users`

```python
# ❌ No valida si el usuario realmente existe
users = r.hgetall(key)  # Confía en Redis
```

**Impacto:** 🟡 **Si Redis quedó con datos stale, se muestran usuarios fantasma**

**Solución:** Agregar timestamp, limpiar presencia > 60s sin ping

---

## ✅ LO QUE FUNCIONA BIEN

- ✅ **SimplePeer P2P:** Conexión directa entre navegadores (SDP/ICE correctos)
- ✅ **Señalización:** Django Channels reenvía correctamente offers/answers
- ✅ **Mute/unmute:** Se refleja en ambas partes
- ✅ **Heartbeat:** WebSocket se mantiene vivo

---

## 📋 RECOMENDACIONES (Prioridad)

| Prioridad | Tarea | Esfuerzo | Bloqueador |
|-----------|-------|----------|-----------|
| CRÍTICO   | Corregir ALLOWED_HOSTS | 2 min | SÍ |
| CRÍTICO   | Agregar Redis error handling | 15 min | PARCIAL |
| ALTO      | Alias corto del usuario | 30 min | NO |
| ALTO      | Tests WebRTC en ChatApiTests | 45 min | NO |
| MEDIO     | TURN server + config | 1 hora | NO |
| MEDIO     | Modal de permiso audio | 30 min | NO |
| BAJO      | Limpiar presencia stale | 20 min | NO |

---

## 🚀 PARA PROBAR HOY

1. **Hacer cambio en settings.py:**
   ```python
   ALLOWED_HOSTS = ['*']  # Solo desarrollo
   ```

2. **Iniciar Redis:** 
   ```bash
   docker compose up -d redis
   ```

3. **Iniciar servidor:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. **Conectar desde otra PC:**
   ```
   http://<IP_SERVIDOR>:8000
   → Sala "test" → Conectar Voz → ✅ Debería funcionar
   ```

---

## 📝 Análisis de Complejidad

- **SimplePeer:** 9.11.1 desde CDN (maduro, confiable)
- **Django Channels:** 4.3.2 (producción-ready)
- **Redis:** 7.4.0 (pero no es crítico si está offline)
- **Código WebRTC:** ~450 líneas Python + 200 líneas JS (manejable)

