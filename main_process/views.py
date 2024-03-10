from rest_framework import status, viewsets
from rest_framework.response import Response
from main_process.serializers import ProjectSerializer
from main_process.models import Project


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    # Add auth class here later, requires 2FA
    permission_classes = []

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
