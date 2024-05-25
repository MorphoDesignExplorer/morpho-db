FROM python:3.11
ADD requirements.txt /app/requirements.txt
RUN python -m venv /env
RUN /env/bin/pip install --upgrade pip
RUN /env/bin/pip install -r /app/requirements.txt
ADD . /app
WORKDIR /app
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH
ENV DJANGO_SETTINGS_MODULE backend.production_settings
EXPOSE 8000
CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "backend.wsgi"]

