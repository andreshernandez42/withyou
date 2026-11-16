# Reporte de validación — WithYou / Sismos

**Fecha de revisión:** 2026-11-15. **Base:** `withyou(1).zip` (complementado con `Plataforma_Resiliente_MVP(1).zip` como referencia histórica).

## Ejecución verificada en este entorno

Comando ejecutado en `backend/`:

```bash
pytest -q tests --disable-warnings
pytest --cov=app --cov-report=term-missing:skip-covered -q tests --disable-warnings
```

**23 pruebas aprobadas, 0 fallidas; cobertura global del backend: 78 %.** Pruebas realizadas sin red pública y sobre base SQLite efímera. Se verificaron los siguientes comportamientos:

- Auth JWT/refresh, rutas protegidas, roles y políticas.
- Checkpoints cifrados, recuperación, vencimiento y acceso contextual.
- Simulaciones sísmicas y filtro geográfico, safety check, respuesta SAFE y solicitudes de ayuda.
- Ausencia de liberación de ubicación para un evento TEST y ausencia de notificación TEST a contactos ordinarios.
- Quórum de confianza y SOS.
- Parseo de respuesta JSON ArcGIS mock, filtro por tiempo real, control de errores, ausencia de paginación `resultRecordCount` y conversión de coordenadas.
- Ingesta y deduplicación de sismos `source=SGC` mediante respuestas controladas; rechazo de fechas ausentes, antiguas y futuras.
- Endpoints HTTP 200 **en TestClient y respuestas ArcGIS simuladas** (no son pruebas live de servicio externo).

## No ejecutado / sin certificación

- Flutter `analyze`, `flutter test` y `flutter run` con el código modificado: Flutter SDK/Android no instalados en este entorno. Se incluye `mobile/test/widget_test.dart` para ejecutarlo en el equipo del proyecto.
- Consulta en vivo de SGC/EPIS: este entorno no tiene búsqueda/conectividad externa. Las anteriores consultas que compartió el usuario probaron que el catálogo configurado devuelve registros históricos y cero eventos desde 2026.
- Recepción push FCM con la app cerrada: faltan credenciales Firebase, SDK cliente configurado y dispositivos de prueba.
- Pruebas de rendimiento y resiliencia multi-contenedor en Docker; el motor Docker no está disponible aquí. El usuario puede realizarlas con el script entregado.
- Validación visual pixel a pixel de todas las pantallas: el prototipo adopta la estructura de las tres acciones principales del mockup, sin certificar coincidencia exacta.

**Conclusión:** validación automatizada local del backend satisfactoria; no se declara cierre del 100 % ni aptitud de producción hasta superar las pruebas externas y móviles pendientes.
