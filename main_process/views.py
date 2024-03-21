import django_otp
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import permissions, status, views, viewsets, mixins
from rest_framework.authentication import (BasicAuthentication,
                                           SessionAuthentication,
                                           TokenAuthentication)
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError

from main_process.models import GeneratedModel, Project, AssetFile
from main_process.serializers import (GeneratedModelSerializer,
                                      ProjectSerializer, AssetFileSerializer)


class TokenLoginView(views.APIView):
    authentication_classes = [TokenAuthentication,
                              SessionAuthentication, BasicAuthentication]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        try:
            assert "username" in request.data
            assert "password" in request.data
            assert "token" in request.data
            print(request.data)

            user = User.objects.get(username=request.data["username"])
            assert user.check_password(request.data["password"])
            request.user = user

            # at this point, user is authenticated.

            if not django_otp.user_has_device(user=user, confirmed=True):
                return Response({"detail", "User has no valid authentication devices."}, status=status.HTTP_400_BAD_REQUEST)

            # get auth devices for the user
            with transaction.atomic():
                device_list = django_otp.devices_for_user(
                    user=user, confirmed=True, for_verify=True)

                # verify token against each device
                for device in device_list:
                    try:
                        device_or_none = django_otp.verify_token(
                            user=user, device_id=device.persistent_id, token=request.data["token"])
                        if device_or_none is not None:
                            token, _ = Token.objects.get_or_create(user=user)
                            return Response({"token": token.key}, status=status.HTTP_200_OK)
                    except:
                        return Response({"detail": "A problem happened during OTP verification."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                return Response({"detail": "Invalid OTP. Wait for a few seconds and re-enter a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

        except AssertionError:
            return Response({"detail": "Invalid login attempt."}, status=status.HTTP_400_BAD_REQUEST)


class AssetFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer

    def get_queryset(self):
        return AssetFile.objects.filter(generated_model=self.kwargs["model_pk"])


class GeneratedModelViewSet(viewsets.ModelViewSet):
    queryset = GeneratedModel.objects.all()
    serializer_class = GeneratedModelSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project = Project.objects.get(project_id=self.kwargs["project_pk"])
        context.update(
            {"project": project})
        return context

    def get_queryset(self):
        return GeneratedModel.objects.filter(project_key=self.kwargs["project_pk"]).prefetch_related("files")

    def update(self, request, *args, **kwargs):
        generated_model = self.get_object()
        project = Project.objects.get(project_id=self.kwargs["project_pk"])
        fileset = dict(map(lambda asset_file: (asset_file.tag, asset_file),
                       AssetFile.objects.filter(generated_model=generated_model)))
        taglist = set(project.assets)
        print(fileset, taglist)

        files_were_uploaded = False
        if len(request.FILES) > 0:
            # Performing file creation here

            # checking manually if the asset class / tag exists within the project schema
            nonexisting_filetags = set(
                filter(lambda filename: filename not in taglist, request.FILES.keys()))
            if len(nonexisting_filetags) > 0:
                raise ValidationError(
                    f"The following tags do not exist: {nonexisting_filetags}")

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
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
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
