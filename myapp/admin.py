from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, Question, Exam, ExamQuestion, 
    PublishedExam, ExamAttempt, Answer, ProctoringLog
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')

    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, 'profile') else '-'
    get_role.short_description = 'Role'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_type', 'text_preview', 'teacher', 'marks', 'created_at')
    list_filter = ('question_type', 'teacher')
    search_fields = ('text',)

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question'


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'duration_minutes', 'start_time', 'end_time', 'is_published')
    list_filter = ('is_published', 'teacher')
    search_fields = ('title',)
    inlines = [ExamQuestionInline]


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'question', 'order', 'marks')
    list_filter = ('exam',)


@admin.register(PublishedExam)
class PublishedExamAdmin(admin.ModelAdmin):
    list_display = ('exam', 'published_at')
    readonly_fields = ('snapshot_data',)


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'status', 'started_at', 'submitted_at', 'total_score')
    list_filter = ('status', 'exam')
    search_fields = ('student__username',)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'exam_question_id', 'is_correct', 'score', 'is_marked_for_review')
    list_filter = ('is_correct', 'is_marked_for_review')


@admin.register(ProctoringLog)
class ProctoringLogAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'violation_type', 'timestamp')
    list_filter = ('violation_type',)
    search_fields = ('attempt__student__username',)
