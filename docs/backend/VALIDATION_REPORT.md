# Informe de validación del backend — With You MVP v1.0

**Corte:** 30 de octubre de 2026  
**Alcance:** backend académico FastAPI y artefactos reproducibles de laboratorio.

## Resultado ejecutado en este entorno

- Compilación Python (`compileall`): **OK**.
- Pytest: **17/17 pruebas aprobadas**.
- Cobertura del paquete `app`: **79 %**.
- OpenAPI: **60 rutas / 70 operaciones HTTP**.
- Colección Postman: **70 solicitudes**, sin operaciones faltantes respecto al OpenAPI.
- `docker-compose.yml`: **parseo YAML correcto**, con 7 servicios (`db`, `redis`, `api1`, `api2`, `worker`, `beat`, `nginx`).
- Alembic baseline: **upgrade probado correctamente sobre SQLite temporal**, creando 20 tablas de dominio + `alembic_version`.

## Flujos funcionales automatizados cubiertos

1. Registro, login, access token, refresh rotatorio y perfil.
2. Restricción de eventos TEST a TESTER/ADMIN.
3. Ocultamiento de eventos TEST para usuarios normales.
4. Trusted Circle y aceptación.
5. Checkpoint cifrado y acceso contextual.
6. Quórum N-de-M antes de liberar ubicación en solicitud familiar.
7. Filtro sísmico por magnitud/relevancia y correlación de evento.
8. Respuesta `SAFE` y notificación a contactos.
9. Timeout a `NO_RESPONSE` sin inferir desaparición/secuestro/muerte/peligro.
10. TTL deslizante: solo se elimina el checkpoint vencido.
11. SOS y grants temporales de ubicación.
12. Personal Safety Mode y escalamiento a caso ciudadano tras verificación.
13. Participación comunitaria con opt-in y múltiples confirmaciones.
14. Directorio limitado a sujetos autorizados.
15. Perfil NNA sintético: sin participación comunitaria y sin auto-targeting.
16. Revocación de grants de ubicación.
17. Cierre de Welfare Check limitado al sujeto o solicitante original.
18. Normalización de fixture SGC.

## Validación condicionada fuera de este entorno

No se afirma como validado aquí aquello que requiere infraestructura o credenciales externas:

- ejecución real de Docker Compose/HA local, porque Docker no está disponible en este runtime;
- FCM real, porque requiere proyecto y credenciales Firebase;
- SMS real, porque requiere proveedor y credenciales;
- SGC/IDEAM en vivo, porque el endpoint/capa debe validarse en el entorno de ejecución y la búsqueda web de esta sesión no está disponible;
- P2P/DTN, porque corresponde al cliente móvil y dispositivos físicos;
- SIRDEC/Alerta Rosa/Fiscalía/Policía operacional, porque requiere autorización institucional;
- multi-región real, porque se conserva como arquitectura objetivo y prueba de simulación, no despliegue del MVP.

## Criterio de cierre

El backend queda **cerrado para el MVP académico** en cuanto a lógica interna, contratos, persistencia, seguridad contextual, simuladores, auditoría, workers y pruebas. Las piezas anteriores no son lógica faltante: son integraciones externas o pruebas de infraestructura que deben ejecutarse en el equipo/laboratorio del proyecto.
