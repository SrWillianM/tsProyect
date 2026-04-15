# Tareas Trello - TeamSpeak Clone MVP

## 📋 COMPAÑERO 1: Chat de Voz (Audio/WebRTC)

### Tarea 1.1: Investigar e integrar WebRTC con Channels
**Descripción:**
- Investigar y documentar la mejor forma de integrar WebRTC (simple-peer, PeerJS o similar) con Django Channels
- Evaluar alternativas: STUN/TURN servers, librerías recomendadas
- Crear PoC (Proof of Concept) con conexión P2P entre 2 navegadores
- Documentar consumo de recursos esperado (CPU, ancho de banda)
- Definir arquitectura de cómo los usuarios se "descubrirán" entre sí dentro de una sala

**Criterios de aceptación:**
- PoC funcional con 2 clientes estableciendo conexión de voz
- Documentación de arquitectura decisiones
- Consumo de recursos medido y documentado

---

### Tarea 1.2: Crear consumidor WebSocket para señalización de WebRTC
**Descripción:**
- Modificar `chat/consumers.py` (o crear `ChatVoiceConsumer`) para manejar:
  - Intercambio de ofertas/respuestas SDP
  - Intercambio de candidatos ICE
  - Listar usuarios disponibles en cada sala (presencia)
  - Notificar conexión/desconexión de usuarios
- Garantizar que WebSocket de signaling NO bloquee el chat de texto existente
- Implementar manejo de errores y timeouts en negociación de conexión

**Criterios de aceptación:**
- Consumidor funcional manejando señalización
- Chat de texto sigue funcionando sin degradación
- Usuarios pueden conectar/desconectar sin errores

---

### Tarea 1.3: Interfaz UI básica para controles de voz
**Descripción:**
- Crear botones en `room.html` para:
  - Conectar/desconectar voz
  - Mute/Unmute micrófono
  - Mute/Unmute altavoz
  - Ver lista de usuarios conectados en voz en la sala
- Indicadores visuales: usuario hablando, usuario muteado, conexión activa
- Usar elementos simples (no requiere heavy JS framework si es posible)

**Criterios de aceptación:**
- Botones funcionales y accesibles
- Indicadores visuales clara
- Compatible con responsive design existente

---

### Tarea 1.4: Pruebas y estabilización de conexión de voz
**Descripción:**
- Test de reconexión cuando se pierde conexión de red
- Test de múltiples usuarios simultáneamente (3+ usuarios en una sala)
- Manejo de latencia y jitter
- Documentación de limitaciones (máximo usuarios recomendados por sala, ancho de banda mínimo)

**Criterios de aceptación:**
- Tests unitarios e integración para WebRTC
- Documentación de limits
- PoC estable con 4+ usuarios

---

## 🎨 COMPAÑERO 2: Interfaz UI y Sistema de Login

### Tarea 2.1: Implementar sistema de autenticación (Django Auth)
**Descripción:**
- Crear vistas de login/registro usando Django auth estándar
- Implementar `login_required` decorador en vistas protegidas
- Crear página de registro con email y password
- Implementar logout
- Gestión de sesiones: ¿cuánto tiempo expira sesión? (default 14 días Django, considerar reducir)
- Modelo opcional: extender `auth.User` con perfil (avatar_url, estado, etc.)

**Criterios de aceptación:**
- Login/registro funcionando
- Rutas protegidas
- Sesiones con duración configurable
- Usuarios no autenticados redirigidos a login

---

### Tarea 2.2: Rediseñar y mejorar layout de salas
**Descripción:**
- Refactor del HTML/CSS de `base.html` y `room.html` para:
  - Mostrar usuario logueado en esquina (dropdown con avatar, estado, logout)
  - Mejorar sidebar: agregar buscador de salas, mute/unmute sidebar
  - Cargar historial de mensajes previos (últimos 50 o scroll infinito)
  - Indicadores: "usuario escribiendo", "usuario en voz"
  - Panel de detalles de sala: descripción, miembros activos, creada por, etc.
- Mantener diseño responsive actual (mobile-first)

**Criterios de aceptación:**
- Usuario logueado visible
- Historial cargable
- Indicadores de presencia en tiempo real
- Responsive en mobile

---

### Tarea 2.3: Crear página de gestión de salas
**Descripción:**
- Vista para crear salas (no solo admin)
- Permisos básicos:
  - Creador es admin de sala
  - Admin puede: eliminar sala, cambiar nombre, descripción, invitar/expulsar usuarios
  - Usuarios: pueden salir de sala
- Interfaz: formulario simple, modal o página dedicada
- Evitar eliminación accidental (confirmación)

