from main_process.models import Project, GeneratedModel, AssetFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from enum import Enum


class AssetFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetFile
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"

    class DefinedTypes(Enum):
        INT = "INT"
        DOUBLE = "DOUBLE"
        STRING = "STRING"

        @classmethod
        def from_str(cls, string):
            if string == "INT":
                return cls.INT
            elif string == "DOUBLE":
                return cls.DOUBLE
            elif string == "STRING":
                return cls.STRING
            raise TypeError("Appropriate mapping not found.")

    __PRIORITY_MAPPING = {
        DefinedTypes.DOUBLE: 2,
        DefinedTypes.INT: 1
    }

    """
    Compares the size compatibility of `a` against `b`.
    
    RETURN VALUES:
    1: if a is larger than b
    -1: if a is smaller than b
    0: if a is equal to b

    EXCEPTIONS:
    TypeError: if a is incompatible with b
    """

    def size_ordering(self, a, b):
        if a == b:
            return 0
        if a == self.DefinedTypes.STRING or b == self.DefinedTypes.STRING:
            raise TypeError(
                "type STRING cannot be compared with other types.")

        if self.__PRIORITY_MAPPING[a] > self.__PRIORITY_MAPPING[b]:
            return 1
        elif self.__PRIORITY_MAPPING[a] < self.__PRIORITY_MAPPING[b]:
            return -1
        else:
            return 0

    @classmethod
    def type_match(cls, item: int | float | str, defined_type):
        numeric_types = {cls.DefinedTypes.DOUBLE.value,
                         cls.DefinedTypes.INT.value}
        if isinstance(item, int) or isinstance(item, float):
            if defined_type == cls.DefinedTypes.STRING:
                return False
        else:
            if defined_type in numeric_types:
                return False
        return True

    def validate(self, attrs):
        # iterating through the dict and checking the pairs (data_type, unit_name)
        if "metadata" in attrs:
            for key in attrs["metadata"]:
                if len(attrs["metadata"][key]) == 2:
                    param_pair = attrs["metadata"][key]
                    if param_pair[0] not in [def_type.value for def_type in self.DefinedTypes]:
                        raise ValidationError(
                            f"Key \'{key}\': Wrong format. Refer to project creation documentation.")
                else:
                    raise ValidationError(
                        f"Field \'{key}\': Wrong format. Refer to project creation documentation.")
        return super().validate(attrs)

    def create(self, validated_data):
        if (
            ("project_name" in validated_data) and
            (validated_data["project_name"].__len__() == 0)
        ):
            raise ValidationError("Project name is empty.")

        if (not "metadata" in validated_data):
            raise ValidationError("Project parameters are not defined.")

        if (not "assets" in validated_data):
            raise ValidationError("Asset tags are not defined.")

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "project_name" in validated_data:
            setattr(instance, "project_name", validated_data["project_name"])

        if "metadata" in validated_data:
            old_params = instance.metadata
            new_params = validated_data["metadata"]

            for key in old_params:
                if key not in new_params.keys():
                    raise ValidationError("Parameters cannot be deleted.")

            for key, value in new_params.items():
                if key not in old_params:
                    continue
                new_value, old_value = self.DefinedTypes.from_str(
                    value[0]), self.DefinedTypes.from_str(old_params[key][0])
                try:
                    if self.size_ordering(new_value, old_value) < 0:
                        raise ValidationError(
                            "Parameters can only be expanded, not shrunk.")
                except TypeError:
                    raise ValidationError(
                        "Cannot convert number types to non-number types.")
            setattr(instance, "metadata", validated_data["metadata"])

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
        fields = "__all__"

    def validate(self, attrs):
        project_instance = self.context["project"]
        missing_parameters = []
        mismatched_types = []

        new_attrs = {}

        if "parameters" in attrs:
            new_attrs["parameters"] = {}
            for param_name in project_instance.metadata:
                if param_name not in attrs["parameters"]:
                    missing_parameters.append(param_name)
                    continue

                param_type = project_instance.metadata[param_name][0]
                param_val = attrs["parameters"][param_name]
                if not ProjectSerializer.type_match(param_val, param_type):
                    mismatched_types.append(param_name)
                    continue

                new_attrs['parameters'].update({param_name: param_val})

            if len(missing_parameters) > 0:
                raise ValidationError(
                    f"The following parameters were missing: {missing_parameters}")

            if len(mismatched_types) > 0:
                raise ValidationError(
                    f"The following parameters had mismatched types: {mismatched_types}. Refer to project schema."
                )

        return super().validate(new_attrs)

    def create(self, validated_data):
        project_instance = self.context["project"]

        if "parameters" not in validated_data:
            raise ValidationError("parameters are required.")

        validated_data["project_key"] = project_instance

        return super().create(validated_data)
