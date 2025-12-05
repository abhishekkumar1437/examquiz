from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count
from .models import Category, Exam, QuizSession, UserAnswer, Question, Choice
from .serializers import (
    CategorySerializer, ExamSerializer, QuizSessionSerializer,
    UserAnswerSerializer, QuestionSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing categories"""
    queryset = Category.objects.annotate(exam_count=Count('exams')).filter(exam_count__gt=0)
    serializer_class = CategorySerializer
    permission_classes = []


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing exams"""
    queryset = Exam.objects.filter(is_active=True).annotate(question_count=Count('questions')).filter(question_count__gt=0)
    serializer_class = ExamSerializer
    permission_classes = []

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for an exam"""
        exam = self.get_object()
        questions = exam.questions.filter(is_active=True)
        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        return Response(serializer.data)


class QuizSessionViewSet(viewsets.ModelViewSet):
    """API endpoint for quiz sessions"""
    serializer_class = QuizSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QuizSession.objects.filter(user=self.request.user)

    def create(self, request):
        """Start a new quiz session"""
        exam_id = request.data.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id, is_active=True)
        
        # Check if there are questions
        if not exam.questions.filter(is_active=True).exists():
            return Response(
                {'error': 'This exam has no questions available.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quiz_session = QuizSession.objects.create(
            user=request.user,
            exam=exam
        )
        
        serializer = self.get_serializer(quiz_session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """Submit an answer for a question"""
        quiz_session = self.get_object()
        
        if quiz_session.is_completed:
            return Response(
                {'error': 'Quiz already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        question_id = request.data.get('question_id')
        choice_ids = request.data.get('choice_ids', [])
        
        if not question_id or not choice_ids:
            return Response(
                {'error': 'Missing question_id or choice_ids'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        question = get_object_or_404(Question, id=question_id, exam=quiz_session.exam)
        choices = Choice.objects.filter(id__in=choice_ids, question=question)
        
        if not choices.exists():
            return Response(
                {'error': 'Invalid choices'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        serializer = UserAnswerSerializer(user_answer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a quiz session"""
        quiz_session = self.get_object()
        
        if quiz_session.is_completed:
            return Response(
                {'error': 'Quiz already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quiz_session.complete_quiz()
        serializer = self.get_serializer(quiz_session)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get detailed results for a quiz session"""
        quiz_session = self.get_object()
        
        if not quiz_session.is_completed:
            quiz_session.complete_quiz()
        
        user_answers = UserAnswer.objects.filter(
            quiz_session=quiz_session
        ).select_related('question').prefetch_related('selected_choices', 'question__choices')
        
        results_data = {
            'quiz_session': QuizSessionSerializer(quiz_session).data,
            'user_answers': UserAnswerSerializer(user_answers, many=True).data,
            'total_questions': user_answers.count(),
            'correct_count': user_answers.filter(is_correct=True).count(),
            'score': quiz_session.score,
        }
        
        return Response(results_data)


class UserAnswerViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing user answers"""
    serializer_class = UserAnswerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAnswer.objects.filter(quiz_session__user=self.request.user)

