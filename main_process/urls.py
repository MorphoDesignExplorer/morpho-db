from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_nested import routers

from main_process import views

router = routers.SimpleRouter()
router.register(r'project', views.ProjectViewSet)
router.register(r'document', views.MarkdownDocumentViewSet)

project_router = routers.NestedSimpleRouter(
    router, r'project', lookup="project")
project_router.register(
    r'model', views.GeneratedModelViewSet, basename="project-models")

generated_model_router = routers.NestedSimpleRouter(
    project_router, r'model', lookup="model")
generated_model_router.register(
    r'files', views.AssetFileViewSet, basename="model-files")

metadata_urlpatterns = [
    path('project/<str:pk>/metadata/', views.ProjectMetadataView.as_view()),
]

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('', include(project_router.urls)),
    *metadata_urlpatterns,
    path('', include(generated_model_router.urls)),
]

urlpatterns += [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

urlpatterns += router.urls
