from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Exam categories (e.g., Math, English, Biology)"""
    name = models.CharField(max_length=100, unique=True)
    exam_category = models.CharField(max_length=100, default='AAAA', help_text="Exam category like AAAA")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Exam(models.Model):
    """Exams under each category (e.g., SAT, IELTS, Driving Test)
    
    Note: Category deletion cascades - when a Category is deleted, all related
    Exams, Topics, Questions, Choices, QuizSessions, UserAnswers, and BookmarkedQuestions
    will be automatically deleted.
    """
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='exams')
    exam_name = models.CharField(max_length=100, default='UPSC', help_text="Exam name like UPSC, ASI, CTET, STET")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    total_questions = models.PositiveIntegerField(default=10)
    passing_score = models.PositiveIntegerField(default=60, help_text="Passing percentage")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'exam_name', 'name']
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.exam_name} - {self.name}"


class Topic(models.Model):
    """Optional topics inside each exam"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['exam', 'order', 'name']
        unique_together = ['exam', 'name']

    def __str__(self):
        return f"{self.exam.name} - {self.name}"


class Question(models.Model):
    """Questions for exams"""
    QUESTION_TYPE_CHOICES = [
        ('single', 'Multiple Choice (Single Correct)'),
        ('multiple', 'Multiple Correct Choices'),
        ('true_false', 'True/False'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='single')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    explanation = models.TextField(blank=True, help_text="Explanation shown after quiz completion")
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['exam', 'order', 'id']

    def __str__(self):
        return f"{self.exam.name} - Q{self.id}: {self.question_text[:50]}..."

    def get_correct_choices(self):
        """Returns queryset of correct choices"""
        return self.choices.filter(is_correct=True)


class Choice(models.Model):
    """Answer choices for questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['question', 'order', 'id']

    def __str__(self):
        return f"{self.question.id} - {self.choice_text[:30]}..."


class QuizSession(models.Model):
    """Each quiz attempt by a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='quiz_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True)
    tokens_granted = models.BooleanField(default=False, help_text="Whether tokens were granted for completing this quiz")
    is_paused = models.BooleanField(default=False, help_text="Whether the quiz timer is currently paused")
    paused_at = models.DateTimeField(null=True, blank=True, help_text="When the quiz was paused")
    total_paused_seconds = models.PositiveIntegerField(default=0, help_text="Total time the quiz has been paused (in seconds)")

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        status = "Completed" if self.is_completed else "In Progress"
        return f"{self.user.username} - {self.exam.name} ({status})"

    def calculate_score(self):
        """Calculate and update the score based on total questions in exam"""
        # Get total questions in the exam (not just attempted)
        total_questions_in_exam = self.exam.questions.filter(is_active=True).count()
        if total_questions_in_exam == 0:
            return 0

        correct = self.user_answers.filter(is_correct=True).count()
        self.correct_answers = correct
        self.total_questions = total_questions_in_exam
        # Calculate score as percentage of total exam questions (not just attempted)
        self.score = (correct / total_questions_in_exam) * 100
        return self.score

    def complete_quiz(self):
        """Mark quiz as completed and calculate final score"""
        self.is_completed = True
        self.completed_at = timezone.now()
        if self.started_at:
            time_diff = self.completed_at - self.started_at
            self.time_taken_seconds = int(time_diff.total_seconds())
        self.calculate_score()
        self.save()
    
    def pause_quiz(self):
        """Pause the quiz timer"""
        if not self.is_paused and not self.is_completed:
            self.is_paused = True
            self.paused_at = timezone.now()
            self.save()
            return True
        return False
    
    def resume_quiz(self):
        """Resume the quiz timer"""
        if self.is_paused and not self.is_completed:
            if self.paused_at:
                # Calculate how long the quiz was paused
                pause_duration = (timezone.now() - self.paused_at).total_seconds()
                self.total_paused_seconds += int(pause_duration)
            self.is_paused = False
            self.paused_at = None
            self.save()
            return True
        return False
    
    def get_remaining_time(self):
        """Calculate remaining time accounting for paused periods"""
        if self.is_completed:
            return 0
        
        exam_duration_seconds = self.exam.duration_minutes * 60
        elapsed_time = (timezone.now() - self.started_at).total_seconds()
        
        # If currently paused, add the current pause duration
        current_pause_duration = 0
        if self.is_paused and self.paused_at:
            current_pause_duration = (timezone.now() - self.paused_at).total_seconds()
        
        # Total elapsed time minus all paused time
        actual_elapsed = elapsed_time - self.total_paused_seconds - current_pause_duration
        remaining = max(0, exam_duration_seconds - actual_elapsed)
        
        return int(remaining)


class UserAnswer(models.Model):
    """User's answer to a question"""
    quiz_session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_choices = models.ManyToManyField(Choice, related_name='user_answers')
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['quiz_session', 'answered_at']
        unique_together = ['quiz_session', 'question']

    def __str__(self):
        return f"{self.quiz_session.user.username} - Q{self.question.id}"

    def check_answer(self):
        """Check if the selected answer(s) are correct"""
        correct_choices = set(self.question.get_correct_choices())
        selected_choices = set(self.selected_choices.all())

        if self.question.question_type == 'single':
            # For single choice, must match exactly one correct choice
            self.is_correct = len(selected_choices) == 1 and selected_choices == correct_choices
        elif self.question.question_type == 'multiple':
            # For multiple choice, all selected must be correct and all correct must be selected
            self.is_correct = selected_choices == correct_choices
        elif self.question.question_type == 'true_false':
            # For true/false, must match exactly one correct choice
            self.is_correct = len(selected_choices) == 1 and selected_choices == correct_choices

        return self.is_correct


class BookmarkedQuestion(models.Model):
    """Questions bookmarked by users for later review"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarked_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'question']

    def __str__(self):
        return f"{self.user.username} - Q{self.question.id}"


class UserProfile(models.Model):
    """Extended user profile with subscription plan"""
    SUBSCRIPTION_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True,
        help_text="User profile photo"
    )
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default='basic',
        help_text="User's subscription plan"
    )
    tokens = models.PositiveIntegerField(
        default=100,
        help_text="Available tokens for AI Assistant and premium features"
    )
    last_token_grant_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when tokens were last granted to the user"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_subscription_plan_display()}"

    @property
    def is_premium(self):
        """Check if user has premium subscription"""
        return self.subscription_plan == 'premium'
    
    @property
    def is_basic(self):
        """Check if user has basic subscription"""
        return self.subscription_plan == 'basic'
    
    def add_tokens(self, amount):
        """Add tokens to user's account"""
        self.tokens += amount
        self.save()
    
    def deduct_tokens(self, amount):
        """Deduct tokens from user's account. Returns True if successful, False if insufficient tokens."""
        if self.tokens >= amount:
            self.tokens -= amount
            self.save()
            return True
        return False
    
    def has_tokens(self, amount=1):
        """Check if user has sufficient tokens"""
        return self.tokens >= amount
    
    def grant_daily_tokens(self):
        """Grant 10 tokens per day if not already granted today"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Check if tokens were already granted today
        if self.last_token_grant_date == today:
            return False  # Already granted today
        
        # Grant 10 tokens
        self.tokens += 10
        self.last_token_grant_date = today
        self.save()
        return True  # Tokens granted successfully

