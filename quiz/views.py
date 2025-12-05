from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from .models import Category, Exam, Question, QuizSession, UserAnswer, Choice, BookmarkedQuestion
import random
import json


def home(request):
    """Home page"""
    # Get all unique exam_names across all categories with exam counts
    exam_names_data = Exam.objects.filter(
        is_active=True
    ).annotate(
        question_count=Count('questions', filter=Q(questions__is_active=True))
    ).filter(question_count__gt=0).values('exam_name').annotate(
        exam_count=Count('id', distinct=True)
    ).order_by('exam_name')
    
    exam_names_list = [{'name': item['exam_name'] or 'Other', 'count': item['exam_count']} for item in exam_names_data]
    
    recent_exams = Exam.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    # Performance over time data for authenticated users
    recent_sessions = None
    if request.user.is_authenticated:
        recent_sessions = QuizSession.objects.filter(
            user=request.user, 
            is_completed=True
        ).order_by('-completed_at')[:10]
    
    return render(request, 'quiz/home.html', {
        'exam_names_list': exam_names_list,
        'recent_exams': recent_exams,
        'recent_sessions': recent_sessions
    })


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'quiz/register.html', {'form': form})


@login_required
def logout_view(request):
    """User logout"""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard(request):
    """User dashboard with stats and recent quizzes"""
    user = request.user
    
    # Grant daily tokens if not already granted today
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    tokens_granted = profile.grant_daily_tokens()
    if tokens_granted:
        messages.info(request, f'You received 10 daily tokens! You now have {profile.tokens} tokens.')
    
    # Quiz statistics
    total_quizzes = QuizSession.objects.filter(user=user, is_completed=True).count()
    total_questions_answered = UserAnswer.objects.filter(quiz_session__user=user).count()
    correct_answers = UserAnswer.objects.filter(quiz_session__user=user, is_correct=True).count()
    accuracy = (correct_answers / total_questions_answered * 100) if total_questions_answered > 0 else 0
    
    # Recent quiz sessions
    recent_sessions = QuizSession.objects.filter(user=user).order_by('-started_at')[:10]
    
    # Incomplete quiz sessions
    incomplete_sessions = QuizSession.objects.filter(
        user=user,
        is_completed=False
    ).select_related('exam', 'exam__category').order_by('-started_at')[:5]
    
    # Calculate progress for incomplete sessions and find next question number
    for session in incomplete_sessions:
        total_questions = session.exam.questions.filter(is_active=True).count()
        attempted = session.user_answers.count()
        session.progress_percentage = (attempted / total_questions * 100) if total_questions > 0 else 0
        session.attempted_count = attempted
        session.total_count = total_questions
        
        # Find the first unanswered question or start from question 1
        answered_question_ids = set(session.user_answers.values_list('question_id', flat=True))
        # Get questions in database order (order field, then id)
        questions_list = list(session.exam.questions.filter(is_active=True).order_by('order', 'id'))
        
        # Find first unanswered question
        next_question_num = 1
        for idx, question in enumerate(questions_list, 1):
            if question.id not in answered_question_ids:
                next_question_num = idx
                break
        session.next_question_num = next_question_num
    
    # Bookmarked questions count
    bookmarked_count = BookmarkedQuestion.objects.filter(user=user).count()
    
    # Available exams
    available_exams = Exam.objects.filter(is_active=True).annotate(
        question_count=Count('questions')
    ).filter(question_count__gt=0)
    
    # Performance by exam
    exam_performance = QuizSession.objects.filter(
        user=user, 
        is_completed=True
    ).values('exam__name').annotate(
        avg_score=Avg('score'),
        attempt_count=Count('id')
    ).order_by('-avg_score')[:5]
    
    # Performance by category
    category_performance = QuizSession.objects.filter(
        user=user,
        is_completed=True
    ).values('exam__category__name').annotate(
        avg_score=Avg('score'),
        attempt_count=Count('id')
    ).order_by('-avg_score')[:5]
    
    return render(request, 'quiz/dashboard.html', {
        'total_quizzes': total_quizzes,
        'total_questions_answered': total_questions_answered,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'recent_sessions': recent_sessions,
        'incomplete_sessions': incomplete_sessions,
        'bookmarked_count': bookmarked_count,
        'available_exams': available_exams,
        'exam_performance': exam_performance,
        'category_performance': category_performance,
    })


