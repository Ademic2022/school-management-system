from django.db import models
from core.choices import AttendanceStatusChoices
from core.models.classroom import ClassRoom
from core.models.student import Student
from users.models import CustomUser


class Attendance(models.Model):
    """
    Django Model: Attendance

    Represents a student's attendance for a single day. There is at most one record
    per student per date; marking the same day again updates that record.

    Attributes:
        student (ForeignKey): The student the record belongs to.
        classroom (ForeignKey): The classroom the student was marked in. Stored on the record
            so past attendance stays with the class even if the student later changes class.
        date (DateField): The day the attendance is for.
        status (CharField): PRESENT, ABSENT, LATE or LEAVE.
        marked_by (ForeignKey): The teacher or admin user who last marked the record.
        created_at (DateTimeField): When the record was first created.
        updated_at (DateTimeField): When the record was last marked.

    Meta:
        constraints: Ensures one record per student and date.

    Example Usage:
        Attendance.objects.update_or_create(
            student=student, date=date,
            defaults={"classroom": classroom, "status": "PRESENT", "marked_by": user},
        )
    """

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance_records"
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatusChoices.choices)
    marked_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="marked_attendance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "student__user__last_name", "student__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"], name="unique_attendance_per_student_per_day"
            )
        ]
        indexes = [models.Index(fields=["classroom", "date"])]

    def __str__(self):
        return f"{self.student.user} - {self.date} - {self.status}"
