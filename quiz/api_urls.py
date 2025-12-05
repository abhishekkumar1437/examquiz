from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CategoryViewSet, ExamViewSet, QuizSessionViewSet, UserAnswerViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'quiz-sessions', QuizSessionViewSet, basename='quizsession')
router.register(r'user-answers', UserAnswerViewSet, basename='useranswer')

urlpatterns = [
    path('', include(router.urls)),
]

