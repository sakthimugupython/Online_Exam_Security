from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Teacher
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/questions/', views.teacher_questions, name='teacher_questions'),
    path('teacher/questions/add/', views.teacher_question_form, name='teacher_question_add'),
    path('teacher/questions/<int:pk>/edit/', views.teacher_question_form, name='teacher_question_edit'),
    path('teacher/questions/<int:pk>/delete/', views.teacher_question_delete, name='teacher_question_delete'),
    path('teacher/exams/', views.teacher_exams, name='teacher_exams'),
    path('teacher/exams/add/', views.teacher_exam_form, name='teacher_exam_add'),
    path('teacher/exams/<int:pk>/edit/', views.teacher_exam_form, name='teacher_exam_edit'),
    path('teacher/exams/<int:pk>/', views.teacher_exam_detail, name='teacher_exam_detail'),
    path('teacher/exams/<int:pk>/add-question/', views.teacher_exam_add_question, name='teacher_exam_add_question'),
    path('teacher/exams/<int:pk>/add-inline-question/', views.teacher_exam_add_inline_question, name='teacher_exam_add_inline_question'),
    path('teacher/exams/<int:pk>/remove-question/<int:eq_id>/', views.teacher_exam_remove_question, name='teacher_exam_remove_question'),
    path('teacher/exams/<int:pk>/publish/', views.teacher_exam_publish, name='teacher_exam_publish'),
    path('teacher/exams/<int:pk>/delete/', views.teacher_exam_delete, name='teacher_exam_delete'),
    path('teacher/exams/<int:pk>/results/', views.teacher_exam_results, name='teacher_exam_results'),
    path('teacher/grade/<int:attempt_id>/', views.teacher_grade_attempt, name='teacher_grade_attempt'),
    path('teacher/grade/save/<int:answer_id>/', views.teacher_save_grade, name='teacher_save_grade'),
    
    # Student
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/exam/<int:exam_id>/start/', views.student_start_exam, name='student_start_exam'),
    path('student/exam/<int:attempt_id>/', views.student_take_exam, name='student_take_exam'),
    path('student/result/<int:attempt_id>/', views.student_result, name='student_result'),
    
    # API
    path('api/exam/<int:attempt_id>/save-answer/', views.api_save_answer, name='api_save_answer'),
    path('api/exam/<int:attempt_id>/submit/', views.api_submit_exam, name='api_submit_exam'),
    path('api/exam/<int:attempt_id>/violation/', views.api_log_violation, name='api_log_violation'),
    path('api/exam/<int:attempt_id>/answers/', views.api_get_answers, name='api_get_answers'),
]
