from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from core.choices import ClassRoomStreamChoices, ClassRoomTitleChoices
from core.models.attendance import Attendance
from core.models.classroom import ClassRoom
from core.models.student import Student
from users.models import CustomUser


def make_student(email, classroom):
    # Saving the user triggers the signal that creates its Student profile
    user = CustomUser.objects.create_user(
        username=email.split("@")[0],
        first_name=email.split("@")[0],
        last_name="Pupil",
        sex=CustomUser.SexChoices.FEMALE,
        role=CustomUser.RoleChoices.STUDENT,
        email=email,
        password="12345678QQ",
    )
    student = Student.objects.get(user=user)
    student.classroom = classroom
    student.save()
    return student


@pytest.mark.django_db
class TestAttendanceViewSet:
    @pytest.fixture(autouse=True)
    def setup(self, setup_users):
        self.client = setup_users["client"]
        self.tokens = {
            "admin": setup_users["admin_token"],
            "teacher": setup_users["teacher_token"],
            "student": setup_users["student_token"],
            "unauthorized": "",
        }
        self.classroom = ClassRoom.objects.create(
            title=ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_1,
            stream=ClassRoomStreamChoices.A,
        )
        self.other_classroom = ClassRoom.objects.create(
            title=ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_2,
            stream=ClassRoomStreamChoices.B,
        )
        self.students = [
            make_student(f"pupil{i}@example.com", self.classroom) for i in range(3)
        ]
        self.outsider = make_student("outsider@example.com", self.other_classroom)
        self.today = timezone.localdate()

    def bulk_mark(self, payload, user_type="teacher"):
        return self.client.post(
            reverse("core:attendance-bulk-mark"),
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Token {self.tokens[user_type]}",
        )

    def payload(self, statuses, date=None, classroom=None):
        return {
            "classroom": (classroom or self.classroom).id,
            "date": str(date or self.today),
            "records": [
                {"student": student.id, "status": status_value}
                for student, status_value in zip(self.students, statuses)
            ],
        }

    """ BULK MARK (POST) """

    @pytest.mark.parametrize(
        "user_type, expected_status",
        [
            ("admin", status.HTTP_200_OK),
            ("teacher", status.HTTP_200_OK),
            ("student", status.HTTP_403_FORBIDDEN),
            ("unauthorized", status.HTTP_401_UNAUTHORIZED),
        ],
    )
    def test_bulk_mark_permissions(self, user_type, expected_status):
        response = self.bulk_mark(self.payload(["PRESENT"] * 3), user_type)
        assert response.status_code == expected_status

    def test_bulk_mark_creates_records(self):
        response = self.bulk_mark(self.payload(["PRESENT", "ABSENT", "LATE"]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 3
        assert response.data["updated"] == 0
        assert Attendance.objects.count() == 3
        record = Attendance.objects.get(student=self.students[1])
        assert record.status == "ABSENT"
        assert record.classroom == self.classroom
        assert record.marked_by.email == "example@gmail.com"

    def test_re_marking_updates_instead_of_duplicating(self):
        self.bulk_mark(self.payload(["PRESENT", "PRESENT", "PRESENT"]))
        first_ids = set(Attendance.objects.values_list("id", flat=True))

        response = self.bulk_mark(self.payload(["PRESENT", "LEAVE", "PRESENT"]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 0
        assert response.data["updated"] == 3
        assert Attendance.objects.count() == 3
        assert set(Attendance.objects.values_list("id", flat=True)) == first_ids
        assert Attendance.objects.get(student=self.students[1]).status == "LEAVE"

    def test_admin_re_mark_records_new_marker(self):
        self.bulk_mark(self.payload(["PRESENT"] * 3))
        self.bulk_mark(self.payload(["ABSENT"] * 3), user_type="admin")
        assert set(
            Attendance.objects.values_list("marked_by__email", flat=True)
        ) == {"example2@gmail.com"}

    def test_same_student_on_another_day_is_a_new_record(self):
        self.bulk_mark(self.payload(["PRESENT"] * 3))
        response = self.bulk_mark(
            self.payload(["ABSENT"] * 3, date=self.today - timedelta(days=1))
        )
        assert response.data["created"] == 3
        assert Attendance.objects.count() == 6

    @pytest.mark.parametrize(
        "change, field",
        [
            ({"date": "FUTURE"}, "date"),
            ({"date": "27-10-2026"}, "date"),
            ({"records": [{"student": "FIRST", "status": "HOLIDAY"}]}, "records"),
            ({"records": []}, "records"),
            ({"records": "DUPLICATE"}, "records"),
            ({"records": "OUTSIDER"}, "records"),
            ({"records": [{"student": 999999, "status": "PRESENT"}]}, "records"),
            ({"classroom": 999999}, "classroom"),
        ],
    )
    def test_bulk_mark_validation(self, change, field):
        payload = self.payload(["PRESENT"] * 3)
        payload.update(change)
        if payload["date"] == "FUTURE":
            payload["date"] = str(self.today + timedelta(days=1))
        if payload["records"] == "DUPLICATE":
            first = {"student": self.students[0].id, "status": "PRESENT"}
            payload["records"] = [first, first]
        elif payload["records"] == "OUTSIDER":
            payload["records"] = [{"student": self.outsider.id, "status": "PRESENT"}]
        elif payload["records"] and payload["records"][0]["student"] == "FIRST":
            payload["records"][0]["student"] = self.students[0].id

        response = self.bulk_mark(payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert field in response.data
        assert Attendance.objects.count() == 0

    """ RECORDS (GET) """

    @pytest.mark.parametrize(
        "user_type, expected_status",
        [
            ("admin", status.HTTP_200_OK),
            ("teacher", status.HTTP_200_OK),
            ("student", status.HTTP_403_FORBIDDEN),
            ("unauthorized", status.HTTP_401_UNAUTHORIZED),
        ],
    )
    def test_list_permissions(self, user_type, expected_status):
        response = self.client.get(
            reverse("core:attendance-list"),
            HTTP_AUTHORIZATION=f"Token {self.tokens[user_type]}",
        )
        assert response.status_code == expected_status

    def test_filter_by_classroom_and_date(self):
        yesterday = self.today - timedelta(days=1)
        self.bulk_mark(self.payload(["PRESENT", "ABSENT", "LATE"]))
        self.bulk_mark(self.payload(["ABSENT"] * 3, date=yesterday))
        self.bulk_mark(
            {
                "classroom": self.other_classroom.id,
                "date": str(self.today),
                "records": [{"student": self.outsider.id, "status": "PRESENT"}],
            }
        )

        response = self.client.get(
            reverse("core:attendance-list"),
            {"classroom": self.classroom.id, "date": str(self.today)},
            HTTP_AUTHORIZATION=f"Token {self.tokens['teacher']}",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        assert {row["status"] for row in response.data} == {"PRESENT", "ABSENT", "LATE"}
        assert {row["classroom"] for row in response.data} == {self.classroom.id}
        assert {row["date"] for row in response.data} == {str(self.today)}
        assert response.data[0]["student_name"]
        assert response.data[0]["registration_number"]

    def test_filter_with_no_records_returns_empty_list(self):
        response = self.client.get(
            reverse("core:attendance-list"),
            {"classroom": self.classroom.id, "date": str(self.today)},
            HTTP_AUTHORIZATION=f"Token {self.tokens['teacher']}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_retrieve_record(self):
        self.bulk_mark(self.payload(["LATE"] * 3))
        record = Attendance.objects.first()
        response = self.client.get(
            reverse("core:attendance-detail", args=[record.id]),
            HTTP_AUTHORIZATION=f"Token {self.tokens['teacher']}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "LATE"

    def test_records_cannot_be_written_directly(self):
        response = self.client.post(
            reverse("core:attendance-list"),
            data={"student": self.students[0].id, "status": "PRESENT"},
            format="json",
            HTTP_AUTHORIZATION=f"Token {self.tokens['teacher']}",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_filter_students_by_classroom(self):
        response = self.client.get(
            reverse("core:students-list"),
            {"classroom": self.classroom.id},
            HTTP_AUTHORIZATION=f"Token {self.tokens['teacher']}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert {row["id"] for row in response.data} == {s.id for s in self.students}