def exam_list(request):
    """List exam_names first, then categories, then exams when selected"""
    exam_name = request.GET.get('exam_name')
    category_id = request.GET.get('category')
    search_query = request.GET.get('search', '')
    
    # Get all unique exam_names across all categories with exam counts
    exam_names_data = Exam.objects.filter(
        is_active=True
    ).annotate(
        question_count=Count('questions', filter=Q(questions__is_active=True))
    ).filter(question_count__gt=0).values('exam_name').annotate(
        exam_count=Count('id', distinct=True)
    ).order_by('exam_name')
    
    exam_names_list = [{'name': item['exam_name'] or 'Other', 'count': item['exam_count']} for item in exam_names_data]
    
    # Get categories and exams based on what's selected
    categories_list = []
    exams_by_exam_name = {}
    selected_category = None
    selected_exam_name = None
    
    if exam_name:
        selected_exam_name = exam_name
        
        # Get all categories that have exams with this exam_name
        if exam_name == 'Other':
            # For "Other", filter categories that have exams with NULL or empty exam_name
            categories_data = Category.objects.filter(
                Q(exams__exam_name__isnull=True) | Q(exams__exam_name=''),
                exams__is_active=True
            ).annotate(
                exam_count=Count('exams', filter=Q(exams__is_active=True) & (Q(exams__exam_name__isnull=True) | Q(exams__exam_name='')) & Q(exams__questions__is_active=True), distinct=True)
            ).filter(exam_count__gt=0).distinct().order_by('name')
        else:
            categories_data = Category.objects.filter(
                exams__exam_name=exam_name,
                exams__is_active=True
            ).annotate(
                exam_count=Count('exams', filter=Q(exams__is_active=True) & Q(exams__exam_name=exam_name) & Q(exams__questions__is_active=True), distinct=True)
            ).filter(exam_count__gt=0).distinct().order_by('name')
        
        categories_list = [{'id': cat.id, 'name': cat.name, 'description': cat.description, 'exam_count': cat.exam_count} for cat in categories_data]
        
        # If category is also selected, fetch exams for that exam_name and category
        if category_id:
            selected_category = get_object_or_404(Category, id=category_id)
            
            # Handle "Other" case (NULL or empty exam_name)
            if exam_name == 'Other':
                exam_filter = Q(category_id=category_id, exam_name__isnull=True) | Q(category_id=category_id, exam_name='')
            else:
                exam_filter = Q(category_id=category_id, exam_name=exam_name)
            
            exams = Exam.objects.filter(
                exam_filter,
                is_active=True
            ).annotate(
                question_count=Count('questions', filter=Q(questions__is_active=True))
            ).filter(question_count__gt=0).prefetch_related('topics').order_by('name')
            
            if search_query:
                exams = exams.filter(
                    Q(name__icontains=search_query) | 
                    Q(description__icontains=search_query)
                )
            
            # Get user's completion status for each exam
            exam_status = {}
            if request.user.is_authenticated:
                # Get all completed sessions for the exams, ordered by most recent first
                completed_sessions = QuizSession.objects.filter(
                    user=request.user,
                    is_completed=True,
                    exam__in=exams
                ).select_related('exam').order_by('-completed_at')
                
                # Create a dict mapping exam_id to status: 'passed', 'failed', or 'not_attempted'
                # Use the most recent completed attempt for each exam
                for session in completed_sessions:
                    exam_id = session.exam_id
                    if exam_id not in exam_status:  # Only keep the most recent completed attempt (first occurrence due to ordering)
                        if session.score >= session.exam.passing_score:
                            exam_status[exam_id] = 'passed'
                        else:
                            exam_status[exam_id] = 'failed'
            
            # Add status to each exam (defaults to 'not_attempted' if not found)
            for exam in exams:
                exam.completion_status = exam_status.get(exam.id, 'not_attempted')
            
            # Group exams by exam_name (should be just one group)
            for exam in exams:
                exam_name_val = exam.exam_name or 'Other'
                if exam_name_val not in exams_by_exam_name:
                    exams_by_exam_name[exam_name_val] = []
                exams_by_exam_name[exam_name_val].append(exam)
    
    return render(request, 'quiz/exam_list.html', {
        'exams_by_exam_name': exams_by_exam_name,
        'exam_names_list': exam_names_list,
        'categories_list': categories_list,
        'selected_category': selected_category,
        'selected_exam_name': selected_exam_name,
        'search_query': search_query,
    })


