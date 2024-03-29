from django.db import models
from core.choices import *


class ClassRoom(models.Model):

    """
    Django Model: ClassRoom

    Represents a classroom with specific attributes.

    Attributes:
        title (CharField): Title of the classroom, chosen from predefined choices.
        code (CharField): Code assigned based on the title, automatically updated using 'update_class_code' method.
        capacity (PositiveIntegerField): Maximum capacity of the classroom, default is 1.
        stream (CharField): Stream of the classroom, chosen from predefined choices.

    Methods:
        update_class_code(): Updates the 'code' based on the 'title' using a predefined mapping.

    Notes:
        - 'choices' module is imported from 'core.choices'.
        - 'save' method is overridden to ensure the 'code' is updated on save.

    Example Usage:
        classroom_instance = ClassRoom.objects.create(title='...', stream='...')
        print(classroom_instance.title)
        print(classroom_instance.code)
        print(classroom_instance.capacity)
        print(classroom_instance.stream)
    """

    title = models.CharField(
        max_length=30, choices=ClassRoomTitleChoices.choices, unique=True
    )
    code = models.CharField(
        max_length=10,
        choices=ClassRoomCodeChoices.choices,
        blank=True,
        null=True,
        unique=True,
    )
    capacity = models.PositiveIntegerField(default=1)
    stream = models.CharField(max_length=1, choices=ClassRoomStreamChoices.choices)

    def update_class_code(self):
        title_to_code_mapping = {
            ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_1: ClassRoomCodeChoices.JSS_1,
            ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_2: ClassRoomCodeChoices.JSS_2,
            ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_3: ClassRoomCodeChoices.JSS_3,
            ClassRoomTitleChoices.SENIOR_SECONDARY_SCHOOL_1: ClassRoomCodeChoices.SSS_1,
            ClassRoomTitleChoices.SENIOR_SECONDARY_SCHOOL_2: ClassRoomCodeChoices.SSS_2,
            ClassRoomTitleChoices.SENIOR_SECONDARY_SCHOOL_3: ClassRoomCodeChoices.SSS_3,
        }

        self.code = title_to_code_mapping.get(self.title, self.code)
        return self.code

    def save(self, *args, **kwargs):
        if self.id is None:
            self.id = self.pk
        self.code = self.update_class_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
