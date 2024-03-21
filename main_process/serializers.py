from morpho_typing import ArcSchema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from main_process.models import AssetFile, GeneratedModel, Project


class AssetFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetFile
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"

    def validate(self, attrs):
        if "metadata" in attrs:
            # run the metadata through the ArcSchema to check for a validation error
            ArcSchema(fields=attrs["metadata"])
        return super().validate(attrs)

    def update(self, instance, validated_data):
        # Only allow updation of project name and addition of asset types

        if "project_name" in validated_data:
            setattr(instance, "project_name", validated_data["project_name"])

        if "assets" in validated_data:
            old_assets = instance.assets
            new_assets = validated_data["assets"]

            missing_tags = []
            for key in old_assets:
                if key not in new_assets:
                    missing_tags.append(key)

            if len(missing_tags) > 0:
                raise ValidationError(
                    f"Asset tags cannot be deleted; the following tags are missing from the update action: {missing_tags}")

            setattr(instance, "assets", validated_data["assets"])

        instance.save()

        return instance


class GeneratedModelSerializer(serializers.ModelSerializer):

    # Custom Fields

    files = AssetFileSerializer(many=True, read_only=True)

    class Meta:
        model = GeneratedModel
        fields = ["id", "parameters", "files"]

    def validate(self, attrs):
        project_instance = self.context["project"]

        new_attrs = {}

        if "parameters" in attrs:
            # new_attrs["parameters"] = {}
            schema = ArcSchema(fields=project_instance.metadata)
            record = []
            for field in schema.fields:
                record.append(attrs["parameters"][field.field_name])
            is_valid, errors = schema.validate_record(record)
            if not is_valid:
                raise ValidationError(errors)
            new_attrs["parameters"] = record

        return super().validate(new_attrs)

    def create(self, validated_data):
        project_instance = self.context["project"]

        if "parameters" not in validated_data:
            raise ValidationError("parameters are required.")

        validated_data["project_key"] = project_instance

        return super().create(validated_data)
