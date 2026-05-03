# AGENTS.md — gestor-de-turnos

## Developer commands

```bash
# Daily start (Windows bash)
source .venv/Scripts/activate && python manage.py runserver

# After touching models.py
python manage.py makemigrations turnos && python manage.py migrate

# Full reset (safe — no real data to preserve)
rm db.sqlite3 && python manage.py migrate && python manage.py setup_inicial
```

No tests, linter, formatter, or typecheck are configured.

## Architecture

- **Django 5 + DRF**, Function-Based Views only. Never introduce `APIView`, `ViewSet`, `TemplateView`, or class-based views.
- **Logic goes in `turnos/services.py`**. Views only parse input, call the service, return response.
- **Two URL roots** in `no_me_olvido/urls.py`: `/api/` → `turnos/api_urls.py`, `/` → `turnos/urls.py`. API routes must be listed before HTML routes.
- **No authentication** — all views are public (family trust model).

## Data invariants

1. Only **ONE `CicloConfig` with `activo=True`** at a time. `CicloConfig.save()` enforces this in a transaction. Creating a new cycle deactivates the previous one.
2. **`TurnoReal.fecha` is UNIQUE** — at most one record per day. Mutations always go through `services.registrar_turno()` which uses `update_or_create`.
3. **All FKs use `PROTECT`** — cannot delete Cuidadores in use. Mark `activo=False` instead.

## Conventions

- **Code comments in Spanish** — docstrings, inline comments, template `{# #}` comments, JS `//` comments.
- **Identifiers in ASCII Spanish** (`anio`, `fecha_inicio`), but the API accepts both `?año=` and `?anio=`.
- **Build-free frontend** — Bootstrap, FullCalendar, day.js from CDN. JS is inline in templates.
- **CSRF on POSTs**: templates use `@ensure_csrf_cookie`, JS reads `window.csrfToken` from `base.html`, POST fetches send `X-CSRFToken` header. Follow this pattern for new POSTs.

## PWA cache updates

If CDN versions change, update both `ASSETS` list and bump `CACHE_NAME` in `static/sw.js` (e.g., `nmo-v1` → `nmo-v2`).

## Deploy

Railway with PostgreSQL. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`. Start: `gunicorn no_me_olvido.wsgi`. Run `setup_inicial` once from Railway shell.

## Reference

See `CLAUDE.md` for detailed architecture walkthrough, seed behavior, and "what doesn't exist yet" inventory.
