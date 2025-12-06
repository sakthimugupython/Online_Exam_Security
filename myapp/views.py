from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
import json

from .models import (
    UserProfile, Question, Exam, ExamQuestion,
    PublishedExam, ExamAttempt, Answer, ProctoringLog
)
from .serializers import (
    QuestionSerializer, QuestionListSerializer,
    ExamSerializer, ExamListSerializer, ExamQuestionSerializer,
    ExamAttemptSerializer, AnswerSerializer, ProctoringLogSerializer,
    SaveAnswerSerializer, GradeAnswerSerializer
)


def is_teacher(user):
    return hasattr(user, 'profile') and user.profile.is_teacher


def is_student(user):
    return hasattr(user, 'profile') and user.profile.is_student


# Auth Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard_redirect')
        return render(request, 'myapp/login.html', {'error': 'Invalid credentials'})
    return render(request, 'myapp/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    return redirect('student_dashboard')


# Teacher Views
@login_required
def teacher_dashboard(request):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    exams = Exam.objects.filter(teacher=request.user).order_by('-created_at')
    questions_count = Question.objects.filter(teacher=request.user).count()
    published_exams = exams.filter(is_published=True).count()
    total_attempts = ExamAttempt.objects.filter(exam__teacher=request.user).count()
    
    context = {
        'exams': exams[:5],
        'questions_count': questions_count,
        'published_exams': published_exams,
        'total_attempts': total_attempts,
    }
    return render(request, 'myapp/teacher/dashboard.html', context)


@login_required
def teacher_questions(request):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    questions = Question.objects.filter(teacher=request.user).order_by('-created_at')
    search = request.GET.get('search', '')
    qtype = request.GET.get('type', '')
    
    if search:
        questions = questions.filter(text__icontains=search)
    if qtype:
        questions = questions.filter(question_type=qtype)
    
    return render(request, 'myapp/teacher/questions.html', {
        'questions': questions,
        'search': search,
        'qtype': qtype,
    })


@login_required
def teacher_question_form(request, pk=None):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    question = None
    if pk:
        question = get_object_or_404(Question, pk=pk, teacher=request.user)
    
    if request.method == 'POST':
        data = {
            'question_type': request.POST.get('question_type'),
            'text': request.POST.get('text'),
            'option_a': request.POST.get('option_a'),
            'option_b': request.POST.get('option_b'),
            'option_c': request.POST.get('option_c'),
            'option_d': request.POST.get('option_d'),
            'correct_answer': request.POST.get('correct_answer'),
            'marks': request.POST.get('marks', 1),
        }
        
        if question:
            for key, value in data.items():
                setattr(question, key, value)
            question.save()
        else:
            question = Question.objects.create(teacher=request.user, **data)
        
        return redirect('teacher_questions')
    
    return render(request, 'myapp/teacher/question_form.html', {'question': question})


@login_required
@require_POST
def teacher_question_delete(request, pk):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    question = get_object_or_404(Question, pk=pk, teacher=request.user)
    question.delete()
    return JsonResponse({'success': True})


@login_required
def teacher_exams(request):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    exams = Exam.objects.filter(teacher=request.user).order_by('-created_at')
    return render(request, 'myapp/teacher/exams.html', {'exams': exams})


@login_required
def teacher_exam_form(request, pk=None):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    exam = None
    if pk:
        exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description', ''),
            'duration_minutes': int(request.POST.get('duration_minutes', 60)),
            'randomize_questions': request.POST.get('randomize_questions') == 'on',
            'randomize_options': request.POST.get('randomize_options') == 'on',
        }
        
        if exam:
            for key, value in data.items():
                setattr(exam, key, value)
            exam.save()
        else:
            exam = Exam.objects.create(teacher=request.user, **data)
        
        return redirect('teacher_exam_detail', pk=exam.pk)
    
    return render(request, 'myapp/teacher/exam_form.html', {'exam': exam})


@login_required
@require_POST
def teacher_exam_add_inline_question(request, pk):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    if exam.is_published:
        return JsonResponse({'error': 'Cannot modify published exam'}, status=400)
    
    # Create question
    question = Question.objects.create(
        teacher=request.user,
        question_type=request.POST.get('question_type'),
        text=request.POST.get('text'),
        option_a=request.POST.get('option_a', ''),
        option_b=request.POST.get('option_b', ''),
        option_c=request.POST.get('option_c', ''),
        option_d=request.POST.get('option_d', ''),
        correct_answer=request.POST.get('correct_answer'),
        marks=int(request.POST.get('marks', 1))
    )
    
    # Add to exam
    order = exam.exam_questions.count() + 1
    eq = ExamQuestion.objects.create(exam=exam, question=question, order=order, marks=question.marks)
    
    return JsonResponse({
        'success': True,
        'question_id': question.id,
        'exam_question_id': eq.id,
        'order': order
    })


