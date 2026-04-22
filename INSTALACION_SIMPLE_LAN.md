# Instalacion Simple (Misma Red WiFi/LAN)

Objetivo: pasar este proyecto a otra PC y que lo levanten facil con doble clic.

## En la PC destino

1. Instalar Python 3.13+ (activar opcion Add Python to PATH).
2. Copiar esta carpeta del proyecto completa.
3. Doble clic en [instalar_lan.bat](instalar_lan.bat).
4. (Opcional) Doble clic en [crear_admin.bat](crear_admin.bat).
5. Doble clic en [iniciar_lan.bat](iniciar_lan.bat).

## Como entrar desde otra PC de la misma red

- En la consola de inicio veras algo como:
  - URL local: `http://127.0.0.1:8000`
  - URL en red: `http://192.168.x.x:8000`
- En la otra PC, abrir la URL en red.

## Modo simple incluido

- `iniciar_lan.bat` usa `USE_INMEMORY_CHANNEL_LAYER=1`.
- Esto evita depender de Redis para una instalacion rapida.
- Ideal para demo en red local.

## Nota para chat de voz

- El chat de voz puede requerir Redis para presencia y mas estabilidad.
- Para solo chat de texto en LAN, este instalador simple funciona bien.

## Si Windows bloquea firewall

Permitir Python/Django en red privada cuando lo pida Windows Defender Firewall.
