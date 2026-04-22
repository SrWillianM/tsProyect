# tsProject - MVP Chat en Tiempo Real

Base de backend para clon tipo TeamSpeak usando Django + Channels.

## Requisitos

- Python 3.13+
- Docker (para Redis)

## Instalación

1. Abrir una terminal en la raíz del proyecto.
2. Crear el entorno virtual:

```powershell
py -3 -m venv .venv
```

3. Activar el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si usas CMD:

```bat
.\.venv\Scripts\activate.bat
```

4. Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

5. Instalar y activar pre-commit para que los checks de estilo y análisis estático se ejecuten antes de cada commit:

```bash
python -m pip install pre-commit
pre-commit install
```

6. Validar todo el repositorio antes del primer commit o después de cambiar reglas:

```bash
pre-commit run --all-files
```

7. Levantar Redis (recomendado para trabajo grupal):

```bash
docker compose up -d redis
```

Si no tienes Docker en tu máquina, puedes usar fallback local en memoria:

```powershell
$env:USE_INMEMORY_CHANNEL_LAYER="1"
```

8. Migrar base de datos:

```bash
python manage.py makemigrations
python manage.py migrate
```

9. Crear usuario admin:

```bash
python manage.py createsuperuser
```

10. Ejecutar servidor:

```bash
python manage.py runserver
```

## Calidad obligatoria con Git Hooks

El repositorio usa pre-commit para bloquear commits que no cumplan el estilo PEP 8 o que contengan errores estáticos detectables por Flake8.

Configuración activa:

- Black: formateo automático con ancho de línea de 88 caracteres.
- Flake8: verificación de errores y advertencias de estilo compatibles con Black.
- Exclusiones: archivos generados por Django en `*/migrations/*` y entornos virtuales como `.venv/`, `venv/` y `env/`.

Flujo recomendado para cada integrante:

1. Instalar dependencias del proyecto.
2. Activar el entorno virtual local antes de instalar dependencias.
3. Instalar pre-commit con `python -m pip install pre-commit`.
4. Activar los hooks con `pre-commit install`.
5. Dejar que el hook bloquee el commit si hay problemas.

### Verificación de bloqueo

Para comprobar que el sistema realmente bloquea un commit, introduce temporalmente uno de estos errores en un archivo Python versionado:

- una importación no utilizada, por ejemplo `import os` si no se usa;
- una línea que rompa el formato de Black;
- una línea demasiado larga o un problema de estilo detectado por Flake8.

Luego ejecuta `git add .` y `git commit -m "prueba"`.

El commit debe fallar y mostrar la salida del hook correspondiente hasta que el código quede corregido o formateado.

## Instalacion simple para otra PC (misma red)

Si quieres pasar el proyecto a otra PC de tu misma red WiFi/LAN y que instalen facil:

1. Copiar la carpeta del proyecto completa en la PC destino.
2. Ejecutar `instalar_lan.bat`.
3. (Opcional) Ejecutar `crear_admin.bat`.
4. Ejecutar `iniciar_lan.bat`.

Guia rapida: `INSTALACION_SIMPLE_LAN.md`

### Crear ZIP listo para compartir

Para generar un paquete limpio para otra PC (sin `.venv`, sin `__pycache__`, sin `.git`, sin `db.sqlite3`):

1. Ejecutar `empaquetar_lan.bat`
2. El archivo se crea en la carpeta `dist/` con nombre tipo:
	- `tsProject-lan-YYYYMMDD-HHMMSS.zip`

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
