"""
ASGI entrypoint.

Configures Django and then runs the application defined in the ASGI_APPLICATION setting.

For more information on this file, see
https://channels.readthedocs.io/en/latest/deploying.html
"""

import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elite.settings")
django.setup()

application = get_default_application()
