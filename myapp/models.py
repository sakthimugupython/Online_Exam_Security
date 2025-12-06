from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import random

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_student(self):
        return self.role == 'student'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Question(models.Model):
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('truefalse', 'True/False'),
        ('descriptive', 'Descriptive'),
        ('coding', 'Coding'),
    ]
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    text = models.TextField()
    option_a = models.CharField(max_length=500, blank=True, null=True)
    option_b = models.CharField(max_length=500, blank=True, null=True)
    option_c = models.CharField(max_length=500, blank=True, null=True)
    option_d = models.CharField(max_length=500, blank=True, null=True)
    correct_answer = models.CharField(max_length=500, blank=True, null=True)
    marks = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_question_type_display()}: {self.text[:50]}..."

    def get_options_list(self):
        if self.question_type == 'mcq':
            return [
                ('A', self.option_a),
                ('B', self.option_b),
                ('C', self.option_c),
                ('D', self.option_d),
            ]
        elif self.question_type == 'truefalse':
            return [('True', 'True'), ('False', 'False')]
        return []


class Exam(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def total_marks(self):
        return sum(eq.marks for eq in self.exam_questions.all())


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    marks = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ['exam', 'question']

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"


class PublishedExam(models.Model):
    """Snapshot of exam when published - immutable"""
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='published_snapshot')
    snapshot_data = models.JSONField()
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Published: {self.exam.title}"

    @classmethod
    def create_snapshot(cls, exam):
        questions_data = []
        for eq in exam.exam_questions.all():
            q = eq.question
            questions_data.append({
                'id': eq.id,
                'question_id': q.id,
                'type': q.question_type,
                'text': q.text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_answer': q.correct_answer,
                'marks': eq.marks,
                'order': eq.order,
            })
        snapshot = {
            'title': exam.title,
            'description': exam.description,
            'duration_minutes': exam.duration_minutes,
            'start_time': exam.start_time.isoformat() if exam.start_time else None,
            'end_time': exam.end_time.isoformat() if exam.end_time else None,
            'total_marks': exam.total_marks,
            'questions': questions_data,
        }
        published, created = cls.objects.update_or_create(
            exam=exam,
            defaults={'snapshot_data': snapshot}
        )
        return published


class ExamAttempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('auto_submitted', 'Auto Submitted'),
        ('graded', 'Graded'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    question_order = models.JSONField(default=list)  # Randomized order for this attempt
    total_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ['student', 'exam']

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"

    def generate_question_order(self):
        if self.exam.is_published and hasattr(self.exam, 'published_snapshot'):
            questions = self.exam.published_snapshot.snapshot_data['questions']
            order = list(range(len(questions)))
            if self.exam.randomize_questions:
                random.shuffle(order)
            self.question_order = order
            self.save()


class Answer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    exam_question_id = models.IntegerField()  # References snapshot question
    answer_text = models.TextField(blank=True, null=True)
    is_marked_for_review = models.BooleanField(default=False)
    is_correct = models.BooleanField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_answers')
    graded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['attempt', 'exam_question_id']

    def __str__(self):
        return f"Answer for Q{self.exam_question_id} by {self.attempt.student.username}"


class ProctoringLog(models.Model):
    VIOLATION_TYPES = [
        ('tab_switch', 'Tab Switch'),
        ('fullscreen_exit', 'Fullscreen Exit'),
        ('face_not_detected', 'Face Not Detected'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('copy_attempt', 'Copy Attempt'),
        ('paste_attempt', 'Paste Attempt'),
        ('right_click', 'Right Click Attempt'),
    ]
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='proctoring_logs')
    violation_type = models.CharField(max_length=30, choices=VIOLATION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.attempt.student.username}"