@login_required
@login_required
def quiz_start(request, exam_id):
    """Start a new quiz session or resume incomplete one - Login required"""
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    
    # Check if there are questions
    questions = exam.questions.filter(is_active=True)
    if not questions.exists():
        messages.error(request, 'This exam has no questions available.')
        return redirect('exam_list')
    
    # Check for incomplete quiz session for this exam
    incomplete_session = QuizSession.objects.filter(
        user=request.user,
        exam=exam,
        is_completed=False
    ).order_by('-started_at').first()
    
    if incomplete_session:
        # Resume incomplete quiz
        messages.info(request, 'Resuming your incomplete quiz session.')
        return redirect('quiz_question', session_id=incomplete_session.id, question_num=1)
    
    # Create a new quiz session
    quiz_session = QuizSession.objects.create(
        user=request.user,
        exam=exam
    )
    
    return redirect('quiz_question', session_id=quiz_session.id, question_num=1)


@login_required
def quiz_question(request, session_id, question_num):
    """Display a question in the quiz"""
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.is_completed:
        messages.info(request, 'This quiz has already been completed.')
        return redirect('quiz_result', session_id=quiz_session.id)
    
    # Get all questions for this exam in database order (order field, then id)
    questions = list(quiz_session.exam.questions.filter(is_active=True).order_by('order', 'id'))
    
    if not questions:
        messages.error(request, 'No questions available for this exam.')
        return redirect('exam_list')
    
    # Ensure question_num is valid
    question_num = int(question_num)
    if question_num < 1 or question_num > len(questions):
        question_num = 1
    
    current_question = questions[question_num - 1]
    
    # Get all user answers for this session to show which questions are answered
    user_answers_map = {ua.question_id: ua for ua in UserAnswer.objects.filter(quiz_session=quiz_session).select_related('question')}
    
    # Get bookmarked question IDs for this exam
    bookmarked_question_ids = set(BookmarkedQuestion.objects.filter(
        user=request.user,
        question__exam=quiz_session.exam
    ).values_list('question_id', flat=True))
    
    # Get user's previous answer if exists
    user_answer = UserAnswer.objects.filter(
        quiz_session=quiz_session,
        question=current_question
    ).first()
    
    selected_choice_ids = list(user_answer.selected_choices.values_list('id', flat=True)) if user_answer else []
    
    # Get choices for this question
    choices = current_question.choices.all().order_by('order', 'id')
    
    # Calculate remaining time using quiz_session method (accounts for paused time)
    remaining_time_seconds = quiz_session.get_remaining_time()
    exam_duration_seconds = quiz_session.exam.duration_minutes * 60
    
    # Check if time has expired - allow user to continue viewing questions
    # Don't auto-complete here, let them continue and submit manually
    time_expired = remaining_time_seconds <= 0
    if time_expired:
        remaining_time_seconds = 0  # Set to 0 for display purposes
    
    # Resume quiz if it was paused (update paused time)
    if quiz_session.is_paused:
        quiz_session.resume_quiz()
    
    # Check if question is bookmarked
    is_bookmarked = current_question.id in bookmarked_question_ids
    
    # Prepare question navigation data (all questions with their status)
    # Note: We don't show correct/incorrect status during quiz to prevent cheating
    question_navigation = []
    for idx, q in enumerate(questions, 1):
        user_answer = user_answers_map.get(q.id)
        is_bookmarked_q = q.id in bookmarked_question_ids
        question_navigation.append({
            'number': idx,
            'question': q,
            'is_answered': user_answer is not None,
            'is_bookmarked': is_bookmarked_q,
            'is_current': idx == question_num,
        })
    
    context = {
        'quiz_session': quiz_session,
        'question': current_question,
        'choices': choices,
        'question_num': question_num,
        'total_questions': len(questions),
        'selected_choice_ids': selected_choice_ids,
        'progress': (question_num / len(questions)) * 100,
        'remaining_time_seconds': remaining_time_seconds,
        'exam_duration_seconds': exam_duration_seconds,
        'is_bookmarked': is_bookmarked,
        'question_navigation': question_navigation,
        'is_paused': quiz_session.is_paused,
    }
    
    return render(request, 'quiz/quiz_question.html', context)


