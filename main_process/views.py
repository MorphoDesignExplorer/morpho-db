from authorization.utils import JWTAuthentication
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max 
from morpho_typing import MorphoAssetCollection
import pydantic
from rest_framework import permissions, status, views, viewsets, views
from rest_framework.authentication import (SessionAuthentication)
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.request import Request
from rest_framework.response import Response

from main_process.models import AssetFile, GeneratedModel, Project, ProjectMetadata, MarkdownDocument, Caption
from main_process.serializers import (AssetFileSerializer,
                                      GeneratedModelSerializer,
                                      ProjectSerializer, GeneratedModelReadOnlySerializer, MarkdownDocumentSerializer)
from typing import Literal, Union, List



class AssetFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer

    def get_queryset(self):
        return AssetFile.objects.filter(generated_model=self.kwargs["model_pk"])


class GeneratedModelViewSet(viewsets.ModelViewSet):
    queryset = GeneratedModel.objects.all()
    serializer_class = GeneratedModelSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer(self, *args, **kwargs):
        if self.request.method in ('PUT', 'PATCH') and isinstance(self.request.data, list):
            kwargs['many'] = True
        elif self.request.method == 'GET':
            return GeneratedModelReadOnlySerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project = Project.objects.get(project_name=self.kwargs["project_pk"])
        context.update(
            {"project": project})
        return context

    def get_queryset(self):
        return GeneratedModel.objects.filter(project=self.kwargs["project_pk"]).prefetch_related("files").order_by("scoped_id")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        models = request.data
        erroring_models = []
        succeeding_models = []
        if isinstance(models, dict):
            # perform regular, single-object creation
            scoped_id = 0 # this WILL break. Please fetch the latest scoped_id and THEN add the models.
            scoped_id_set = GeneratedModel.objects.select_for_update().filter(project_id=self.get_serializer_context()["project"].project_name)
            if scoped_id_set.exists():
                scoped_id = 1 + scoped_id_set.aggregate(Max('scoped_id'))["scoped_id__max"]
                models["scoped_id"] = scoped_id
            serializer = self.get_serializer(data=models)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        raise NotImplementedError("bulk model creation is not supported.")
        for model in models:
            # handle multiple-object creation
            serializer = GeneratedModelSerializer(
                data=model, context=self.get_serializer_context())
            if not serializer.is_valid():
                erroring_models.append(
                    {"model": model, "errors": serializer.errors})
            else:
                succeeding_models.append(model)
                self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
        return Response({"models_created": len(succeeding_models), "failures": erroring_models, "successes": succeeding_models}, status=status.HTTP_200_OK, headers=headers)

    def update(self, request, *args, **kwargs):
        generated_model = self.get_object()
        project = Project.objects.get(project_name=self.kwargs["project_pk"])
        fileset = dict(map(lambda asset_file: (asset_file.tag, asset_file),
                       AssetFile.objects.filter(generated_model=generated_model)))
        taglist = {asset.tag: asset for asset in MorphoAssetCollection(
            assets=project.assets).assets}

        files_were_uploaded = False
        if len(request.FILES) > 0:
            # Performing file creation here

            # checking manually if the asset class / tag exists within the project schema
            nonexisting_filetags = set(
                filter(lambda filename: filename not in taglist, request.FILES.keys()))
            if len(nonexisting_filetags) > 0:
                raise ValidationError(
                    f"The following tags do not exist: {nonexisting_filetags}")

            # add file extension validation here later

            # if all is well, upload all the files
            for filename, file in request.FILES.items():
                if filename in fileset:
                    fileset[filename].delete()
                file_object = AssetFile.objects.create(
                    file=file, tag=filename, generated_model=generated_model)
                file_object.save()

            files_were_uploaded = True

        # Run inherited code
        serializer = self.get_serializer(
            generated_model, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(generated_model, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            generated_model._prefetched_objects_cache = {}

        # nothing else to get updated here, so we do nothing with the serialized data
        response = {
            "model": serializer.data,
        }

        if files_were_uploaded:
            response["files"] = f"Files {list(request.FILES.keys())} were successfully uploaded"

        return Response(response)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(deleted=False)
    serializer_class = ProjectSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # perform soft deletion by flipping the deleted status
        instance = self.get_object()
        instance.deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkdownDocumentViewSet(viewsets.ModelViewSet):
    queryset = MarkdownDocument.objects.all()
    serializer_class = MarkdownDocumentSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class MetadataRequest(pydantic.BaseModel):
    field: Literal["captions", "human_name", "description"]
    new_content: str | List[Caption]


class ProjectMetadataView(views.APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_instance(self) -> ProjectMetadata | None:
        try:
            model = ProjectMetadata.objects.get(project__project_name=self.kwargs.get("pk"))
            return model
        except:
            return None

    def get(self, request: Request, *args, **kwargs):
        instance = self.get_instance()
        if instance is not None:
            metadata = ProjectMetadata.Metadata.model_validate(instance)
            return Response(metadata.model_dump())
        else:
            raise APIException("Resource not found.")

    def put(self, request: Request, *args, **kwargs):
        try:
            metadata = MetadataRequest.model_validate(request.data)
            instance = self.get_instance()
            print(metadata)
            match metadata.field:
                case "captions":
                    instance.captions = [caption.model_dump() for caption in metadata.new_content]
                    instance.save()
                case "description":
                    instance.description.text = metadata.new_content
                    instance.description.save()
                case "human_name":
                    instance.human_name = metadata.new_content
                    instance.save()
            response = ProjectMetadata.Metadata.model_validate(self.get_instance())
            return Response(
                response.model_dump()
            )
        except pydantic.ValidationError as ve:
            return Response(ve.errors())