@login_required
def teacher_exam_detail(request, pk):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    # Exclude questions already in this exam AND questions used in any other exam
    used_question_ids = ExamQuestion.objects.values_list('question_id', flat=True)
    available_questions = Question.objects.filter(teacher=request.user).exclude(
        id__in=used_question_ids
    )
    
    return render(request, 'myapp/teacher/exam_detail.html', {
        'exam': exam,
        'available_questions': available_questions,
    })


@login_required
@require_POST
def teacher_exam_add_question(request, pk):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    if exam.is_published:
        return JsonResponse({'error': 'Cannot modify published exam'}, status=400)
    
    question_id = request.POST.get('question_id')
    marks = request.POST.get('marks', 1)
    question = get_object_or_404(Question, pk=question_id, teacher=request.user)
    
    order = exam.exam_questions.count() + 1
    ExamQuestion.objects.create(exam=exam, question=question, order=order, marks=marks)
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def teacher_exam_remove_question(request, pk, eq_id):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    if exam.is_published:
        return JsonResponse({'error': 'Cannot modify published exam'}, status=400)
    
    eq = get_object_or_404(ExamQuestion, pk=eq_id, exam=exam)
    eq.delete()
    
    # Reorder remaining questions
    for i, eq in enumerate(exam.exam_questions.all(), 1):
        eq.order = i
        eq.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def teacher_exam_publish(request, pk):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    
    if exam.exam_questions.count() == 0:
        return JsonResponse({'error': 'Cannot publish exam without questions'}, status=400)
    
    PublishedExam.create_snapshot(exam)
    exam.is_published = True
    exam.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def teacher_exam_delete(request, pk):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    
    if exam.is_published:
        return JsonResponse({'error': 'Cannot delete published exam'}, status=400)
    
    exam.delete()
    return JsonResponse({'success': True, 'redirect': '/teacher/exams/'})


@login_required
def teacher_exam_results(request, pk):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)
    attempts = ExamAttempt.objects.filter(exam=exam).select_related('student')
    
    stats = {
        'total_attempts': attempts.count(),
        'submitted': attempts.filter(status__in=['submitted', 'auto_submitted', 'graded']).count(),
        'avg_score': attempts.filter(total_score__isnull=False).aggregate(Avg('total_score'))['total_score__avg'],
        'violations': ProctoringLog.objects.filter(attempt__exam=exam).count(),
    }
    
    return render(request, 'myapp/teacher/exam_results.html', {
        'exam': exam,
        'attempts': attempts,
        'stats': stats,
    })


@login_required
def teacher_grade_attempt(request, attempt_id):
    if not is_teacher(request.user):
        return redirect('student_dashboard')
    
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, exam__teacher=request.user)
    snapshot = attempt.exam.published_snapshot.snapshot_data
    
    answers_with_questions = []
    for q in snapshot['questions']:
        answer = attempt.answers.filter(exam_question_id=q['id']).first()
        # Create empty answer object for display if none exists
        if not answer:
            answer = Answer.objects.create(
                attempt=attempt,
                exam_question_id=q['id'],
                answer_text=''
            )
        answers_with_questions.append({
            'question': q,
            'answer': answer,
        })
    
    violations = ProctoringLog.objects.filter(attempt=attempt)
    
    return render(request, 'myapp/teacher/grade_attempt.html', {
        'attempt': attempt,
        'answers_with_questions': answers_with_questions,
        'violations': violations,
    })


@login_required
@require_POST
def teacher_save_grade(request, answer_id):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    answer = get_object_or_404(Answer, pk=answer_id, attempt__exam__teacher=request.user)
    score = request.POST.get('score')
    
    answer.score = Decimal(score)
    answer.graded_by = request.user
    answer.graded_at = timezone.now()
    answer.save()
    
    # Recalculate total score
    attempt = answer.attempt
    total = attempt.answers.filter(score__isnull=False).aggregate(Sum('score'))['score__sum'] or 0
    attempt.total_score = total
    
    # Check if all answers are graded
    snapshot = attempt.exam.published_snapshot.snapshot_data
    if attempt.answers.filter(score__isnull=False).count() == len(snapshot['questions']):
        attempt.status = 'graded'
    
    attempt.save()
    
    return JsonResponse({'success': True, 'total_score': float(attempt.total_score)})


# Student Views
@login_required
def student_dashboard(request):
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    
    # Available exams (published, not attempted)
    attempted_exam_ids = ExamAttempt.objects.filter(student=request.user).values_list('exam_id', flat=True)
    available_exams = Exam.objects.filter(
        is_published=True
    ).exclude(id__in=attempted_exam_ids).order_by('-created_at')
    
    # My attempts
    my_attempts = ExamAttempt.objects.filter(student=request.user).select_related('exam').order_by('-started_at')
    
    return render(request, 'myapp/student/dashboard.html', {
        'available_exams': available_exams,
        'my_attempts': my_attempts,
    })


