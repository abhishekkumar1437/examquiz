from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home and Auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='quiz/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='quiz/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='quiz/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='quiz/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='quiz/password_reset_complete.html'),
         name='password_reset_complete'),
    
    # Dashboard and Profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Exams
    path('exams/', views.exam_list, name='exam_list'),
    
    # Quiz
    path('quiz/start/<int:exam_id>/', views.quiz_start, name='quiz_start'),
    path('quiz/<int:session_id>/question/<int:question_num>/', views.quiz_question, name='quiz_question'),
    path('quiz/<int:session_id>/submit/', views.quiz_submit_answer, name='quiz_submit_answer'),
    path('quiz/<int:session_id>/pause/', views.pause_quiz, name='pause_quiz'),
    path('quiz/<int:session_id>/resume/', views.resume_quiz, name='resume_quiz'),
    path('quiz/<int:session_id>/result/', views.quiz_result, name='quiz_result'),
    
    # Bookmarks and Incomplete Quizzes
    path('bookmarks/', views.bookmarked_questions, name='bookmarked_questions'),
    path('bookmarks/toggle/<int:question_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('incomplete-quizzes/', views.incomplete_quizzes, name='incomplete_quizzes'),
    
    # AI Assistant
    path('ai-assistant/<int:session_id>/<int:question_id>/', views.ai_assistant, name='ai_assistant'),
    
    # Subscription Management
    path('subscription/upgrade/', views.upgrade_subscription, name='upgrade_subscription'),
    path('subscription/downgrade/', views.downgrade_subscription, name='downgrade_subscription'),
]

