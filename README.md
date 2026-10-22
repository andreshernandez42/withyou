# With You - Plataforma Resiliente (MVP académico)

Paquete integral del Trabajo de Grado: anteproyecto, backend, esquema de base de datos, aplicación móvil Flutter, mockups, diagramas, colección Postman, OpenAPI, documentación técnica y scripts de arranque.

## Qué funciona en el MVP

- Registro/login con token firmado y contraseñas Argon2.
- Trusted Circle con invitación/aceptación y permisos.
- Consent Policy con quórum N-de-M.
- Emergency Location Vault con coordenadas exactas cifradas, TTL individual de 24 h y `incident_hold` temporal.
- Checkpoints desde móvil.
- Motor multiamenaza con eventos `TEST` (sismo, deslizamiento, inundación, incendio).
- Filtro sísmico configurable por magnitud y distancia.
- Safety Check automático para usuarios dentro del área relevante.
- Estados `SAFE`, `HELP_REQUIRED`, `UNABLE_TO_EXIT`, `CHECK_REQUESTED`, `NO_RESPONSE`/quórum, sin inferir secuestro o desaparición por silencio.
- Solicitud familiar de Welfare Check y quórum del círculo de confianza.
- Caso de verificación de paradero separado de una denuncia oficial.
- Referencia institucional asociable a un caso.
- Personal Safety Mode para vulnerabilidad inmediata.
- Auditoría de accesos y eventos sensibles.
- Integración read-only con SIRDEC/Datos Abiertos mediante SODA.
- Link seguro a consulta pública SICLICO (no automatiza CAPTCHA).
- Adapter SGC ArcGIS configurable y sincronización de sismos.
- Adapter IDEAM configurable; si no hay endpoint oficial estable configurado se usa el simulador multiamenaza.
- App Flutter con login, pantalla principal, alerta tipo mockup, círculo de confianza, solicitudes, fuentes y modo de seguridad.
- OpenAPI y colección Postman.

## Qué NO se afirma como implementado en producción

- Acceso operacional privilegiado a SIRDEC, Fiscalía, Policía o Alerta Rosa.
- Activación automática de MBU o denuncia oficial.
- Integración con operadores, Cell Broadcast o satélite.
- FCM/SMS productivo sin credenciales propias del usuario.
- Mesh universal Android+iOS.
- Despliegue multi-región real. La arquitectura y pruebas se documentan; el MVP corre localmente.

## Arranque rápido con Docker

1. Instala Docker Desktop.
2. Copia `.env.demo` a `.env`.
3. Ejecuta `scripts/start_demo.ps1` (Windows) o `scripts/start_demo.sh` (Linux/macOS).
4. Abre Swagger: `http://localhost:8000/docs`.
5. Importa `postman/WithYou_MVP.postman_collection.json` si deseas probar API.
6. Para el móvil, revisa `mobile/README.md`.

## Validación incluida

El backend incluye pruebas automatizadas del flujo central y adaptador SGC. Se validaron localmente sin acceso web externo: autenticación, Trusted Circle, checkpoint, bloqueo de acceso no autorizado, evento sísmico de prueba, check-in, notificaciones, quórum 2-de-3, caso de verificación, referencia institucional, Personal Safety Mode y TTL deslizante.

Las llamadas en vivo a SGC/SIRDEC están configuradas pero deben validarse desde un entorno con Internet, ya que el entorno de construcción de este paquete no tenía búsqueda web habilitada.