@login_required
def quiz_submit_answer(request, session_id):
    """Submit an answer for a question"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.is_completed:
        return JsonResponse({'error': 'Quiz already completed'}, status=400)
    
    question_id = request.POST.get('question_id')
    choice_ids = request.POST.getlist('choice_ids[]')
    
    if not question_id or not choice_ids:
        return JsonResponse({'error': 'Missing question_id or choice_ids'}, status=400)
    
    question = get_object_or_404(Question, id=question_id, exam=quiz_session.exam)
    choices = Choice.objects.filter(id__in=choice_ids, question=question)
    
    if not choices.exists():
        return JsonResponse({'error': 'Invalid choices'}, status=400)
    
    # Get or create user answer
    user_answer, created = UserAnswer.objects.get_or_create(
        quiz_session=quiz_session,
        question=question,
        defaults={}
    )
    
    # Update selected choices
    user_answer.selected_choices.set(choices)
    user_answer.check_answer()
    user_answer.save()
    
    return JsonResponse({
        'success': True,
        'is_correct': user_answer.is_correct
    })


@login_required
def pause_quiz(request, session_id):
    """Pause the quiz timer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.is_completed:
        return JsonResponse({'error': 'Quiz already completed'}, status=400)
    
    success = quiz_session.pause_quiz()
    
    if success:
        return JsonResponse({
            'success': True,
            'is_paused': True,
            'message': 'Quiz paused successfully'
        })
    else:
        return JsonResponse({'error': 'Quiz is already paused'}, status=400)


