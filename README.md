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

## Estructura principal

- `tsProject/settings.py`: configuración de Django + Channels.
- `tsProject/asgi.py`: enruta HTTP y WebSocket.
- `chat/models.py`: Room y Message.
- `chat/consumers.py`: ChatConsumer con persistencia de mensajes.
- `chat/routing.py`: rutas WebSocket.
- `chat/templates/chat/`: vistas HTML para pruebas de integración.
