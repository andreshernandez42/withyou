# With You — MVP académico

Plataforma móvil resiliente para verificación de bienestar, localización mínima y coordinación controlada de ayuda.

## Estado del paquete

Este paquete contiene el **backend MVP v1.0**, el mini frontend Flutter existente, PostgreSQL/PostGIS, Redis/Celery, Nginx para balanceo local, simulador multiamenaza, adaptadores SGC/SIRDEC/IDEAM, colección Postman y pruebas automatizadas.

La separación conceptual se mantiene:

- un caso creado en la app **no es** una denuncia, MBU, Alerta Rosa ni registro SIRDEC;
- `NO_RESPONSE` significa únicamente **estado no confirmado**;
- los eventos TEST siempre se marcan como simulación;
- la ubicación exacta no se libera por pertenecer al Trusted Circle: requiere un **grant contextual temporal** derivado de SOS, respuesta de ayuda, evento preautorizado o quórum;
- cada checkpoint tiene TTL individual de 24 h; no existe borrado masivo diario;
- NNA se maneja solo como perfil sintético/restringido en el MVP.

## Inicio rápido con Docker

1. Instalar Docker Desktop.
2. Copiar `.env.demo` a `.env` si desea modificar parámetros del laboratorio.
3. Ejecutar:

```bash
docker compose --env-file .env.demo up -d --build
```

4. Crear datos demo:

```bash
docker compose --env-file .env.demo exec api1 python -m app.seed
```

5. Abrir `http://localhost:8000/docs`.

Credenciales demo: ver `LOCAL_DEMO_CREDENTIALS.txt`.

## Pruebas sin Docker

Desde `backend/`:

```bash
pytest -q
```

La batería incluida cubre autenticación, roles TEST, quórum, grants de ubicación, filtros de magnitud, Safety Check, TTL deslizante, SOS, Personal Safety, casos ciudadanos, verificación comunitaria y NNA sintético.

## Frontend

El mini frontend Flutter se conserva en `mobile/`. La URL por defecto es:

- emulador Android: `http://10.0.2.2:8000/api/v1`
- dispositivo físico: `http://<IP-LAN-PC>:8000/api/v1`

No se debe exponer el entorno demo directamente a Internet.

## Dependencias externas

El backend queda cerrado a nivel de lógica de MVP. Estas capacidades dependen de servicios/credenciales externas reales:

- Firebase Cloud Messaging: código soportado, requiere proyecto/credenciales.
- SGC ArcGIS: adapter configurable; validar endpoint/capa en el entorno de ejecución.
- IDEAM/FEWS: adapter configurable; no se inventa un endpoint estable.
- SIRDEC operacional/Fiscalía/Policía/Alerta Rosa: no hay integración privilegiada; se usa Open Data/portal oficial y contratos simulados.
- P2P/DTN: pertenece principalmente al cliente móvil y sigue experimental.

## Cierre y evidencia del backend

- Contrato API: `docs/backend/API_CONTRACT.md`
- Integración Flutter: `docs/backend/FRONTEND_INTEGRATION.md`
- Estado de cierre: `docs/backend/BACKEND_STATUS.md`
- Informe de validación: `docs/backend/VALIDATION_REPORT.md`
- Migraciones: `docs/backend/MIGRATIONS.md`
- OpenAPI: `docs/openapi.json`
- Postman: `postman/WithYou_Backend_MVP_v1.postman_collection.json`
- Cobertura: `docs/coverage_summary.txt` y `docs/coverage.xml`
