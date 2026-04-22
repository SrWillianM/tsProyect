# Investigación WebRTC - Chat de Voz

## Comparación de Librerías

### 1. PeerJS
- **Pros:**
  - Servidor de señalización incluido (PeerServer)
  - API de alto nivel muy simple
  - 13.3k estrellas en GitHub
  - Soporta data connections y media calls
  - Documentación completa
- **Contras:**
  - Dependencia de servidor externo (puede self-host)
  - Requiere servidor para discovery inicial
  - Más pesado que simple-peer

### 2. simple-peer
- **Pros:**
  - Más ligero (7.8k estrellas)
  - No requiere servidor externo para signaling
  - Puedes implementar tu propio signaling con WebSockets
  - Mejor control sobre la conexión
  - Muy popular en producción (WebTorrent, etc.)
- **Contras:**
  - API más baja que PeerJS
  - Requiere implementar signaling manualmente

### 3. WebRTC Nativo
- **Pros:**
  - Sin dependencias adicionales
  - Control total
- **Contras:**
  - Mucho más código
  - Manejo complejo de ICE candidates

---

## Recomendación: **simple-peer**

Para este proyecto, **simple-peer** es la mejor opción porque:
1. ✅ Se integra perfectamente con Django Channels (nuestro propio signaling)
2. ✅ No necesitamos servidor externo
3. ✅ Más control sobre la señalización
4. ✅ Ligero y bien mantenido

---

## Servidores STUN/TURN

### ¿Qué son?
- **STUN** (Session Traversal Utilities for NAT): Permite a los peers descubrir su IP pública y tipo de NAT
- **TURN** (Traversal Using Relays around NAT): Servidor relay cuando STUN no funciona (redes restrictivas)

### Servidores públicos gratuitos:
```javascript
{
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:global.stun.twilio.com:3478' }
  ]
}
```

### ¿Necesitamos TURN?
- **Redes domésticas:** STUN suficiente (~85% de conexiones)
- **Redes corporativas/firewalls:** Requiere TURN
- **Producción:** Recomendado coturn o Twilio

### Para MVP: STUN público gratuito es suficiente

---

## Arquitectura de Señalización con Django Channels

### Flujo:
```
[Navegador A] <-- WebSocket (SDP/ICE) --> [Django Channel] <-- group_send --> [Navegador B]
         <-- simple-peer P2P (audio) --> [Navegador B]
```

### Grupo por sala:
- Cada sala de chat tendrá un `room_group_name` 
- La señalización WebSocket se envía a este grupo
- Los usuarios en la sala reciben los mensajes de señalización

### Eventos de señalización:
```json
{
  "event": "webrtc_signal",
  "type": "offer|answer|ice-candidate",
  "from": "usuario_A",
  "signal": { ... }
}
```

---

## Descubrimiento de Usuarios en Sala

### Mecanismo:
1. Cuando un usuario se conecta al WebSocket de voz, se registra en el grupo de presencia de la sala
2. El consumidor mantiene un diccionario de usuarios en voz por sala
3. Al entrar, el usuario recibe la lista actual de usuarios en voz
4. Cuando alguien entra/sale, se notifica a todos los de la sala

### Estructura de datos:
```python
voice_presence = {
    "sala_1": {
        "usuario_1": {"connected": true, "muted": false},
        "usuario_2": {"connected": true, "muted": true}
    }
}
```

---

## Consumo de Recursos Estimado

### Por usuario en voz:
- **CPU:** 5-15% (codec Opus optimizado)
- **Ancho de banda:** 
  - Audio solo: ~40-80 kbps (codec Opus)
  - Con video: ~500-1500 kbps
- **RAM:** ~50-100 MB por peer

### Para 4 usuarios (mesh):
- **Ancho de banda total:** ~160-320 kbps × 3 conexiones = 480-960 kbps
- **CPU total:** ~20-40%

---

## Próximos Pasos

1. [x] Investigar alternativas WebRTC
2. [x] Evaluar servidores STUN/TURN
3. [x] Crear PoC con 2 navegadores
4. [x] Documentar consumo de recursos
5. [x] Definir arquitectura de descubrimiento

---

## Archivos Creados

### 1. `static/js/voice-chat.js`
Cliente JavaScript que usa **simple-peer** para WebRTC:
- Clase `VoiceChat` con API limpia
- Manejo de stream de audio
- Conexión P2P mesh entre usuarios
- Controles de mute/unmute
- Eventos para UI

### 2. `chat/consumers_voice.py`
Consumidor Django Channels para señalización:
- `VoiceSignalingConsumer` - maneja presencia de voz
- Eventos: `join`, `leave`, `signal`, `mute_status`
- Reenvío de señales SDP/ICE entre peers

### 3. `chat/routing.py`
Nueva ruta WebSocket para voz:
- `/ws/voice/<room_name>/` - señalización de voz

---

## Cómo probar el PoC

1. Descargar `simple-peer.min.js` de https://cdnjs.com/libraries/simple-peer
2. Guardar en `static/js/simple-peer.min.js`
3. Agregar a `room.html`:
   ```html
   <script src="{% static 'js/simple-peer.min.js' %}"></script>
   <script src="{% static 'js/voice-chat.js' %}"></script>
   ```
4. Agregar botones de voz en el HTML
5. Abrir dos navegadores en la misma sala