@login_required
def student_start_exam(request, exam_id):
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)
    
    # Check if already attempted
    attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()
    
    if attempt:
        if attempt.status in ['submitted', 'auto_submitted', 'graded']:
            return redirect('student_result', attempt_id=attempt.id)
        return redirect('student_take_exam', attempt_id=attempt.id)
    
    # Create new attempt
    attempt = ExamAttempt.objects.create(
        student=request.user,
        exam=exam,
        max_score=exam.total_marks
    )
    attempt.generate_question_order()
    
    return redirect('student_take_exam', attempt_id=attempt.id)


@login_required
def student_take_exam(request, attempt_id):
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    
    if attempt.status in ['submitted', 'auto_submitted', 'graded']:
        return redirect('student_result', attempt_id=attempt.id)
    
    exam = attempt.exam
    snapshot = exam.published_snapshot.snapshot_data
    
    # Calculate remaining time
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining_seconds = max(0, exam.duration_minutes * 60 - elapsed)
    
    if remaining_seconds <= 0:
        # Auto submit
        attempt.status = 'auto_submitted'
        attempt.submitted_at = timezone.now()
        attempt.save()
        auto_grade_attempt(attempt)
        return redirect('student_result', attempt_id=attempt.id)
    
    # Get questions in order
    ordered_questions = []
    for idx in attempt.question_order:
        q = snapshot['questions'][idx]
        answer = attempt.answers.filter(exam_question_id=q['id']).first()
        ordered_questions.append({
            'question': q,
            'answer': answer,
            'index': len(ordered_questions),
        })
    
    return render(request, 'myapp/student/take_exam.html', {
        'attempt': attempt,
        'exam': exam,
        'questions': ordered_questions,
        'remaining_seconds': int(remaining_seconds),
        'snapshot': snapshot,
    })


def auto_grade_attempt(attempt):
    """Auto-grade MCQ and True/False questions"""
    snapshot = attempt.exam.published_snapshot.snapshot_data
    total_score = Decimal('0')
    
    for q in snapshot['questions']:
        answer = attempt.answers.filter(exam_question_id=q['id']).first()
        if not answer:
            continue
        
        if q['type'] in ['mcq', 'truefalse']:
            is_correct = answer.answer_text == q['correct_answer']
            answer.is_correct = is_correct
            answer.score = Decimal(q['marks']) if is_correct else Decimal('0')
            answer.save()
            total_score += answer.score
    
    attempt.total_score = total_score
    attempt.save()


@login_required
def student_result(request, attempt_id):
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    
    if attempt.status == 'in_progress':
        return redirect('student_take_exam', attempt_id=attempt.id)
    
    snapshot = attempt.exam.published_snapshot.snapshot_data
    
    answers_with_questions = []
    for q in snapshot['questions']:
        answer = attempt.answers.filter(exam_question_id=q['id']).first()
        answers_with_questions.append({
            'question': q,
            'answer': answer,
        })
    
    return render(request, 'myapp/student/result.html', {
        'attempt': attempt,
        'answers_with_questions': answers_with_questions,
    })


# API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_save_answer(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    
    if attempt.status != 'in_progress':
        return Response({'error': 'Exam already submitted'}, status=400)
    
    serializer = SaveAnswerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    data = serializer.validated_data
    
    answer, created = Answer.objects.update_or_create(
        attempt=attempt,
        exam_question_id=data['exam_question_id'],
        defaults={
            'answer_text': data['answer_text'],
            'is_marked_for_review': data['is_marked_for_review'],
        }
    )
    
    return Response(AnswerSerializer(answer).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_exam(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    
    if attempt.status != 'in_progress':
        return Response({'error': 'Exam already submitted'}, status=400)
    
    attempt.status = 'submitted'
    attempt.submitted_at = timezone.now()
    attempt.save()
    
    auto_grade_attempt(attempt)
    
    return Response({'success': True, 'redirect': f'/student/result/{attempt.id}/'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_log_violation(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    
    if attempt.status != 'in_progress':
        return Response({'error': 'Exam not in progress'}, status=400)
    
    violation_type = request.data.get('violation_type')
    details = request.data.get('details', '')
    
    valid_types = [v[0] for v in ProctoringLog.VIOLATION_TYPES]
    if violation_type not in valid_types:
        return Response({'error': 'Invalid violation type'}, status=400)
    
    log = ProctoringLog.objects.create(
        attempt=attempt,
        violation_type=violation_type,
        details=details
    )
    
    return Response(ProctoringLogSerializer(log).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_answers(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, student=request.user)
    answers = Answer.objects.filter(attempt=attempt)
    return Response(AnswerSerializer(answers, many=True).data)
