from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from core.choices import (
    ClassRoomStreamChoices,
    ClassRoomTitleChoices,
    ExamType,
    SubjectCodeChoices,
    SubjectTitleChoices,
)
from core.models.classroom import ClassRoom
from core.models.exams import Exam
from core.models.results import SubjectResult
from core.models.student import Student
from core.models.subject import Subject
from core.models.teacher import Teacher
from users.models import CustomUser

PASSWORD = "string@1234"

users = [
    {
        "username": "peter",
        "role": CustomUser.RoleChoices.ADMIN,
        "first_name": "Peter",
        "last_name": "Evance",
        "sex": CustomUser.SexChoices.MALE,
        "email": "admin@example.com",
    },
    {
        "username": "adewale",
        "role": CustomUser.RoleChoices.TEACHER,
        "first_name": "Adewale",
        "last_name": "Johnson",
        "sex": CustomUser.SexChoices.MALE,
        "email": "teacher@example.com",
    },
    {
        "username": "david",
        "role": CustomUser.RoleChoices.STUDENT,
        "first_name": "David",
        "last_name": "Thomas",
        "sex": CustomUser.SexChoices.MALE,
        "email": "student@example.com",
    },
    {
        "username": "amaka",
        "role": CustomUser.RoleChoices.STUDENT,
        "first_name": "Amaka",
        "last_name": "Obi",
        "sex": CustomUser.SexChoices.FEMALE,
        "email": "student2@example.com",
    },
]

subjects = [
    (SubjectTitleChoices.MATHEMATICS, SubjectCodeChoices.MTH),
    (SubjectTitleChoices.ENGLISH_LANGUAGE, SubjectCodeChoices.ENG),
    (SubjectTitleChoices.BIOLOGY, SubjectCodeChoices.BIO),
    (SubjectTitleChoices.COMPUTER_SCIENCE, SubjectCodeChoices.CPS),
]


class Command(BaseCommand):
    help = "Seed the database with demo users, classrooms, subjects, exams and results"

    @transaction.atomic
    def handle(self, *args, **options):
        accounts = {}
        for data in users:
            user = CustomUser.objects.filter(email=data["email"]).first()
            if user is None:
                # Saving the user triggers signals that create its Student/Teacher/Admin profile
                user = CustomUser.objects.create_user(password=PASSWORD, **data)
            if not user.is_approved:
                user.is_approved = True
                user.save()
            accounts[data["username"]] = user

        classroom, _ = ClassRoom.objects.get_or_create(
            title=ClassRoomTitleChoices.SENIOR_SECONDARY_SCHOOL_1,
            defaults={"capacity": 40, "stream": ClassRoomStreamChoices.A},
        )
        ClassRoom.objects.get_or_create(
            title=ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_1,
            defaults={"capacity": 40, "stream": ClassRoomStreamChoices.B},
        )

        subject_objs = [
            Subject.objects.get_or_create(title=title, code=code, class_room=classroom)[0]
            for title, code in subjects
        ]

        teacher = Teacher.objects.get(user=accounts["adewale"])
        teacher.classroom = classroom
        teacher.save()
        teacher.assigned_subjects.add(*subject_objs[:2])

        students = Student.objects.filter(
            user__in=[accounts["david"], accounts["amaka"]]
        )
        for student in students:
            student.classroom = classroom
            student.save()
            student.enrolled_subjects.add(*subject_objs)

        exam, _ = Exam.objects.get_or_create(
            exam_type=ExamType.MIDTERM,
            subject=subject_objs[0],
            defaults={
                "duration": timedelta(hours=2),
                "max_marks": 100,
                "instructions": "Answer all questions.",
            },
        )
        for student, marks in zip(students, [78, 85]):
            SubjectResult.objects.get_or_create(
                student=student,
                exam=exam,
                defaults={"marks_obtained": marks, "remarks": "Good work"},
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully"))
        for data in users:
            self.stdout.write(f"  {data['role']:<8} {data['email']}  /  {PASSWORD}")