**Criterios de aceptación:**
- CRUD de salas desde UI
- Permisos respetados
- Confirmaciones antes de borrar

---

### Tarea 2.4: Implementar perfil de usuario
**Descripción:**
- Página de perfil con:
  - Avatar (upload o gravatar)
  - Nombre visible
  - Estado (En línea, En una sala, Ausente)
  - Historial de salas (últimas 10)
  - Configuración: tema (claro/oscuro), notificaciones
- Editar perfil: cambiar contraseña, avatar, nombre

**Criterios de aceptación:**
- Página de perfil accesible
- Edición de datos funcionando
- Avatar cargando sin errores

---

### Tarea 2.5: Mejorar diseño visual y UX
**Descripción:**
- Actualizar paleta de colores si es necesario (actual: teal/beige está bien, pero revisar accesibilidad)
- Tipografía: mejorar legibilidad en chat (tamaños fonts, espaciado)
- Animaciones suaves (transiciones CSS, no JavaScript pesado)
- Theme oscuro como opción
- Testear en navegadores: Chrome, Firefox, Safari, Edge

**Criterios de aceptación:**
- Visualmente cohesivo
- Accesible (WCAG AA mínimo)
- Responsive probado
- <3 segundos de carga en conexión 3G

---

## 💬 TU PARTE: Chat de Texto Optimizado y Estable

### Tarea 3.1: Cargar historial de mensajes al entrar a sala (lazy loading)
**Descripción:**
- Cuando usuario entra a sala, cargar últimos 30 mensajes (no todos, evitar memory leak)
- Implementar infinite scroll: cargar 30 más al scroll hacia arriba
- Usar API REST separada `GET /api/rooms/<room>/messages/?limit=30&offset=0`
- **Optimización:** Paginar siempre, nunca cargar todo de BD
- Evitar duplicate render: marcar mensajes como "cargados desde DB" vs "en tiempo real"
- Backend: querysets optimizados con `select_related()` y `only()` para reducir queries

**Criterios de aceptación:**
- Historial cargando sin delay notable
- Infinite scroll funcionando suavemente
- DB queries optimizadas (<50ms por request)
- No hay memory leaks en cliente

---

### Tarea 3.2: Optimizar persistencia de mensajes en BD
**Descripción:**
- Auditar modelo `Message` en `models.py` para:
  - ¿Índices necesarios? (room_id, timestamp) para query rápida
  - ¿Campos innecesarios? (actualmente: id, room_fk, alias, content, timestamp - parece OK)
  - Considerar: limpieza automática de mensajes muy antiguos (policy: borrar >30 días, archivable a archivo aparte)
  - Connection pooling: garantizar no estamos abriendo conexión nueva por each message (usar ORM cache)
- Benchmark: medir tiempo de insert + query 1000 mensajes

**Criterios de aceptación:**
- Índices creados y aplicados
- Timings documentados
- Política de archivos/limpieza definida
- 1000 inserts < 5 segundos en SQLite (o <1s con PostgreSQL)

---

### Tarea 3.3: Optimizar WebSocket para reducir overhead de red y CPU
**Descripción:**
- Revisar payloads JSON enviados en `chat_message` event (consumers.py):
  - ¿Puedo comprimirlos? (room + alias + message + timestamp = ~100 bytes ahora, está OK)
  - ¿Necesito enviar room en cada mensaje si ya está en grupo? Optimización: omitir si es redundante
- Implementar heartbeat/ping para detectar desconexiones stale
- Throttling: limitar broadcast si hay spam (ej: máx 1 mensaje/500ms por usuario)
- Monitoreo: agregar logging de consumo de memoria del consumer

**Criterios de aceptación:**
- Payload JSON minimizado
- Tests de carga: 10 usuarios x 5 mensajes/seg durante 1 minuto
- Memoria stable (no crece)
- CPU < 15% en VM de test

---

### Tarea 3.4: Implementar presencia de usuarios en salas (opcional pero recomendado)
**Descripción:**
- Cuando usuario conecta/desconecta a WebSocket:
  - Broadcast evento `user_joined` / `user_left` (sin guardar en BD, solo evento en tiempo real)
  - Cliente muestra: "usuario X entró a la sala", "usuario X salió"
  - Mostrar lista de usuarios activos en tiempo real en sidebar
  - Timeout automático: si no hay ping en 30s, marcar como offline
- Payload: `{event: 'user_joined', user: 'alias', timestamp}`

**Criterios de aceptación:**
- Presencia mostrando en tiempo real
- Desconexiones detectadas
- No impacta performance del chat

