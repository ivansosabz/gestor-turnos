# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

El README cubre setup, variables de entorno y deploy. Este archivo cubre **arquitectura** y **convenciones** que requieren leer varios archivos para entender.

## Comandos útiles

Setup y daily workflow ya están en el README. Adicionales que conviene saber:

```bash
# Tras tocar models.py
python manage.py makemigrations turnos
python manage.py migrate

# Reset rápido cuando el seed quedó mal (no hay datos reales que conservar)
rm db.sqlite3 && python manage.py migrate && python manage.py setup_inicial

# Inspeccionar/modificar datos sin SQL
python manage.py shell
# /admin/ también está habilitado para los 4 modelos.
```

No hay test suite, ni linter configurado, ni pre-commit hooks. Si agregás tests, usar `pytest-django` o `python manage.py test turnos`.

## Arquitectura

### Capas

```
templates/*.html (Bootstrap + FullCalendar + day.js, todo CDN, JS inline)
       ↓ fetch JSON
turnos/views.py          ← Function-Based Views (HTML + @api_view de DRF)
       ↓ delegan a
turnos/services.py       ← LÓGICA DE NEGOCIO. Es el "cerebro" de la app.
       ↓ usa
turnos/models.py         ← Cuidador, CicloConfig, CicloOrden, TurnoReal
```

**Regla**: lógica nueva va en `services.py`, no en views ni en modelos. Las vistas solo parsean input, llaman al service y devuelven la respuesta.

### URLs: dos roots

`no_me_olvido/urls.py` monta dos includes:
- `/api/...` → `turnos/api_urls.py` (endpoints DRF)
- `/...`     → `turnos/urls.py` (vistas HTML)

Las vistas API y HTML viven juntas en el mismo `views.py` — distinguilas por el decorador (`@api_view` vs `@ensure_csrf_cookie`).

### Modelo de datos: invariantes clave

1. **Solo puede haber UN `CicloConfig` con `activo=True`**. El `save()` del modelo lo garantiza desactivando los demás dentro de una transacción. Crear un ciclo nuevo desactiva al anterior — esto es intencional, no hay UI para "editar" un ciclo, se crea uno nuevo.

2. **`TurnoReal.fecha` es UNIQUE**. Como mucho un registro por día. Las mutaciones siempre van por `services.registrar_turno()` que usa `update_or_create`.

3. **El cuidador del día se calcula así** (`services.calcular_turno_para_fecha`):
   ```
   posicion = ((fecha - ciclo.fecha_inicio).days // ciclo.intervalo_dias) % len(cuidadores)
   ```
   - `intervalo_dias=1` → rotación diaria (default del seed). Yo→Papá→Tío→Yo...
   - `intervalo_dias=2` → cada cuidador duerme 2 noches seguidas.
   - Fechas anteriores a `fecha_inicio` devuelven `None` (no extrapola hacia atrás).

4. **`TurnoReal` PISA al ciclo teórico**. `services.get_calendario(año, mes)` itera el mes calculando el cuidador del ciclo, pero si existe un `TurnoReal` para esa fecha, usa el `responsable` y `tipo` del registro. Es la forma de modelar coberturas/intercambios sin tocar el ciclo.

5. **Foreign keys con PROTECT**. No se pueden borrar Cuidadores en uso. Para "sacar" un cuidador del ciclo, marcalo `activo=False` (se filtra en los selects pero conserva el historial).

### Seed inicial

`turnos/management/commands/setup_inicial.py` es **idempotente**:
- Crea Yo/Papá/Tío con `get_or_create` (no pisa colores ya cambiados).
- Crea un ciclo activo SOLO si no existe ninguno — preserva configuración manual.
- Default: `INTERVALO_DIAS_DEFAULT = 1` (rotación diaria). El README comenta "cada 3 días", está desactualizado: lo correcto es 1.

## Convenciones

- **Function-Based Views obligatorio**. El usuario pidió FBV explícitamente. No introducir `APIView`, `ViewSet`, `TemplateView`, `ListView`, etc. Para API usar `@api_view([...])`; para HTML, funciones que devuelven `render(...)`.

- **Código comentado en español**. El usuario pidió comentar todo el código (excepción a la regla general de "no comments"). Mantené ese estilo: docstring en cada función, comentarios inline para lógica no obvia, comentarios `{# #}` en los templates y `//` en el JS.

- **UI en español, código en español neutro**. Los identificadores Python son ASCII (`anio`, no `año`), pero la API acepta `?año=` *y* `?anio=` por comodidad. Los nombres de modelos y campos están en español (`Cuidador`, `intervalo_dias`, `fecha_inicio`).

- **Sin autenticación**. Todas las vistas son públicas (modelo de confianza familiar). Si agregás auth en el futuro, `LoginRequiredMixin` no aplica acá: usar el decorador `@login_required` y, para la API, `permission_classes` por endpoint.

- **CSRF en POSTs de la API**: las vistas que renderizan templates llevan `@ensure_csrf_cookie`, el JS de `base.html` lee la cookie en `window.csrfToken`, y los `fetch` POST mandan el header `X-CSRFToken`. Si agregás un nuevo POST desde JS, seguir ese patrón.

- **Frontend sin build step**. Bootstrap, FullCalendar y day.js se cargan por CDN; no hay bundler ni npm. El service worker (`static/sw.js`) precachea esos CDNs — si cambia una versión, también hay que actualizar la lista en `ASSETS` y bumpear `CACHE_NAME` (`nmo-v1` → `nmo-v2`).

- **Static files**. `STATICFILES_DIRS = [BASE_DIR / "static"]`. WhiteNoise sirve estáticos en dev y prod (`whitenoise.runserver_nostatic` desactiva el built-in de Django). En prod hace falta `collectstatic` antes de levantar gunicorn.

## Cosas que NO existen todavía

- Tests automáticos.
- Iconos PWA reales (hay un README.txt placeholder en `static/icons/`).
- Auth, permisos, multi-tenant.
- Validación de que `responsable_id`/`turno_original_id` existan al registrar (los FKs lo enforzan a nivel DB; en service no se chequea explícitamente).
- Endpoint para borrar un `TurnoReal` (solo se puede update vía `registrar_turno`, o borrar desde `/admin/`).
