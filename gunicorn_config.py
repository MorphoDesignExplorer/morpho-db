import multiprocessing

accesslog = "-"  # stdin for journalctl
errorlog = "/app/django.log"
loglevel = 'debug'
capture_output = True
workers = multiprocessing.cpu_count() * 2 + 1
# bind = "127.0.0.1:8000" # Debug Config
bind = "unix:/run/gunicorn.sock"
raw_env = ["DJANGO_SETTINGS_MODULE=backend.production_settings"]
wsgi_app = "backend.wsgi"