---

### Tarea 3.5: Tests exhaustivos del chat de texto
**Descripción:**
- Ampliar `tests.py` actual con:
  - Test historial loading (API GET /api/rooms/...)
  - Test infinit scroll paginación
  - Test de múltiples usuarios simultáneos (5+) enviando mensajes
  - Test de reconexión WebSocket (enviar mensaje, reconectar, recibir pendientes)
  - Test de límites: alias muy largo, mensaje muy largo, caracteres especiales/emojis
  - Test de edge cases: sala no existe, usuario baneado (futuro), permisos
  - Tests de carga: 100 mensajes/segundo durante 10 segundos
- Documentar timings esperados y máximos

**Criterios de aceptación:**
- Cobertura >80% en chat/consumers.py y chat/views.py
- Tests pasando
- Documentación de performance baselines

---

### Tarea 3.6: Crear API REST para historial y salas (opcional pero escalable)
**Descripción:**
- Crear endpoints Django REST framework:
  - `GET /api/rooms/` - listar todas las salas
  - `GET /api/rooms/<id>/` - detalle de sala
  - `GET /api/rooms/<id>/messages/?limit=30&offset=0` - historial paginado
  - `POST /api/rooms/` - crear sala (requiere auth)
  - `DELETE /api/rooms/<id>/` - eliminar sala (requiere ownership)
- Implementar throttling por usuario: 100 requests/minuto
- Caché: mensajes cached 5 minutos para evitar queries repetidas
- Serializar con `rest_framework.serializers` para validación automática

**Criterios de aceptación:**
- Endpoints documentados en Swagger (swagger-ui auto)
- Funcionales y testeados
- Throttling actuando
- Cache mejorando timings

---

### Tarea 3.7: Optimización de base de datos y despliegue
**Descripción:**
- **Desarrollo:** SQLite OK temporalmente
- **Producción:** migrar a PostgreSQL (solo si escala lo requiere)
- Conexión pooling: usar `django-db-conn-pool` para evitar abrir conexión nueva por request
- Backups: implementar script de backup automático (rsync o pg_dump)
- Monitoreo: agregar logging de query times lentos (`django-waffle` o `django-silk`)
- Variables de entorno: archivo `.env` nunca en git, ejemplo `.env.example` sí

**Criterios de aceptación:**
- DB en PostgreSQL (local o Docker)
- Connection pooling configurado
- Backups automated
- Logging de slow queries activo

---

### Tarea 3.8: Documentación técnica del chat
**Descripción:**
- Actualizar README con:
  - Arquitectura de datos (diagrama ER simple)
  - Flujo WebSocket y REST API
  - Performance expectations (latencia típica, máximo usuarios recomendados por sala)
  - Troubleshooting: "¿Por qué se desconecta?" "¿Por qué lag?"
- Documentar en código: docstrings en `consumers.py`, `models.py`, `views.py`
- Crear `API.md` con ejemplos de curl para cada endpoint REST

**Criterios de aceptación:**
- README completo e actualizado
- Código comentado
- API.md con ejemplos funcionales

---

## 📊 RESUMEN DE PRIORIDADES

### MVP ("funciona y es usable"):
1. **Compañero 1:** Tareas 1.1, 1.2
2. **Compañero 2:** Tareas 2.1, 2.2, 2.3
3. **Tú:** Tareas 3.1, 3.2, 3.5

### Post-MVP ("escalable y pulido"):
1. **Compañero 1:** Tareas 1.3, 1.4
2. **Compañero 2:** Tareas 2.4, 2.5
3. **Tú:** Tareas 3.3, 3.4, 3.6, 3.7, 3.8

---

## 🎯 CONSEJOS PARA OPTIMIZACIÓN DE RECURSOS

### Reducir CPU:
- Evitar loops en Python durante WebSocket broadcast (Channels maneja threading)
- Usar `select_related()` en queries Django
- Cachear resultados frecuentes (salas, usuarios)

### Reducir RAM:
- Limitar historial en memoria a últimos 50 mensajes por sala
- Usar generadores en lugar de listas donde sea posible
- Connection pooling (5-10 conexiones DB, no 100)

### Reducir ancho de banda:
- JSON comprimido (gzip middleware)
- Pagination (nunca cargar 10,000 mensajes)
- Caché en cliente (localStorage para salas, mensajes)
- Diferencial updates: enviar solo cambios, no estado completo

### Reducir latencia:
- Redis para Channels layer (mejor que InMemory para múltiples workers)
- Índices en BD
- CDN para assets estáticos (CSS, JS, si es posible)

