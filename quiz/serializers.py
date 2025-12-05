from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Exam, Topic, Question, Choice, QuizSession, UserAnswer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'difficulty', 'points', 
                  'explanation', 'choices', 'order']


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'description', 'order']


class ExamSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exam
        fields = ['id', 'name', 'description', 'category', 'category_name',
                  'duration_minutes', 'total_questions', 'passing_score',
                  'is_active', 'question_count', 'topics']


class CategorySerializer(serializers.ModelSerializer):
    exam_count = serializers.IntegerField(read_only=True)
    exams = ExamSerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'exam_count', 'exams']


class UserAnswerSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_choices', 'is_correct', 'answered_at']


class QuizSessionSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    exam_category = serializers.CharField(source='exam.category.name', read_only=True)
    user_answers = UserAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizSession
        fields = ['id', 'user', 'exam', 'exam_name', 'exam_category',
                  'started_at', 'completed_at', 'is_completed', 'score',
                  'total_questions', 'correct_answers', 'time_taken_seconds',
                  'user_answers']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

