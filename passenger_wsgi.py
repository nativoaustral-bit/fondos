#!/home1/paulocis/fondos_app/venv/bin/python
import sys, os

# Add project directory to sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
for d in [project_dir, '/home1/paulocis/fondos_app', '/home1/paulocis/public_html/FONDOS']:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

# Set environment variables for Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'humm_fondos.settings'

# Import Django WSGI application
from humm_fondos.wsgi import application as _application

# Wrapper to strip passenger_wsgi.py from SCRIPT_NAME in generated URLs
def application(environ, start_response):
    environ['SCRIPT_NAME'] = ''
    return _application(environ, start_response)

# If running under Apache CGI (no Passenger plugin)
if __name__ == '__main__' or 'GATEWAY_INTERFACE' in os.environ:
    from wsgiref.handlers import CGIHandler
    CGIHandler().run(application)
