import os
import sys

# Put the Django project on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

os.environ['DJANGO_SETTINGS_MODULE'] = 'editorsnotes.settings'

from django.core.handlers.wsgi import get_wsgi_application
application = get_wsgi_application()