@login_required
def resume_quiz(request, session_id):
    """Resume the quiz timer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.is_completed:
        return JsonResponse({'error': 'Quiz already completed'}, status=400)
    
    success = quiz_session.resume_quiz()
    
    if success:
        return JsonResponse({
            'success': True,
            'is_paused': False,
            'remaining_time': quiz_session.get_remaining_time(),
            'message': 'Quiz resumed successfully'
        })
    else:
        return JsonResponse({'error': 'Quiz is not paused'}, status=400)


@login_required
def quiz_result(request, session_id):
    """Display quiz results"""
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    # Track if quiz was just completed (before calling complete_quiz)
    was_completed_before = quiz_session.is_completed
    
    # Complete the quiz if not already completed
    if not quiz_session.is_completed:
        quiz_session.complete_quiz()
    
    # Recalculate score based on total exam questions (not just attempted)
    quiz_session.calculate_score()
    quiz_session.save()
    
    # Grant 50 tokens if quiz was just completed AND score >= passing score AND tokens not already granted
    if not was_completed_before and not quiz_session.tokens_granted:
        if quiz_session.score >= quiz_session.exam.passing_score:
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.add_tokens(50)
            quiz_session.tokens_granted = True
            quiz_session.save()
            messages.success(request, f'🎉 Congratulations! You passed the quiz and earned 50 tokens! You now have {profile.tokens} tokens.')
    
    # Get all user answers with questions
    user_answers = UserAnswer.objects.filter(
        quiz_session=quiz_session
    ).select_related('question').prefetch_related('selected_choices', 'question__choices')
    
    # Get all questions in the exam (not just attempted)
    all_exam_questions = quiz_session.exam.questions.filter(is_active=True).select_related('topic').prefetch_related('choices').order_by('id')
    total_questions_in_exam = all_exam_questions.count()
    
    # Create a mapping of question_id to user_answer for quick lookup
    user_answer_map = {ua.question_id: ua for ua in user_answers}
    
    # Organize all questions by status
    correct_questions = []
    incorrect_questions = []
    unattempted_questions = []
    
    for question in all_exam_questions:
        user_answer = user_answer_map.get(question.id)
        question_data = {
            'question': question,
            'user_answer': user_answer,
            'selected_choices': list(user_answer.selected_choices.all()) if user_answer else [],
        }
        
        if user_answer:
            if user_answer.is_correct:
                correct_questions.append(question_data)
            else:
                incorrect_questions.append(question_data)
        else:
            unattempted_questions.append(question_data)
    
    # Calculate statistics
    attempted_questions = user_answers.count()
    correct_count = len(correct_questions)
    incorrect_count = len(incorrect_questions)
    unanswered_count = len(unattempted_questions)
    
    # Calculate percentage based on total questions in exam: (correct / total_exam_questions) * 100
    correct_percentage = round((correct_count / total_questions_in_exam * 100), 1) if total_questions_in_exam > 0 else 0
    
    # Also calculate accuracy (correct / attempted) for display
    accuracy_percentage = round((correct_count / attempted_questions * 100), 1) if attempted_questions > 0 else 0
    
    # Performance by difficulty
    difficulty_stats = {}
    for difficulty in ['easy', 'medium', 'hard']:
        diff_questions = user_answers.filter(question__difficulty=difficulty)
        diff_total = diff_questions.count()
        diff_correct = diff_questions.filter(is_correct=True).count()
        if diff_total > 0:
            difficulty_stats[difficulty] = {
                'total': diff_total,
                'correct': diff_correct,
                'percentage': round((diff_correct / diff_total) * 100, 1)
            }
    
    # Performance by topic
    topic_stats = {}
    for user_answer in user_answers:
        topic = user_answer.question.topic
        topic_name = topic.name if topic else 'No Topic'
        if topic_name not in topic_stats:
            topic_stats[topic_name] = {'total': 0, 'correct': 0}
        topic_stats[topic_name]['total'] += 1
        if user_answer.is_correct:
            topic_stats[topic_name]['correct'] += 1
    
    for topic_name in topic_stats:
        stats = topic_stats[topic_name]
        stats['percentage'] = round((stats['correct'] / stats['total']) * 100, 1) if stats['total'] > 0 else 0
    
    # Prepare shareable content
    from urllib.parse import quote
    share_url = request.build_absolute_uri(request.path)
    share_message = (
        f"I scored {correct_percentage}% on {quiz_session.exam.name}! "
        f"Got {correct_count} out of {total_questions_in_exam} questions correct. "
        f"#ExamQuiz #OnlineLearning"
    )
    share_title = f"Quiz Result: {quiz_session.exam.name}"
    
    # Pre-encode URLs for social sharing to avoid double encoding
    share_url_encoded = quote(share_url, safe='')
    share_message_encoded = quote(share_message, safe='')
    share_title_encoded = quote(share_title, safe='')
    
    context = {
        'quiz_session': quiz_session,
        'user_answers': user_answers,
        'all_questions': all_exam_questions,
        'correct_questions': correct_questions,
        'incorrect_questions': incorrect_questions,
        'unattempted_questions': unattempted_questions,
        'total_questions': total_questions_in_exam,
        'attempted_questions': attempted_questions,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'unanswered_count': unanswered_count,
        'correct_percentage': correct_percentage,
        'accuracy_percentage': accuracy_percentage,
        'difficulty_stats': difficulty_stats,
        'topic_stats': topic_stats,
        'passed': correct_percentage >= quiz_session.exam.passing_score,
        'share_url': share_url,
        'share_url_encoded': share_url_encoded,
        'share_message': share_message,
        'share_message_encoded': share_message_encoded,
        'share_title': share_title,
        'share_title_encoded': share_title_encoded,
    }
    
    return render(request, 'quiz/quiz_result.html', context)


@login_required
def toggle_bookmark(request, question_id):
    """Toggle bookmark status for a question"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    question = get_object_or_404(Question, id=question_id)
    bookmark, created = BookmarkedQuestion.objects.get_or_create(
        user=request.user,
        question=question
    )
    
    if not created:
        # Already bookmarked, remove it
        bookmark.delete()
        return JsonResponse({'bookmarked': False, 'message': 'Question removed from bookmarks'})
    
    return JsonResponse({'bookmarked': True, 'message': 'Question bookmarked successfully'})


