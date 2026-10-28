from core.models.attendance import Attendance
from core.models.exams import Exam
from core.models.results import SubjectResult
from core.models.subject import Subject
from core.models.student import Student
from django_filters import rest_framework as filters


class StudentFilter(filters.FilterSet):
    """
     StudentFilter:
    - Filters students based on user information using a case-insensitive match.
    - Filters students by classroom.
    """

    user = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Student
        fields = ["user", "classroom"]


class SubjectFilter(filters.FilterSet):
    """
     SubjectFilter:
    - Filters subjects based on the associated class room.
    """

    class Meta:
        model = Subject
        fields = ["class_room"]


class ExamFilter(filters.FilterSet):
    """
     ExamFilter:
    - Filters exams based on exam type and associated subject.
    """

    class Meta:
        model = Exam
        fields = ("exam_type", "subject")


class SubjectResultFilter(filters.FilterSet):
    """
     SubjectResultFilter:
    - Filters subject results based on the associated student and exam.
    """

    class Meta:
        model = SubjectResult
        fields = ("student", "exam")


class AttendanceFilter(filters.FilterSet):
    """
     AttendanceFilter:
    - Filters attendance records by classroom, date, student and status.
    """

    class Meta:
        model = Attendance
        fields = ("classroom", "date", "student", "status")
