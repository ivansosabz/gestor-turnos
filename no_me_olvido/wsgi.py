import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "no_me_olvido.settings")

application = get_wsgi_application()
