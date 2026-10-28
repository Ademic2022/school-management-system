import random
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
Role = CustomUser.RoleChoices
Sex = CustomUser.SexChoices

# Each classroom gets one teacher and a list of students.
# The first teacher and student are the easy-to-remember demo logins.
classrooms = [
    {
        "title": ClassRoomTitleChoices.SENIOR_SECONDARY_SCHOOL_1,
        "stream": ClassRoomStreamChoices.A,
        "teacher": ("Test", "Teacher", Sex.MALE, "teacher@example.com"),
        "students": [
            ("Test", "Student", Sex.MALE, "student@example.com"),
            ("John", "Smith", Sex.MALE),
            ("Jane", "Doe", Sex.FEMALE),
            ("Alex", "Johnson", Sex.MALE),
            ("Emily", "Brown", Sex.FEMALE),
            ("Michael", "Davis", Sex.MALE),
            ("Sarah", "Wilson", Sex.FEMALE),
            ("Daniel", "Moore", Sex.MALE),
            ("Laura", "Taylor", Sex.FEMALE),
            ("Chris", "Anderson", Sex.MALE),
        ],
        "subjects": [
            (SubjectTitleChoices.MATHEMATICS, SubjectCodeChoices.MTH),
            (SubjectTitleChoices.ENGLISH_LANGUAGE, SubjectCodeChoices.ENG),
            (SubjectTitleChoices.BIOLOGY, SubjectCodeChoices.BIO),
            (SubjectTitleChoices.PHYSICS, SubjectCodeChoices.PHY),
        ],
    },
    {
        "title": ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_2,
        "stream": ClassRoomStreamChoices.B,
        "teacher": ("Mary", "Example", Sex.FEMALE, "teacher2@example.com"),
        "students": [
            ("Tom", "Sample", Sex.MALE),
            ("Anna", "Placeholder", Sex.FEMALE),
            ("Peter", "Jones", Sex.MALE),
            ("Lucy", "Miller", Sex.FEMALE),
            ("Mark", "Thomas", Sex.MALE),
            ("Grace", "White", Sex.FEMALE),
            ("Paul", "Harris", Sex.MALE),
        ],
        "subjects": [
            (SubjectTitleChoices.MATHEMATICS, SubjectCodeChoices.MTH),
            (SubjectTitleChoices.ENGLISH_LANGUAGE, SubjectCodeChoices.ENG),
            (SubjectTitleChoices.SOCIAL_STUDIES, SubjectCodeChoices.SOS),
            (SubjectTitleChoices.COMPUTER_SCIENCE, SubjectCodeChoices.CPS),
        ],
    },
    {
        "title": ClassRoomTitleChoices.JUNIOR_SECONDARY_SCHOOL_1,
        "stream": ClassRoomStreamChoices.C,
        "teacher": ("David", "Testman", Sex.MALE, "teacher3@example.com"),
        "students": [
            ("Kate", "Clark", Sex.FEMALE),
            ("Sam", "Lewis", Sex.MALE),
            ("Nina", "Walker", Sex.FEMALE),
            ("Ben", "Hall", Sex.MALE),
            ("Olivia", "Young", Sex.FEMALE),
        ],
        "subjects": [
            (SubjectTitleChoices.MATHEMATICS, SubjectCodeChoices.MTH),
            (SubjectTitleChoices.ENGLISH_LANGUAGE, SubjectCodeChoices.ENG),
            (SubjectTitleChoices.CIVIC_EDUCATION, SubjectCodeChoices.CVE),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with fake users, classrooms, subjects, exams and results"

    def get_or_create_user(self, first_name, last_name, sex, role, email):
        user = CustomUser.objects.filter(email=email).first()
        if user is None:
            # Saving the user triggers signals that create its Student/Teacher/Admin profile
            user = CustomUser.objects.create_user(
                username=email.split("@")[0],
                first_name=first_name,
                last_name=last_name,
                sex=sex,
                role=role,
                email=email,
                password=PASSWORD,
            )
        if not user.is_approved:
            user.is_approved = True
            user.save()
        return user

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)  # fixed seed so marks are the same on every run
        self.get_or_create_user("Test", "Admin", Sex.FEMALE, Role.ADMIN, "admin@example.com")

        for room in classrooms:
            classroom, _ = ClassRoom.objects.get_or_create(
                title=room["title"],
                defaults={"capacity": 40, "stream": room["stream"]},
            )
            subject_objs = [
                Subject.objects.get_or_create(title=title, code=code, class_room=classroom)[0]
                for title, code in room["subjects"]
            ]

            first, last, sex, email = room["teacher"]
            teacher = Teacher.objects.get(
                user=self.get_or_create_user(first, last, sex, Role.TEACHER, email)
            )
            teacher.classroom = classroom
            teacher.save()
            teacher.assigned_subjects.add(*subject_objs)

            exam, _ = Exam.objects.get_or_create(
                exam_type=ExamType.MIDTERM,
                subject=subject_objs[0],
                defaults={
                    "duration": timedelta(hours=2),
                    "max_marks": 100,
                    "instructions": "Answer all questions.",
                },
            )

            for entry in room["students"]:
                first, last, sex = entry[:3]
                email = entry[3] if len(entry) > 3 else f"{first}.{last}@example.com".lower()
                student = Student.objects.get(
                    user=self.get_or_create_user(first, last, sex, Role.STUDENT, email)
                )
                student.classroom = classroom
                student.save()
                student.enrolled_subjects.add(*subject_objs)
                SubjectResult.objects.get_or_create(
                    student=student,
                    exam=exam,
                    defaults={"marks_obtained": rng.randint(45, 98), "remarks": "Good work"},
                )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully"))
        self.stdout.write(f"All accounts use the password: {PASSWORD}")
        self.stdout.write("  Admin    admin@example.com")
        self.stdout.write("  Teacher  teacher@example.com (also teacher2@, teacher3@)")
        self.stdout.write("  Student  student@example.com (others: firstname.lastname@example.com)")
