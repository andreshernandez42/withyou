# Contrato API — Backend MVP v1.0

Base: `/api/v1`

| Dominio | Rutas principales | Regla clave |
|---|---|---|
| Auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | access token corto + refresh rotatorio |
| Perfil/dispositivos | `/me`, `/devices`, `/authorized-subjects` | móvil nunca accede directamente a BD |
| Trusted Circle | `/trusted-contacts*` | invitación, aceptación, permisos, revocación |
| Consentimiento | `/policies*` | quórum, comunidad, exactitud, TTL de acceso |
| Vault | `/checkpoints*` | ubicación cifrada, TTL individual, incident hold |
| Eventos | `/events`, `/test/emergency-events`, `/events/sync/sgc` | TEST solo TESTER/ADMIN; filtro contextual |
| Safety | `/safety/pending`, `/safety/respond`, `/sos*` | `NO_RESPONSE` no infiere desaparición |
| Welfare | `/welfare-checks*` | quórum antes de liberar ubicación en flujo familiar |
| Comunidad | `/community/welfare-checks/nearby` | zona aproximada + opt-in adulto |
| Casos | `/cases*` | caso ciudadano separado de referencia institucional |
| Personal Safety | `/personal-safety*` | vulnerabilidad inmediata; no acusa terceros |
| SIRDEC/IDEAM | `/official/*` | read-only / referencia oficial |
| Privacidad | `/privacy/location-grants`, `/privacy/access-history` | transparencia y revocación |
| Auditoría/experimentos | `/audit-logs`, `/experiments/runs`, `/metrics/summary` | TESTER/ADMIN |

El contrato completo se encuentra en `docs/openapi.json` y en la colección Postman.

## Salud del servicio

- `GET /api/v1/health`: compatibilidad y estado básico de la API.
- `GET /api/v1/health/live`: liveness; comprueba que el proceso responde.
- `GET /api/v1/health/ready`: readiness; comprueba acceso al source of truth mediante `SELECT 1`.

## Persistencia

En DEV/TEST puede usarse bootstrap automático. Para un entorno persistente el esquema se versiona con Alembic y `AUTO_CREATE_SCHEMA=false`.
