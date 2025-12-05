from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.core.management import call_command
from django.http import HttpResponseRedirect
from .models import Category, Exam, Topic, Question, Choice, QuizSession, UserAnswer, BookmarkedQuestion, UserProfile
import csv
from django.http import HttpResponse
from django import forms
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import pandas as pd


class ChoiceInline(admin.TabularInline):
    """Inline admin for choices"""
    model = Choice
    extra = 4
    fields = ['choice_text', 'is_correct', 'order']


class TopicInline(admin.TabularInline):
    """Inline admin for topics"""
    model = Topic
    extra = 1
    fields = ['name', 'description', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_category', 'description', 'exam_count', 'created_at']
    search_fields = ['name', 'exam_category', 'description']
    list_filter = ['exam_category', 'created_at']

    def exam_count(self, obj):
        return obj.exams.count()
    exam_count.short_description = 'Exams'


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_name', 'category', 'total_questions', 'duration_minutes', 'passing_score', 'is_active', 'question_count']
    list_filter = ['category', 'exam_name', 'is_active', 'created_at']
    search_fields = ['name', 'exam_name', 'description']
    inlines = [TopicInline]

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam', 'question_count', 'order']
    list_filter = ['exam']
    search_fields = ['name', 'description']

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_text_short', 'exam', 'topic', 'question_type', 'difficulty', 'points', 'choice_count', 'is_active']
    list_filter = ['exam', 'question_type', 'difficulty', 'is_active', 'created_at']
    search_fields = ['question_text', 'explanation']
    inlines = [ChoiceInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('exam', 'topic', 'question_text', 'question_type', 'difficulty', 'points', 'order', 'is_active')
        }),
        ('Explanation', {
            'fields': ('explanation',),
            'classes': ('wide',)
        }),
    )

    def question_text_short(self, obj):
        return obj.question_text[:100] + "..." if len(obj.question_text) > 100 else obj.question_text
    question_text_short.short_description = 'Question'

    def choice_count(self, obj):
        return obj.choices.count()
    choice_count.short_description = 'Choices'

    actions = ['export_questions_csv', 'export_questions_excel', 'process_inbox_csv']
    
    def process_inbox_csv(self, request, queryset):
        """Process CSV files from inbox folder"""
        try:
            call_command('import_questions_csv', '--auto-process')
            self.message_user(request, 'CSV files from inbox folder have been processed successfully.', messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f'Error processing CSV files: {str(e)}', messages.ERROR)
        return HttpResponseRedirect(request.get_full_path())
    process_inbox_csv.short_description = "Process CSV files from inbox folder"

    def export_questions_csv(self, request, queryset):
        """Export selected questions to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="questions_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Exam', 'Topic', 'Question Text', 'Question Type', 'Difficulty', 'Points', 'Explanation', 'Choices', 'Correct Choices'])
        for question in queryset:
            choices = "|".join([c.choice_text for c in question.choices.all()])
            correct_indices = []
            for idx, choice in enumerate(question.choices.all(), start=1):
                if choice.is_correct:
                    correct_indices.append(str(idx))
            correct_choices = ",".join(correct_indices)
            writer.writerow([
                question.exam.category.name,
                question.exam.name,
                question.topic.name if question.topic else '',
                question.question_text,
                question.question_type,
                question.difficulty,
                question.points,
                question.explanation,
                choices,
                correct_choices
            ])
        return response
    export_questions_csv.short_description = "Export selected questions to CSV"

    def export_questions_excel(self, request, queryset):
        """Export selected questions to Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Questions Export"
        headers = ['Exam', 'Topic', 'Question Text', 'Question Type', 'Difficulty', 'Points', 'Explanation', 'Choices', 'Correct Choices']
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        for question in queryset:
            choices = " | ".join([c.choice_text for c in question.choices.all()])
            correct_choices = " | ".join([c.choice_text for c in question.get_correct_choices()])
            ws.append([
                question.exam.name,
                question.topic.name if question.topic else '',
                question.question_text,
                question.question_type,
                question.difficulty,
                question.points,
                question.explanation,
                choices,
                correct_choices
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="questions_export.xlsx"'
        wb.save(response)
        return response
    export_questions_excel.short_description = "Export selected questions to Excel"

    def import_questions_csv(self, request, queryset):
        """Bulk import questions from CSV"""
        # This is a placeholder - actual implementation would require a form
        pass
    import_questions_csv.short_description = "Import questions from CSV"


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'choice_text_short', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__exam']
    search_fields = ['choice_text', 'question__question_text']

    def choice_text_short(self, obj):
        return obj.choice_text[:50] + "..." if len(obj.choice_text) > 50 else obj.choice_text
    choice_text_short.short_description = 'Choice'


class UserAnswerInline(admin.TabularInline):
    """Inline admin for user answers"""
    model = UserAnswer
    extra = 0
    readonly_fields = ['question', 'selected_choices', 'is_correct', 'answered_at']
    can_delete = False


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'exam', 'started_at', 'is_completed', 'score_display', 'correct_answers', 'total_questions', 'tokens_granted', 'time_taken']
    list_filter = ['is_completed', 'tokens_granted', 'exam', 'started_at']
    search_fields = ['user__username', 'exam__name']
    readonly_fields = ['started_at', 'completed_at', 'score', 'total_questions', 'correct_answers', 'time_taken_seconds']
    inlines = [UserAnswerInline]

    def score_display(self, obj):
        if obj.is_completed:
            color = 'green' if obj.score >= obj.exam.passing_score else 'red'
            return format_html('<span style="color: {};">{:.1f}%</span>', color, obj.score)
        return '-'
    score_display.short_description = 'Score'

    def time_taken(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return '-'
    time_taken.short_description = 'Time Taken'


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'quiz_session', 'question_short', 'selected_choices_display', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at', 'quiz_session__exam']
    search_fields = ['question__question_text', 'quiz_session__user__username']
    readonly_fields = ['quiz_session', 'question', 'selected_choices', 'is_correct', 'answered_at']

    def question_short(self, obj):
        return obj.question.question_text[:50] + "..." if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Question'

    def selected_choices_display(self, obj):
        choices = obj.selected_choices.all()
        if choices:
            return ", ".join([c.choice_text[:30] for c in choices])
        return "-"
    selected_choices_display.short_description = 'Selected Choices'


admin.site.register(BookmarkedQuestion)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_plan_display', 'tokens', 'last_token_grant_date', 'created_at', 'updated_at']
    list_filter = ['subscription_plan', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'profile_photo', 'subscription_plan', 'tokens', 'last_token_grant_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subscription_plan_display(self, obj):
        if obj.subscription_plan == 'premium':
            return format_html('<span style="color: #ffc107; font-weight: bold;">⭐ Premium</span>')
        return format_html('<span style="color: #6c757d;">Basic</span>')
    subscription_plan_display.short_description = 'Subscription Plan'
    
    actions = ['add_tokens_100', 'add_tokens_500', 'add_tokens_1000', 'reset_tokens_basic', 'reset_tokens_premium']
    
    def add_tokens_100(self, request, queryset):
        for profile in queryset:
            profile.add_tokens(100)
        self.message_user(request, f'Added 100 tokens to {queryset.count()} profile(s).')
    add_tokens_100.short_description = "Add 100 tokens to selected"
    
    def add_tokens_500(self, request, queryset):
        for profile in queryset:
            profile.add_tokens(500)
        self.message_user(request, f'Added 500 tokens to {queryset.count()} profile(s).')
    add_tokens_500.short_description = "Add 500 tokens to selected"
    
    def add_tokens_1000(self, request, queryset):
        for profile in queryset:
            profile.add_tokens(1000)
        self.message_user(request, f'Added 1000 tokens to {queryset.count()} profile(s).')
    add_tokens_1000.short_description = "Add 1000 tokens to selected"
    
    def reset_tokens_basic(self, request, queryset):
        for profile in queryset:
            profile.tokens = 100
            profile.save()
        self.message_user(request, f'Reset tokens to 100 for {queryset.count()} profile(s).')
    reset_tokens_basic.short_description = "Reset tokens to 100 (Basic)"
    
    def reset_tokens_premium(self, request, queryset):
        for profile in queryset:
            profile.tokens = 1100  # 100 default + 1000 premium bonus
            profile.save()
        self.message_user(request, f'Reset tokens to 1100 for {queryset.count()} profile(s).')
    reset_tokens_premium.short_description = "Reset tokens to 1100 (Premium)"

