# 🎙️ GUÍA: Conectarse al Chat de Voz desde otra PC

Esta es la guía paso-a-paso para que **Will (server)** y **Amigo (client)** se conecten a voz en 2 PCs diferentes.

---

## ✅ Paso 0: Pre-requisitos

Antes de empezar, verifica que tienes:

- ✅ Redis corriendo
- ✅ Django configurado para aceptar conexiones externas
- ✅ Ambas PCs en la misma red (WiFi/LAN)
- ✅ Navegadores modernos (Chrome, Firefox, Edge)
- ✅ Micrófono conectado en ambas PCs

Si cada uno está en su casa (redes distintas), además necesitas:

- ✅ Servidor accesible por internet (dominio o IP pública)
- ✅ HTTPS activo (certificado TLS)
- ✅ TURN server (sin TURN puede fallar por NAT)

---

## 🖥️ PASO 1: Configurar PC del Servidor (Will)

### 1.1 - Permitir conexiones desde otras PCs

Editar `tsProject/settings.py`:

```python
# Buscar esta línea (alrededor de línea 33):
ALLOWED_HOSTS = []

# CAMBIAR A:
ALLOWED_HOSTS = ['*']  # Solo para desarrollo, NO en producción
```

**O hacerlo por ambiente:**
```bash
export ALLOWED_HOSTS='*'
# Luego iniciar servidor
python manage.py runserver 0.0.0.0:8000
```

Guardar el archivo.

### 1.1.1 - Configuración recomendada para internet (casas distintas)

En variables de entorno del servidor:

```powershell
$env:ALLOWED_HOSTS="tu-dominio.com,tu-ip-publica"
$env:WEBRTC_TURN_URL="turn:tu-turn-server.com:3478"
$env:WEBRTC_TURN_USERNAME="usuario_turn"
$env:WEBRTC_TURN_CREDENTIAL="password_turn"
```

Con eso el frontend tomará STUN + TURN automáticamente.

### 1.2 - Iniciar Redis (para presencia centralizada)

```bash
# En una terminal:
docker compose up -d redis

# Verificar:
docker compose ps  # Debería ver redis en estado "running"
```

### 1.3 - Iniciar Django

```bash
# En otra terminal (en la carpeta del proyecto):
cd c:/Users/Will/tsProject
python manage.py runserver 0.0.0.0:8000
```

Debería ver:
```
Starting development server at http://0.0.0.0:8000/
Django version 6.0.3, using settings 'tsProject.settings'
```

---

## 💻 PASO 2: Obtener IP del Servidor

Necesitamos saber la IP del servidor para que el cliente se conecte.

### En Windows (PC del Servidor):

```bash
ipconfig
```

Buscar la línea con "IPv4 Address" en la tarjeta de red (ej: `192.168.1.100`):

```
Ethernet adapter Ethernet:
   Connection-specific DNS Suffix . :
   IPv4 Address . . . . . . . . . . . : 192.168.1.100  ← ESTA ES LA IP
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
```

**Apunta esta IP → La necesitarás en el paso 3**

### En PC del Cliente, verificar que ve la IP:

```bash
ping 192.168.1.100
```

Si responde, están conectados en la red.

---

## 📱 PASO 3: Cliente se Conecta (Amigo)

Desde la **PC del Amigo** (cliente):

1. Abrir navegador (Chrome, Firefox, Edge)
2. Navegar a: **`http://192.168.1.100:8000`**
   - Reemplazar `192.168.1.100` con la IP del Paso 2
3. Debería ver la página del chat

---

## 🎤 PASO 4: Ambos Entran en la Misma Sala

**PC del Servidor (Will):**
- Ingresar nombre: `Will`
- Sala: `test` (o el nombre que prefieras)
- Click: "Entrar a la sala"

**PC del Cliente (Amigo):**
- Ingresar nombre: `Amigo`
- Sala: `test` (¡MISMO NOMBRE!)
- Click: "Entrar a la sala"

Ambos deberían ver "Chat de prueba" con la lista de usuarios.

---

## 📞 PASO 5: Conectar el Chat de Voz

Ambas PCs:

1. Click en botón **"🎤 Conectar Voz"**
2. El navegador pedirá permiso para acceder al micrófono
3. Click: **"Permitir"**
4. Esperar 2-3 segundos (está negociando P2P)

