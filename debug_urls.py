
import os
import django
from django.conf import settings
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventario.urls import router

print("Registered URLs:")
for url in router.urls:
    print(url)
