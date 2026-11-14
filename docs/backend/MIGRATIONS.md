# Migraciones de base de datos

El MVP mantiene `AUTO_CREATE_SCHEMA=true` únicamente para DEV/TEST y facilitar la demo académica.

Para un entorno persistente:

```bash
cd backend
export DATABASE_URL='postgresql+psycopg://...'
alembic upgrade head
```

En producción se debe configurar:

```env
APP_ENV=production
AUTO_CREATE_SCHEMA=false
ALLOW_TEST_ENDPOINTS=false
```

La revisión `20261030_0001` es la línea base del esquema. A partir de ella, los cambios deben generarse como migraciones incrementales de Alembic y probarse en TEST antes de aplicarse a DEMO/producción.
