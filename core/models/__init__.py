# Import every model so Django registers them when it loads the core.models package.
# Without this, a model only exists once some other module happens to import it,
# and makemigrations reports "No changes detected" for new models.
from core.models.admin import Admin
from core.models.classroom import ClassRoom
from core.models.subject import Subject
from core.models.student import Student
from core.models.teacher import Teacher
from core.models.exams import Exam
from core.models.results import SubjectResult
from core.models.attendance import Attendance
