from django.urls import include, path
# from rest_framework import routers
from rest_framework_nested import routers

from main_process import views

router = routers.SimpleRouter()
router.register(r'project', views.ProjectViewSet)

project_router = routers.NestedSimpleRouter(
    router, r'project', lookup="project")
project_router.register(
    r'model', views.GeneratedModelViewSet, basename="project-models")

generated_model_router = routers.NestedSimpleRouter(
    project_router, r'model', lookup="model")
generated_model_router.register(
    r'files', views.AssetFileViewSet, basename="model-files")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('', include(project_router.urls)),
    path('', include(generated_model_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('token_login/', views.TokenLoginView.as_view())
]

urlpatterns += router.urls
