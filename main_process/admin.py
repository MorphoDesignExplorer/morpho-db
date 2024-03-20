from django.contrib import admin
from main_process.models import Project, GeneratedModel, AssetFile

# Register your models here.

admin.site.register(Project)
admin.site.register(GeneratedModel)
admin.site.register(AssetFile)