@login_required
def bookmarked_questions(request):
    """Display all bookmarked questions"""
    bookmarks = BookmarkedQuestion.objects.filter(
        user=request.user
    ).select_related('question', 'question__exam', 'question__topic').order_by('-created_at')
    
    context = {
        'bookmarks': bookmarks,
    }
    
    return render(request, 'quiz/bookmarked_questions.html', context)


@login_required
def incomplete_quizzes(request):
    """Display incomplete quiz sessions"""
    incomplete_sessions = QuizSession.objects.filter(
        user=request.user,
        is_completed=False
    ).select_related('exam', 'exam__category').order_by('-started_at')
    
    # Calculate progress for each session and find next question number
    for session in incomplete_sessions:
        total_questions = session.exam.questions.filter(is_active=True).count()
        attempted = session.user_answers.count()
        session.progress_percentage = (attempted / total_questions * 100) if total_questions > 0 else 0
        session.attempted_count = attempted
        session.total_count = total_questions
        
        # Find the first unanswered question or start from question 1
        answered_question_ids = set(session.user_answers.values_list('question_id', flat=True))
        # Get questions in database order (order field, then id)
        questions_list = list(session.exam.questions.filter(is_active=True).order_by('order', 'id'))
        
        # Find first unanswered question
        next_question_num = 1
        for idx, question in enumerate(questions_list, 1):
            if question.id not in answered_question_ids:
                next_question_num = idx
                break
        session.next_question_num = next_question_num
    
    context = {
        'incomplete_sessions': incomplete_sessions,
    }
    
    return render(request, 'quiz/incomplete_quizzes.html', context)


@login_required
def profile(request):
    """User profile page"""
    user = request.user
    
    # Grant daily tokens if not already granted today
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    tokens_granted = profile.grant_daily_tokens()
    if tokens_granted:
        messages.info(request, f'You received 10 daily tokens! You now have {profile.tokens} tokens.')
    
    # Overall statistics
    total_quizzes = QuizSession.objects.filter(user=user, is_completed=True).count()
    total_questions = UserAnswer.objects.filter(quiz_session__user=user).count()
    correct_answers = UserAnswer.objects.filter(quiz_session__user=user, is_correct=True).count()
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Quiz history
    quiz_history = QuizSession.objects.filter(user=user, is_completed=True).order_by('-completed_at')[:20]
    
    # Performance over time (last 10 quizzes)
    recent_sessions = QuizSession.objects.filter(
        user=user, 
        is_completed=True
    ).order_by('-completed_at')[:10]
    
    # Profile already created above with daily tokens granted
    profile.refresh_from_db()  # Refresh to get latest token count
    
    return render(request, 'quiz/profile.html', {
        'user': user,
        'user_profile': profile,
        'total_quizzes': total_quizzes,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'quiz_history': quiz_history,
        'recent_sessions': recent_sessions,
    })


@login_required
def edit_profile(request):
    """Edit user profile including photo upload"""
    from .models import UserProfile
    from django.contrib.auth.forms import UserChangeForm
    
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            # Delete old photo if exists
            if profile.profile_photo:
                profile.profile_photo.delete()
            profile.profile_photo = request.FILES['profile_photo']
            profile.save()
            messages.success(request, 'Profile photo updated successfully!')
        
        # Handle user info update
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'quiz/edit_profile.html', {
        'user': user,
        'user_profile': profile,
    })


@login_required
def upgrade_subscription(request):
    """Upgrade user subscription to Premium"""
    from .models import UserProfile
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if profile.subscription_plan == 'premium':
        messages.info(request, 'You already have a Premium subscription.')
        return redirect('profile')
    
    # Upgrade to premium and add 1000 tokens
    profile.subscription_plan = 'premium'
    profile.add_tokens(1000)  # Add 1000 tokens when upgrading to premium
    
    messages.success(request, 'Congratulations! Your subscription has been upgraded to Premium. You received 1000 bonus tokens!')
    return redirect('profile')


