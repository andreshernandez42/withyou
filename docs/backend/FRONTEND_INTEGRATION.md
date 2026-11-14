# Integración del mini frontend Flutter

El backend conserva las rutas ya utilizadas por `mobile/lib/services/api_service.dart`.

## Autenticación

`POST /auth/login` sigue devolviendo `access_token`, `token_type` y `user`; ahora también devuelve `refresh_token` y `expires_in`. El frontend actual puede seguir operando con `access_token` y posteriormente incorporar refresh sin romper el contrato.

## Usuarios visibles

`GET /users` se mantiene por compatibilidad. Para un usuario normal devuelve únicamente personas que lo han aceptado como contacto de confianza. TESTER/ADMIN conserva el directorio de laboratorio.

Existe además `GET /authorized-subjects`, recomendado para nuevas pantallas de verificación.

## Eventos de laboratorio

`POST /test/emergency-events` conserva `event_id`, `is_test` y `affected_users`; adicionalmente entrega el objeto `event`. Solo funciona para TESTER/ADMIN y cuando `ALLOW_TEST_ENDPOINTS=true`.

## Ubicación

`can_view_checkpoint=true` indica elegibilidad, no acceso permanente. Para consultar ubicación de otra persona se requiere un grant temporal vigente. El flujo normal es:

1. Welfare Check → quórum, o SOS/HELP_REQUIRED/evento preautorizado.
2. Backend crea `LocationAccessGrant`.
3. `GET /checkpoints/{subject}/latest` o `/welfare-checks/{id}/location` entrega COARSE/EXACT según política.

## Notificaciones

El MVP conserva polling de `/notifications`. Si FCM se configura, los mismos registros pueden enviarse como push sin cambiar el modelo funcional.
