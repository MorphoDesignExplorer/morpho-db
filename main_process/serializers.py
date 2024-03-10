from main_process.models import Project, GeneratedModel
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from enum import Enum


class ProjectSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Project
        fields = "__all__"

    def validate(self, attrs):
        if (
            ("project_name" in attrs) and
            (attrs["project_name"].__len__() == 0)
        ):
            raise ValidationError("Project name is empty.")

        if (not "metadata" in attrs):
            raise ValidationError("Project parameters are not defined.")

        # iterating through the dict and checking the pairs (data_type, unit_name)
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

    def update(self, instance, validated_data):
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

        # if validated_data["project_name"] == instance.project_name:
            # instance.delete()
        if "project_name" in validated_data:
            setattr(instance, "project_name", validated_data["project_name"])
        if "metadata" in validated_data:
            setattr(instance, "metadata", validated_data["metadata"])

        instance.save()

        return instance
