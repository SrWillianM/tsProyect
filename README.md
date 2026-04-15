# tsProject - MVP Chat en Tiempo Real

Base de backend para clon tipo TeamSpeak usando Django + Channels.

## Requisitos

- Python 3.13+
- Docker (para Redis)

## Instalación

1. Crear y activar entorno virtual.
2. Instalar dependencias:

```bash
c:/Users/Will/tsProject/.venv/Scripts/python.exe -m pip install -r requirements.txt
```

3. Levantar Redis (recomendado para trabajo grupal):

```bash
docker compose up -d redis
```

Si no tienes Docker en tu máquina, puedes usar fallback local en memoria:

```powershell
$env:USE_INMEMORY_CHANNEL_LAYER="1"
```

4. Migrar base de datos:

```bash
c:/Users/Will/tsProject/.venv/Scripts/python.exe manage.py makemigrations
c:/Users/Will/tsProject/.venv/Scripts/python.exe manage.py migrate
```

5. Crear usuario admin:

```bash
c:/Users/Will/tsProject/.venv/Scripts/python.exe manage.py createsuperuser
```

6. Ejecutar servidor:

```bash
c:/Users/Will/tsProject/.venv/Scripts/python.exe manage.py runserver
```

## Flujo de prueba rápida

1. Entrar a `/admin` y crear salas en el modelo Room.
2. Abrir `http://127.0.0.1:8000/` en dos pestañas.
3. Entrar a la misma sala en ambas pestañas.
4. Enviar mensajes y confirmar recepción en tiempo real.

## Chat Optimizado (implementado)

- Historial paginado por API: `GET /api/rooms/<room>/messages/?limit=30&offset=0`
- Carga lazy + infinite scroll al subir en la sala
- Prevención de duplicados entre historial (`source=history`) y tiempo real (`source=live`)
- WebSocket con eventos de presencia (`presence_snapshot`, `user_joined`, `user_left`)
- Heartbeat `ping/pong` para detectar conexiones stale
- Throttling por conexión: máximo 1 mensaje cada 500ms
- Índices de BD en `Message(room, timestamp)` y `Message(timestamp)`

## API y utilidades

- Documentación de endpoints y eventos WebSocket: `API.md`
- Limpieza de mensajes viejos: `python manage.py prune_messages --days 30`
- Benchmark insert/query: `python manage.py benchmark_messages --count 1000 --room Benchmark`

## Estructura principal

- `tsProject/settings.py`: configuración de Django + Channels.
- `tsProject/asgi.py`: enruta HTTP y WebSocket.
- `chat/models.py`: Room y Message.
- `chat/consumers.py`: ChatConsumer con persistencia de mensajes.
- `chat/routing.py`: rutas WebSocket.
- `chat/templates/chat/`: vistas HTML para pruebas de integración.

## Tareas pendientes

Ver [`TAREAS_TRELLO.md`](./TAREAS_TRELLO.md) para:
- **Compañero 1** (Audio/WebRTC): Chat de voz, integración WebRTC, signaling, pruebas (8 tareas)
- **Compañero 2** (Frontend/Auth): Login, gestión de salas, UI mejorada, perfil (5 tareas)
- **Tu parte** (Backend optimizado): Historial lazy-load, optimización BD/WebSocket, tests, API REST, despliegue (8 tareas)

Todas incluyen descripción detallada, criterios de aceptación y tips de optimización de recursos.
