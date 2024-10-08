from django.db import models
from django.db.models.signals import post_save
from django.contrib.postgres.indexes import GinIndex
from django.dispatch import receiver
from pydantic import BaseModel, ConfigDict
from typing import List, Dict
from uuid import uuid4


class MarkdownDocument(models.Model):
    """
    Represents any markdown data object resident on the database. Ranging from articles, to about pages, to general descriptions or any other miscellaneous text objects.
    """
    slug = models.TextField(help_text="Identifies the document", blank=False, unique=True, primary_key=True)
    text = models.TextField(help_text="Markdown text", blank=True)


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

    creation_date = models.DateTimeField(auto_now=True, help_text="Date of Creation", editable=True)
    project_name = models.CharField(max_length=256, blank=False, help_text="Project Name", primary_key=True)
    variable_metadata = models.JSONField(help_text="Set of variable parameters and their units", blank=False)
    output_metadata = models.JSONField(help_text="Set of output parameters and their units", blank=False)
    assets = models.JSONField(help_text="Set of asset names", blank=False)
    deleted = models.BooleanField(default=False, blank=False)
    # add user foreign key later here

    def __str__(self) -> str:
        return self.project_name


class GeneratedModel(models.Model):
    class Meta:
        db_table = "generated_model"
        indexes = [GinIndex(fields=['parameters'])]

    id = models.BigAutoField(primary_key=True, editable=False)
    scoped_id = models.IntegerField(blank=False)
    parameters = models.JSONField(help_text="set of variable parameters and their values", unique=True)
    output_parameters = models.JSONField(help_text="set of output parameters and their values", blank=True, null=True)
    project = models.ForeignKey(Project, to_field="project_name", on_delete=models.PROTECT, help_text="Foreign Key to Associated Project", blank=False)

    def __str__(self) -> str:
        return str(self.parameters | self.output_parameters) + ' -> ' + str(self.project)


class AssetFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    file = models.FileField(help_text="File associated with a generated model", blank=False, editable=False, upload_to="./assets")
    tag = models.CharField(max_length=30, help_text="File tag of the asset", blank=False, editable=False)
    generated_model = models.ForeignKey(GeneratedModel, on_delete=models.PROTECT, help_text="Foreign Key to Associated Generated Model", blank=False, related_name="files")

    def __str__(self) -> str:
        return self.tag + ' -> ' + str(self.generated_model)


class Caption(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tag_name: str
    display_name: str

class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    text: str

@receiver(post_save, sender=Project)
def create_metadata(sender, instance: Project, created=False, **kwargs):
    if created:
        ProjectMetadata.objects.create(project=instance, captions="{}", description="", human_name=instance.project_name)

class ProjectMetadata(models.Model):
    class Metadata(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        captions: List[Caption]
        description: Document
        human_name: str

    project = models.ForeignKey(
        Project, to_field="project_name", on_delete=models.CASCADE, help_text="Foreign Key to Associated Project", blank=False, primary_key=True
    )
    captions = models.JSONField(help_text="Set of captions to be displayed for the project", default="{}")
    description = models.ForeignKey(MarkdownDocument, on_delete=models.DO_NOTHING, help_text="Markdown description of the project")
    human_name = models.TextField(help_text="Human readable name of the project.", default="")
