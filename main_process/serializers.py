from morpho_typing import MorphoAssetCollection, MorphoProjectSchema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy

from main_process.models import AssetFile, GeneratedModel, Project, ProjectMetadata, MarkdownDocument


class AssetFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetFile
        fields = "__all__"


class AssetFileReadOnlySerializer(serpy.Serializer):
    id = serpy.StrField()
    file = serpy.MethodField()
    tag = serpy.StrField()
    generated_model = serpy.MethodField()

    def get_file(self, instance):
        return instance.file.storage.get_prefix() + instance.file.name

    def get_generated_model(self, instance):
        return instance.generated_model.id


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"

    metadata = serializers.SerializerMethodField(read_only=True)

    def get_metadata(self, instance):
        return ProjectMetadataSerializer(ProjectMetadata.objects.get(project=instance)).data

    def validate(self, attrs):
        assert "project_name" in attrs
        if "variable_metadata" in attrs:
            # run the metadata through MorphoProjectSchema to check for a validation error
            MorphoProjectSchema(fields=attrs["variable_metadata"])
        if "output_metadata" in attrs:
            MorphoProjectSchema(fields=attrs["output_metadata"])
        if "assets" in attrs:
            # run the asset definition through MorphoAssetCollection to check for a validation error
            MorphoAssetCollection(assets=attrs["assets"])
        return super().validate(attrs)

    def update(self, instance, validated_data):
        # Only allow addition of asset types

        if "assets" in validated_data:
            old_assets = MorphoAssetCollection(assets=instance.assets)
            new_assets = MorphoAssetCollection(assets=validated_data["assets"])

            old_asset_tags = set(
                [old_asset.tag for old_asset in old_assets.assets])
            new_asset_tags = set(
                [new_asset.tag for new_asset in new_assets.assets])

            # returns tags that are missing in new_asset_tags, that were present in old_asset_tags
            missing_tags = list(old_asset_tags.difference(new_asset_tags))

            if len(missing_tags) > 0:
                raise ValidationError(
                    f"Asset tags cannot be deleted; the following tags are missing from the update action: {missing_tags}")

            setattr(instance, "assets", validated_data["assets"])

        instance.save()

        return instance


class GeneratedModelReadOnlySerializer(serpy.Serializer):
    id = serpy.IntField()
    scoped_id = serpy.IntField()
    parameters = serpy.Field(attr="parameters")
    output_parameters = serpy.Field(attr="output_parameters")
    files = serpy.MethodField()

    def get_files(self, instance):
        return [AssetFileReadOnlySerializer(file).data for file in instance.files.all()]


class GeneratedModelSerializer(serializers.ModelSerializer):

    # Custom Fields

    files = AssetFileSerializer(many=True, read_only=True)

    class Meta:
        model = GeneratedModel
        fields = ["id", "scoped_id", "parameters", "output_parameters", "files"]

    def validate(self, attrs):
        project_instance = self.context["project"]

        new_attrs = {}

        if "parameters" in attrs:
            schema = MorphoProjectSchema(
                fields=project_instance.variable_metadata)

            # arrange the record parameters according to the schema's order
            record, params = [], {}
            for field in schema.fields:
                record.append(attrs["parameters"][field.field_name])
                params[field.field_name] = attrs["parameters"][field.field_name]
            is_valid, errors = schema.validate_record(record)
            if not is_valid:
                raise ValidationError(errors)
            new_attrs["parameters"] = params

        if "output_parameters" in attrs:
            schema = MorphoProjectSchema(
                fields=project_instance.output_metadata)
            # arrange the record parameters according to the schema's order
            record, params = [], {}
            for field in schema.fields:
                record.append(attrs["output_parameters"][field.field_name])
                params[field.field_name] = attrs["output_parameters"][field.field_name]
            is_valid, errors = schema.validate_record(record)
            if not is_valid:
                raise ValidationError(errors)
            new_attrs["output_parameters"] = params

        return super().validate(new_attrs)

    def create(self, validated_data):
        project_instance = self.context["project"]

        if "parameters" not in validated_data:
            raise ValidationError("parameters are required.")

        validated_data["project"] = project_instance

        return super().create(validated_data)

class ProjectMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMetadata
        fields = ["captions", "description", "human_name"]

    def validate(self, attrs):
        project: Project = self.context["project"]
        attrs = super().validate(attrs)
        all_tagnames = set([obj["field_name"] for obj in project.variable_metadata + project.output_metadata])
        if type(attrs["captions"]) != list:
            raise ValidationError("Captions must be a list of form {'tag_name': string, 'display_name': string}.")
        for caption in attrs["captions"]:
            tag_name, display_name = caption["tag_name"], caption["display_name"]
            if tag_name not in all_tagnames:
                raise ValidationError(f"parameter name '{tag_name}' does not match any parameter names.")
            if len(display_name) == 0:
                raise ValidationError(f"Display name for parameter '{tag_name}' cannot be empty.")
        attrs["project"] = project
        return attrs


class MarkdownDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkdownDocument
        fields = ["text"]
