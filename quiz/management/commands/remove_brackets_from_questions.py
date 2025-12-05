from django.core.management.base import BaseCommand
from quiz.models import Question, Choice, Exam, Category, Topic


class Command(BaseCommand):
    help = 'Remove all square brackets from question text, choices, and explanations in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating the database'
        )

    def remove_brackets(self, text):
        """Remove all square brackets from text"""
        if not isinstance(text, str):
            return text
        return text.replace('[', '').replace(']', '')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        updated_count = 0
        
        # Update questions
        questions = Question.objects.all()
        for question in questions:
            original_text = question.question_text
            original_explanation = question.explanation
            
            cleaned_text = self.remove_brackets(original_text)
            cleaned_explanation = self.remove_brackets(original_explanation)
            
            if original_text != cleaned_text or original_explanation != cleaned_explanation:
                updated_count += 1
                self.stdout.write(f'Question {question.id}:')
                if original_text != cleaned_text:
                    self.stdout.write(f'  Text: "{original_text}" -> "{cleaned_text}"')
                if original_explanation != cleaned_explanation:
                    self.stdout.write(f'  Explanation: "{original_explanation}" -> "{cleaned_explanation}"')
                
                if not dry_run:
                    question.question_text = cleaned_text
                    question.explanation = cleaned_explanation
                    question.save()
        
        # Update choices
        choices_updated = 0
        choices = Choice.objects.all()
        for choice in choices:
            original_text = choice.choice_text
            cleaned_text = self.remove_brackets(original_text)
            
            if original_text != cleaned_text:
                choices_updated += 1
                self.stdout.write(f'Choice {choice.id}: "{original_text}" -> "{cleaned_text}"')
                
                if not dry_run:
                    choice.choice_text = cleaned_text
                    choice.save()
        
        # Update exam and category names
        exams_updated = 0
        exams = Exam.objects.all()
        for exam in exams:
            original_name = exam.name
            original_description = exam.description or ''
            
            cleaned_name = self.remove_brackets(original_name)
            cleaned_description = self.remove_brackets(original_description)
            
            if original_name != cleaned_name or original_description != cleaned_description:
                exams_updated += 1
                if not dry_run:
                    exam.name = cleaned_name
                    exam.description = cleaned_description
                    exam.save()
        
        categories_updated = 0
        categories = Category.objects.all()
        for category in categories:
            original_name = category.name
            original_description = category.description or ''
            
            cleaned_name = self.remove_brackets(original_name)
            cleaned_description = self.remove_brackets(original_description)
            
            if original_name != cleaned_name or original_description != cleaned_description:
                categories_updated += 1
                if not dry_run:
                    category.name = cleaned_name
                    category.description = cleaned_description
                    category.save()
        
        topics_updated = 0
        topics = Topic.objects.all()
        for topic in topics:
            original_name = topic.name
            original_description = topic.description or ''
            
            cleaned_name = self.remove_brackets(original_name)
            cleaned_description = self.remove_brackets(original_description)
            
            if original_name != cleaned_name or original_description != cleaned_description:
                topics_updated += 1
                if not dry_run:
                    topic.name = cleaned_name
                    topic.description = cleaned_description
                    topic.save()
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\nWould update: {updated_count} questions, {choices_updated} choices, '
                f'{exams_updated} exams, {categories_updated} categories, {topics_updated} topics'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nSuccessfully updated: {updated_count} questions, {choices_updated} choices, '
                f'{exams_updated} exams, {categories_updated} categories, {topics_updated} topics'
            ))