@login_required
def downgrade_subscription(request):
    """Downgrade user subscription to Basic"""
    from .models import UserProfile
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if profile.subscription_plan == 'basic':
        messages.info(request, 'You already have a Basic subscription.')
        return redirect('profile')
    
    # Downgrade to basic
    profile.subscription_plan = 'basic'
    profile.save()
    
    messages.info(request, 'Your subscription has been downgraded to Basic.')
    return redirect('profile')


@login_required
def ai_assistant(request, session_id, question_id):
    """AI Assistant endpoint for doubt assistance during quiz"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Check user's token balance (AI Assistant costs 1 token per request)
        from .models import UserProfile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        TOKENS_PER_AI_REQUEST = 1  # Cost per AI Assistant request
        
        if not profile.has_tokens(TOKENS_PER_AI_REQUEST):
            return JsonResponse({
                'error': 'Insufficient tokens',
                'response': f'Sorry, you don\'t have enough tokens to use AI Assistant. You have {profile.tokens} token(s) remaining. Please upgrade to Premium to get more tokens or contact support.'
            }, status=403)
        
        # Get context if session_id and question_id are provided
        context_info = ""
        current_question = None
        
        if session_id:
            quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
            
            if question_id:
                current_question = get_object_or_404(Question, id=question_id, exam=quiz_session.exam)
                
                # Build context about the current question
                context_info = f"""
Current Question Context:
- Exam: {quiz_session.exam.name}
- Category: {quiz_session.exam.category.name if quiz_session.exam.category else 'N/A'}
- Question: {current_question.question_text}
- Difficulty: {current_question.difficulty}
- Question Type: {current_question.get_question_type_display()}
- Explanation: {current_question.explanation if current_question.explanation else 'Not available'}
- Choices:
"""
                for choice in current_question.choices.all().order_by('order', 'id'):
                    context_info += f"  - {choice.choice_text}\n"
            else:
                context_info = f"""
Quiz Context:
- Exam: {quiz_session.exam.name}
- Category: {quiz_session.exam.category.name if quiz_session.exam.category else 'N/A'}
- Session Status: {'Completed' if quiz_session.is_completed else 'In Progress'}
"""
        
        # Import OpenAI (handle gracefully if not installed)
        try:
            from openai import OpenAI
        except ImportError:
            return JsonResponse({
                'error': 'OpenAI library not installed. Please run: pip install openai',
                'response': 'AI Assistant is not configured. Please contact the administrator.'
            }, status=503)
        
        # Check if API key is configured
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return JsonResponse({
                'error': 'OpenAI API key not configured',
                'response': 'AI Assistant is not configured. Please contact the administrator.'
            }, status=503)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Build system prompt
        system_prompt = """You are a helpful AI study assistant for an exam quiz platform. Your role is to help students understand questions, clarify concepts, and provide educational guidance. 

IMPORTANT GUIDELINES:
- Do NOT provide direct answers to quiz questions
- Do NOT reveal which choice is correct
- Focus on explaining concepts, definitions, and helping the student think through the problem
- Be educational and encouraging
- If asked about the correct answer, explain the concepts instead of giving the answer directly
- Keep responses concise and clear (2-3 sentences preferred)
- Use simple language appropriate for students"""
        
        # Build user prompt with context
        user_prompt = f"""Student's question: {user_message}
        
{context_info}
        
Please provide helpful guidance without revealing the correct answer."""
        
        # Call OpenAI API
        try:
            model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Deduct tokens after successful AI response
            profile.refresh_from_db()  # Refresh to get latest token count
            if not profile.deduct_tokens(TOKENS_PER_AI_REQUEST):
                return JsonResponse({
                    'error': 'Failed to deduct tokens',
                    'response': 'An error occurred while processing your request.'
                }, status=500)
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'tokens_remaining': profile.tokens
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error calling OpenAI API: {str(e)}',
                'response': 'Sorry, I encountered an error. Please try again later.'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)

