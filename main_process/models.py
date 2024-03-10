from django.db import models
from uuid import uuid4


class Project(models.Model):
    """
    The model representing the Project relation.

    Fields:
        creation_date: the date and time of the creation of a project
        project_name: the name of the project
        metadata: contains the definition of variable parameters pertaining to the project. Also acts as a catch-all field.

    `metadata` primarily contains key-value of the following format:
        parameter_name: (data_type, unit_name)
    where the data type is a valid data type defined in ProjectSerializer.DefinedTypes
    and the unit_name is the SI unit used for the variable (e.g. m^2 for area)

    metadata can only be added to, not modified.
    param pairs in metadata can have their unit_name changed, but the data type can only be made bigger, not shrunk.
    For example, INT can be modified to DOUBLE, but not the other way around.
    project_name can be freely modified.
    creation_date will remain constant and non-editable.
    """
    class Meta:
        db_table = "project"
    project_id = models.UUIDField(
        primary_key=True, default=uuid4, editable=False)
    creation_date = models.DateTimeField(
        auto_now=True, help_text="Date of Creation", editable=False)
    project_name = models.CharField(
        max_length=256, blank=False, help_text="Project Name")
    # parameters and their units
    metadata = models.JSONField(help_text="Set of Parameters and their units")
    deleted = models.BooleanField(default=False, blank=False)
    # add user foreign key later here


class GeneratedModel(models.Model):
    parameters = models.JSONField(
        help_text="Set of Parameters and their Values")
    assets = models.JSONField(help_text="Set of Asset Types and their URLs")
    project_key = models.ForeignKey(
        "project", on_delete=models.PROTECT, help_text="Foreign Key to Associated Model")
