# API Chat

## Endpoints

### Listar salas
```bash
curl -X GET http://127.0.0.1:8000/api/rooms/
```

### Crear sala (requiere sesion autenticada)
```bash
curl -X POST http://127.0.0.1:8000/api/rooms/ \
  -H "Content-Type: application/json" \
  -d '{"name":"General"}'
```

### Ver detalle de sala por id
```bash
curl -X GET http://127.0.0.1:8000/api/rooms/1/
```

### Eliminar sala por id (owner o superuser)
```bash
curl -X DELETE http://127.0.0.1:8000/api/rooms/1/
```

### Historial paginado por nombre de sala
```bash
curl -X GET "http://127.0.0.1:8000/api/rooms/General/messages/?limit=30&offset=0"
```

## WebSocket

### URL
`ws://127.0.0.1:8000/ws/chat/<room_name>/?alias=<alias>`

### Cliente -> servidor
```json
{"event":"ping"}
```

```json
{"alias":"Will","message":"Hola equipo"}
```

### Servidor -> cliente
```json
{"event":"pong","timestamp":"2026-01-01T10:00:00+00:00"}
```

```json
{"event":"message","id":12,"alias":"Will","message":"Hola equipo","timestamp":"...","source":"live"}
```

```json
{"event":"presence_snapshot","users":["Ana","Luis"],"timestamp":"..."}
```

```json
{"event":"user_joined","alias":"Ana","timestamp":"..."}
```

```json
{"event":"user_left","alias":"Ana","timestamp":"..."}
```

```json
{"event":"throttled","detail":"Max 1 message every 500ms"}
```

## Comandos utilitarios

### Limpiar mensajes viejos
```bash
python manage.py prune_messages --days 30
```

### Benchmark rapido
```bash
python manage.py benchmark_messages --count 1000 --room Benchmark
```
