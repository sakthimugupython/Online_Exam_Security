from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Question, Exam, ExamQuestion,
    PublishedExam, ExamAttempt, Answer, ProctoringLog
)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at', 'updated_at']


class QuestionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_type', 'text', 'marks', 'created_at']


class ExamQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    question_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExamQuestion
        fields = ['id', 'question', 'question_id', 'order', 'marks']


class ExamSerializer(serializers.ModelSerializer):
    exam_questions = ExamQuestionSerializer(many=True, read_only=True)
    total_marks = serializers.ReadOnlyField()

    class Meta:
        model = Exam
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at']


class ExamListSerializer(serializers.ModelSerializer):
    total_marks = serializers.ReadOnlyField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'title', 'duration_minutes', 'start_time', 'end_time', 
                  'is_published', 'total_marks', 'question_count']

    def get_question_count(self, obj):
        return obj.exam_questions.count()


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'exam_question_id', 'answer_text', 'is_marked_for_review', 
                  'is_correct', 'score', 'updated_at']
        read_only_fields = ['is_correct', 'score']


class ExamAttemptSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)

    class Meta:
        model = ExamAttempt
        fields = ['id', 'exam', 'exam_title', 'started_at', 'submitted_at', 
                  'status', 'question_order', 'total_score', 'max_score', 'answers']


class ProctoringLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctoringLog
        fields = ['id', 'violation_type', 'timestamp', 'details']
        read_only_fields = ['timestamp']


class SaveAnswerSerializer(serializers.Serializer):
    exam_question_id = serializers.IntegerField()
    answer_text = serializers.CharField(allow_blank=True, allow_null=True)
    is_marked_for_review = serializers.BooleanField(default=False)


class GradeAnswerSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
