# Morpho Design Explorer - Backend

This is the backend behind the Morpho Design Explorer system. 

### Deployment Notes

Be sure to set the `DJANGO_SETTINGS_MODULE` to `backend.production_settings` on the deployment environment. Modify and use `backend.devel_settings` for local testing.

Deployment with gunicorn can be carried out without any modification through the tutorial[1] mentioned below. The change to be made in the `gunicorn.service` file is as follows:
```
[Service]
User=username
Group=www-data
WorkingDirectory=/path/to/repository/clone
ExecStart=/path/to/virtual/environment -c /path/to/repository/clone/gunicorn_config.py
```

#### References

1. Tutorial to deploy the system on a container: https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu#step-6-testing-gunicorn-s-ability-to-serve-the-project
2. gunicorn settings documentation: https://docs.gunicorn.org/en/stable/settings.html
