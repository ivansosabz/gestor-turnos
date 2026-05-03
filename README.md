# No Me Olvido

App Django para coordinar turnos de cuidado nocturno entre 3 personas con un ciclo configurable. Calendario coloreado por cuidador, registro de coberturas e intercambios, vista pública de solo lectura para compartir, y soporte PWA.

## Stack

- Django 5 + Django REST Framework
- Bootstrap 5, FullCalendar 6, day.js (CDN)
- PostgreSQL en producción (sqlite local), `dj-database-url`
- WhiteNoise para estáticos
- PWA (`manifest.json` + service worker)

## Setup local

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows bash
# source .venv/bin/activate      # Linux/macOS

pip install -r requirements.txt
cp .env.example .env             # editar valores

python manage.py migrate
python manage.py setup_inicial   # crea Yo, Papá, Tío y un ciclo cada 3 días
python manage.py runserver
```

Abrir http://localhost:8000/.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DJANGO_SECRET_KEY` | clave de Django |
| `DJANGO_DEBUG` | `True`/`False` |
| `DJANGO_ALLOWED_HOSTS` | lista separada por comas |
| `DATABASE_URL` | URL de la base; default sqlite |
| `CSRF_TRUSTED_ORIGINS` | URLs HTTPS confiables (Railway) |

## Rutas

- `/` calendario interactivo
- `/registrar/` formulario para registrar turno real
- `/compartir/` calendario de solo lectura para Papá y Tío
- `/config/` configurar ciclo (intervalo y orden)
- `/admin/` admin Django

API: `/api/calendario/`, `/api/cuidadores/`, `/api/turnos/registrar/`, `/api/ciclo/activo/`, `/api/ciclo/crear/`.

## PWA

Reemplazar los iconos en `static/icons/` (`icon-192.png` y `icon-512.png`) antes de desplegar.

## Deploy en Railway

1. Conectá el repo, agregá un servicio PostgreSQL.
2. Setea variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS=tu-dominio.up.railway.app`, `CSRF_TRUSTED_ORIGINS=https://tu-dominio.up.railway.app`. `DATABASE_URL` la inyecta Railway.
3. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`.
4. Start: `gunicorn no_me_olvido.wsgi`.
5. Una vez levantada, ejecutá `python manage.py setup_inicial` desde el shell de Railway.
