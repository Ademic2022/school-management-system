from django.utils import timezone
from core.choices import AttendanceStatusChoices
from core.models.attendance import Attendance
from core.models.results import SubjectResult
from core.models.exams import Exam
from users.models import CustomUser
from core.models.admin import Admin
from core.models.student import Student
from core.models.teacher import Teacher
from core.models.classroom import ClassRoom
from core.models.subject import Subject
from rest_framework.serializers import (
    ChoiceField,
    DateField,
    IntegerField,
    ListField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    Serializer,
    ValidationError,
)
from users.serializers import CustomUserSerializer, CustomUserSerializer2


class SubjectSerializer(ModelSerializer):
    """
    Django Model Serializer: SubjectSerializer

    Serializes Subject model fields including id, title, code, class_room, and added_at.
    """

    class_room = PrimaryKeyRelatedField(queryset=ClassRoom.objects.all())

    class Meta:
        model = Subject
        fields = ["id", "title", "code", "class_room", "added_at"]


class ClassRoomSerializer(ModelSerializer):
    """
    Django Model Serializer: ClassRoomSerializer

    Serializes ClassRoom model fields including id, title, code, capacity, and stream with nested representation.
    """

    class Meta:
        depth = True
        model = ClassRoom
        fields = ["id", "title", "code", "capacity", "stream"]


class TeacherSerializer(ModelSerializer):
    """
    Django Model Serializer: TeacherSerializer

    Serializes Teacher model fields including id, user (serialized with CustomUserSerializer),
    classroom, created_at, and assigned_subjects with one level of nested representation.
    """

    user = CustomUserSerializer()

    class Meta:
        depth = 1
        model = Teacher
        fields = ["id", "user", "classroom", "created_at", "assigned_subjects"]


class TeacherSerializer2(ModelSerializer):
    """
    Django Model Serializer: TeacherSerializer2

    Serializes Teacher model fields including id, user (serialized with CustomUserSerializer),
    classroom, created_at, and assigned_subjects without nested representation.
    """

    user = CustomUserSerializer()

    class Meta:
        model = Teacher
        fields = ["id", "user", "classroom", "created_at", "assigned_subjects"]


class StudentSerializer(ModelSerializer):
    """
    Django Model Serializer: StudentSerializer

    Serializes Student model fields including id, user (serialized with CustomUserSerializer),
    classroom, created_at, enrolled_subjects, and registration_number with one level of nested representation.
    """

    user = CustomUserSerializer()

    class Meta:
        depth = 1
        model = Student
        fields = [
            "id",
            "user",
            "classroom",
            "created_at",
            "enrolled_subjects",
            "registration_number",
        ]


class StudentSerializer2(ModelSerializer):
    """
    Django Model Serializer: StudentSerializer2

    Serializes Student model fields including id, user (serialized with CustomUserSerializer),
    classroom, created_at, enrolled_subjects, and registration_number without nested representation.
    """

    user = CustomUserSerializer()

    class Meta:
        model = Student
        fields = [
            "id",
            "user",
            "classroom",
            "created_at",
            "enrolled_subjects",
            "registration_number",
        ]


class AdminSerializer(ModelSerializer):
    """
    Django Model Serializer: AdminSerializer

    Serializes Admin model fields including user and created.
    """

    class Meta:
        model = Admin
        fields = ["user", "created"]


class ExamSerializer(ModelSerializer):
    """
    Django Model Serializer: ExamSerializer

    Serializes Exam model fields including exam_type, subject, scheduled_date, duration,
    max_marks, and instructions."""

    class Meta:
        model = Exam
        fields = (
            "exam_type",
            "subject",
            "scheduled_date",
            "duration",
            "max_marks",
            "instructions",
        )


class SubjectResultSerializer(ModelSerializer):
    """
    Django Model Serializer: SubjectResultSerializer

    Serializes SubjectResult model fields including student, exam, marks_obtained, and remarks.
    """

    class Meta:
        model = SubjectResult
        fields = ("student", "exam", "marks_obtained", "remarks")


class AttendanceSerializer(ModelSerializer):
    """
    Django Model Serializer: AttendanceSerializer

    Read-only representation of an Attendance record, with the student's name and
    registration number so the record page doesn't need a second request per student.
    """

    student_name = ReadOnlyField(source="student.user.get_full_name")
    registration_number = ReadOnlyField(source="student.registration_number")
    marked_by_name = ReadOnlyField(source="marked_by.get_full_name", default=None)

    class Meta:
        model = Attendance
        fields = (
            "id",
            "student",
            "student_name",
            "registration_number",
            "classroom",
            "date",
            "status",
            "marked_by",
            "marked_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AttendanceEntrySerializer(Serializer):
    """
    Serializer: AttendanceEntrySerializer

    One student's status inside a bulk_mark request.
    """

    student = IntegerField()
    status = ChoiceField(choices=AttendanceStatusChoices.choices)


class BulkAttendanceSerializer(Serializer):
    """
    Serializer: BulkAttendanceSerializer

    Validates a bulk_mark request: a classroom, a date that is not in the future,
    and a non-empty list of student statuses. Every student must belong to the
    classroom and may appear only once.
    """

    classroom = PrimaryKeyRelatedField(queryset=ClassRoom.objects.all())
    date = DateField()
    records = ListField(child=AttendanceEntrySerializer(), allow_empty=False)

    def validate_date(self, value):
        if value > timezone.localdate():
            raise ValidationError("Attendance cannot be marked for a future date.")
        return value

    def validate(self, attrs):
        student_ids = [record["student"] for record in attrs["records"]]
        duplicates = sorted({sid for sid in student_ids if student_ids.count(sid) > 1})
        if duplicates:
            raise ValidationError(
                {"records": f"Students listed more than once: {duplicates}"}
            )

        students = Student.objects.in_bulk(student_ids)
        not_in_class = sorted(
            sid
            for sid in student_ids
            if sid not in students or students[sid].classroom_id != attrs["classroom"].id
        )
        if not_in_class:
            raise ValidationError(
                {"records": f"Students not found in this classroom: {not_in_class}"}
            )

        attrs["students"] = students
        return attrs