**Debería ver:**
- ✅ Lista de usuarios en voz (PC1, PC2)
- ✅ Botón de mute/unmute disponible
- ✅ Indicador de conexión (verde si conectó)

---

## 🔊 PASO 6: Probar Audio

**PC1 (Will):**
- Habla con micrófono
- PC2 debería escuchar

**PC2 (Amigo):**
- Habla con micrófono
- PC1 debería escuchar

Si escuchan mutuamente, ✅ **¡Funcionó!**

---

## ❌ TROUBLESHOOTING

### ❌ "Estoy en otra casa y no conecta voz"

**Causa más común:** falta HTTPS y/o TURN.

**Qué verificar:**

1. El sitio abre como `https://...` (no `http://...`)
2. Existe TURN configurado (`WEBRTC_TURN_URL`, `WEBRTC_TURN_USERNAME`, `WEBRTC_TURN_CREDENTIAL`)
3. El servidor está publicado a internet (dominio o IP pública)
4. Firewall permite puertos del TURN server

Sin esas 4 condiciones, entre casas suele fallar por NAT.

---

### ❌ "No se puede conectar a 192.168.x.x:8000"

**Posible causa:** `ALLOWED_HOSTS` no configurado

**Solución:**
```python
# Editar tsProject/settings.py
ALLOWED_HOSTS = ['*']
```

Reiniciar Django.

---

### ❌ "Conectar Voz" pero no hay usuario en la lista

**Posible causa:** Redis no está corriendo

**Solución:**
```bash
docker compose up -d redis
docker compose logs redis  # Ver logs
```

Reiniciar Django.

---

### ❌ No se escucha audio (WebRTC no conecta)

**Posible causa:**

1. **Firewall bloqueando puertos**
   - Abrir firewall de Windows
   - Permitir puertos UDP (WebRTC usa UDP para P2P)

2. **NAT simétrico (ambos tras router diferente)**
   - Solución: Implementar TURN server (paso avanzado)
   - Por ahora: Probar con ambas PCs en LAN del mismo router

3. **Navegador no actualizado**
   - Actualizar a última versión Chrome/Firefox

4. **Permiso de micrófono denegado**
   - Ir a configuración del navegador
   - Permitir micrófono para este sitio

---

### ❌ "Usuario desconectado" pero sigue en lista

**Posible causa:** Presencia stale en Redis

**Solución:**
```bash
# En terminal, conectarse a Redis:
redis-cli
> SELECT 1
> KEYS voice_presence:*
> DEL voice_presence:test  # Limpiar esa sala
> EXIT
```

---

## 📝 Notas de Producción

⚠️ **SOLO PARA DESARROLLO:**

```python
ALLOWED_HOSTS = ['*']  # NUNCA en producción
```

**Para Producción:**

1. Fijar ALLOWED_HOSTS a IPs específicas:
   ```python
   ALLOWED_HOSTS = ['192.168.1.100', 'meuservidor.com']
   ```

2. Usar HTTPS (WebRTC con certificado)

3. Implementar TURN server si clientes están en redes diferentes (casas distintas)

4. Autenticación de usuarios (no anónimos)

---

## ✅ Checklist Final

- [ ] Redis corriendo (`docker compose ps` muestra redis)
- [ ] Django acepta conexiones externas (`ALLOWED_HOSTS = ['*']`)
- [ ] Django corriendo en `0.0.0.0:8000`
- [ ] Cliente puede hacer ping al servidor
- [ ] Ambos en la misma sala de chat
- [ ] Ambos clicaron "Conectar Voz"
- [ ] Ambos dieron permiso de micrófono
- [ ] Audio fluye en ambas direcciones

Para redes distintas (casas):

- [ ] Sitio abierto por HTTPS
- [ ] TURN configurado por variables de entorno
- [ ] Dominio/IP pública accesible desde internet

**¡Si todo está así, tu chat de voz 2-PC está funcionando! 🎉**

---

## 🆘 Si sigue sin funcionar

1. Ver logs de Django:
   ```
   Abrir terminal donde corre Django
   Buscar líneas con "[VoiceSignaling]" o "ERROR"
   ```

2. Ver estado de Redis:
   ```bash
   docker compose logs -f redis
   ```

3. Abrir Developer Tools en navegador (F12):
   - Ir a "Console"
   - Buscar errores de WebRTC o WebSocket
   - Si hay error, copiar y compartir

