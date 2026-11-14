# With You — Backend MVP v1.0

**Fecha:** 30 de octubre de 2026  
**Estado:** cerrado para MVP académico / laboratorio.

## Incluido

- FastAPI modular, PostgreSQL/PostGIS, Redis/Celery y Nginx.
- Auth Argon2 + JWT de acceso + refresh rotatorio.
- Device registry y soporte para push token.
- Trusted Circle, permisos y revocación.
- Consent/Policy Engine y quórum N-de-M.
- Emergency Location Vault cifrado, TTL móvil por registro e incident hold.
- Grants temporales de ubicación COARSE/EXACT y trazabilidad de acceso.
- Eventos multiamenaza TEST y adapter SGC configurable.
- Filtro sísmico contextual por magnitud, edad, distancia/vigencia.
- Safety Check, SAFE, HELP_REQUIRED, UNABLE_TO_EXIT y NO_RESPONSE.
- SOS explícito y Personal Safety Mode.
- Welfare Check familiar y comunidad con opt-in/progressive disclosure.
- Casos ciudadanos separados de referencias institucionales.
- SIRDEC Open Data + referencia SICLICO, sin bypass de CAPTCHA.
- Auditoría, métricas y registro de experimentos.
- Workers de mantenimiento, expiración y notificaciones.
- Alembic baseline y bootstrap automático solo para DEV/TEST.
- OpenAPI y colección Postman sincronizados.
- 17 pruebas automatizadas; cobertura actual 79 %.

## Reglas de seguridad cerradas

- Un usuario normal no crea ni lista eventos TEST.
- `can_view_checkpoint` no equivale a lectura permanente; se requiere grant contextual vigente.
- Una solicitud familiar no revela ubicación antes del quórum cuando la política lo exige.
- `NO_RESPONSE` nunca produce automáticamente MISSING/KIDNAPPED/DEAD/IN_DANGER.
- Cada checkpoint expira de forma individual; no existe borrado masivo diario.
- Un contacto de confianza que no sea sujeto ni solicitante original no puede cerrar unilateralmente el Welfare Check.
- Perfil NNA sintético sin comunidad ni auto-targeting.
- Caso ciudadano no equivale a denuncia, MBU, Alerta Rosa ni registro SIRDEC.

## Requiere ejecución externa

- Docker Compose end-to-end en el equipo del proyecto.
- Credenciales FCM para push real.
- Proveedor/credenciales para SMS real.
- Validación en vivo del endpoint/capa SGC e IDEAM configurado.
- P2P/DTN en dispositivos físicos desde Flutter.
- Integraciones operacionales con entidades, sujetas a autorización.
- Multi-región real, fuera del MVP académico.
