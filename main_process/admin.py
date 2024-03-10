from django.contrib import admin
from main_process.models import Project, GeneratedModel

# Register your models here.

admin.site.register(Project)
admin.site.register(GeneratedModel)

