import os
import csv
import re
from pathlib import Path
from io import StringIO
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from quiz.models import Category, Exam, Topic, Question, Choice


class Command(BaseCommand):
    help = 'Import questions from CSV files in the inbox folder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--inbox-folder',
            type=str,
            default='inbox',
            help='Folder path relative to project root containing CSV files (default: inbox)'
        )
        parser.add_argument(
            '--auto-process',
            action='store_true',
            help='Automatically process all CSV files in inbox folder'
        )

    def handle(self, *args, **options):
        inbox_folder = options['inbox_folder']
        auto_process = options['auto_process']
        
        # Get absolute path to inbox folder
        base_dir = Path(settings.BASE_DIR)
        inbox_path = base_dir / inbox_folder
        
        # Create inbox, processed, and failed folders if they don't exist
        inbox_path.mkdir(exist_ok=True)
        processed_path = inbox_path.parent / 'processed'
        failed_path = inbox_path.parent / 'failed'
        processed_path.mkdir(exist_ok=True)
        failed_path.mkdir(exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS(f'Looking for CSV files in: {inbox_path}'))
        
        # Find all CSV files
        csv_files = list(inbox_path.glob('*.csv'))
        
        if not csv_files:
            self.stdout.write(self.style.WARNING('No CSV files found in inbox folder.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(csv_files)} CSV file(s) to process.'))
        
        # Process each CSV file
        for csv_file in csv_files:
            self.stdout.write(f'\nProcessing: {csv_file.name}')
            success = self.process_csv_file(csv_file, processed_path, failed_path)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'Successfully processed {csv_file.name}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to process {csv_file.name}'))

    def normalize_column_name(self, col_name):
        """Normalize column name to lowercase and remove spaces"""
        if not col_name:
            return None
        # Convert to lowercase and strip whitespace
        normalized = col_name.lower().strip()
        # Replace spaces with underscores
        normalized = normalized.replace(' ', '_')
        return normalized
    
    def map_csv_columns(self, fieldnames):
        """Map CSV column names to standard format (case-insensitive)"""
        column_map = {}
        normalized_fieldnames = {self.normalize_column_name(col): col for col in fieldnames}
        
        # Map variations of column names
        mappings = {
            'category': ['category', 'cat'],
            'exam': ['exam', 'exam_name'],
            'question_text': ['question_text', 'question', 'question_text', 'questiontext'],
            'topic': ['topic'],
            'difficulty': ['difficulty', 'diff'],
            'explanation': ['explanation', 'expl'],
            'points': ['points', 'point'],
            'question_type': ['question_type', 'type', 'qtype'],
            'correct_answer': ['correct_answer', 'correct_choices', 'correct', 'answer'],
            'choice_1': ['choice_1', 'choice1', 'option_1', 'option1'],
            'choice_2': ['choice_2', 'choice2', 'option_2', 'option2'],
            'choice_3': ['choice_3', 'choice3', 'option_3', 'option3'],
            'choice_4': ['choice_4', 'choice4', 'option_4', 'option4'],
            'choice_5': ['choice_5', 'choice5', 'option_5', 'option5'],
            'choice_6': ['choice_6', 'choice6', 'option_6', 'option6'],
            'choices': ['choices'],
        }
        
        for standard_name, variations in mappings.items():
            for variation in variations:
                if variation in normalized_fieldnames:
                    column_map[standard_name] = normalized_fieldnames[variation]
                    break
        
        return column_map

    def process_csv_file(self, csv_file, processed_path, failed_path):
        """Process a single CSV file and import questions"""
        errors = []
        questions_created = 0
        questions_updated = 0
        choices_created = 0
        
        f = None
        try:
            # Try UTF-8 first, fallback to UTF-8-sig or latin-1
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    f = open(csv_file, 'r', encoding=encoding, errors='replace')
                    f.read(1024)  # Test read
                    f.seek(0)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    if f:
                        f.close()
                        f = None
                    continue
            
            if not f:
                raise ValueError('Could not determine file encoding')
            
            # Read entire file content to preprocess brackets
            content = f.read()
            f.close()
            
            # Preprocess: Handle fields wrapped in square brackets [field]
            # This format allows fields with commas: [Category],[Exam],[Question Text],...
            # Strategy: Replace commas inside [] brackets with a placeholder, then restore after CSV parsing
            
            # Pattern to match brackets with any content (including commas, quotes, etc.)
            bracket_pattern = r'\[([^\]]*)\]'
            
            def replace_comma_in_brackets(match):
                bracket_content = match.group(1)
                # Replace commas with placeholder so CSV parser doesn't split on them
                return '[' + bracket_content.replace(',', '___COMMA_PLACEHOLDER___') + ']'
            
            # Replace all brackets with comma-safe versions
            processed_content = re.sub(bracket_pattern, replace_comma_in_brackets, content)
            
            # Also handle quoted fields for compatibility
            quoted_pattern = r'"([^"]+)"'
            def replace_comma_in_quotes(match):
                quoted_content = match.group(1)
                return '"' + quoted_content.replace(',', '___COMMA_PLACEHOLDER___') + '"'
            
            processed_content = re.sub(quoted_pattern, replace_comma_in_quotes, processed_content)
            
            # Detect delimiter (should be comma after bracket processing)
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(processed_content[:1024]).delimiter
            except csv.Error:
                # Default to comma if detection fails
                delimiter = ','
            
            # Create a StringIO object from processed content
            processed_file = StringIO(processed_content)
            
            reader = csv.DictReader(processed_file, delimiter=delimiter)
            raw_fieldnames = list(reader.fieldnames or [])
            
            # Clean fieldnames: remove brackets and restore commas
            cleaned_fieldnames = []
            for fieldname in raw_fieldnames:
                # Remove brackets if present
                fieldname = fieldname.strip()
                if fieldname.startswith('[') and fieldname.endswith(']'):
                    fieldname = fieldname[1:-1].strip()
                # Remove quotes if present
                elif fieldname.startswith('"') and fieldname.endswith('"'):
                    fieldname = fieldname[1:-1].strip()
                # Restore commas from placeholder
                fieldname = fieldname.replace('___COMMA_PLACEHOLDER___', ',')
                cleaned_fieldnames.append(fieldname)
            
            # Update reader fieldnames
            reader.fieldnames = cleaned_fieldnames
            fieldnames = cleaned_fieldnames
            
            if not fieldnames:
                raise ValueError('CSV file has no headers')
            
            # Map columns to standard format (case-insensitive)
            column_map = {}
            normalized_fieldnames = {self.normalize_column_name(col): col for col in fieldnames}
            
            # Direct mapping with variations
            column_mappings = {
                'category': ['category', 'cat'],
                'exam': ['exam', 'exam_name'],
                'question_text': ['question_text', 'question', 'questiontext', 'q'],
                'topic': ['topic'],
                'difficulty': ['difficulty', 'diff'],
                'explanation': ['explanation', 'expl'],
                'points': ['points', 'point'],
                'question_type': ['question_type', 'type', 'qtype'],
                'correct_answer': ['correct_answer', 'correct_choices', 'correct', 'answer', 'right_answer'],
            }
            
            # Map standard columns
            for standard_name, variations in column_mappings.items():
                for variation in variations:
                    if variation in normalized_fieldnames:
                        column_map[standard_name] = normalized_fieldnames[variation]
                        break
            
            # Map choice columns (Choice 1, Choice 2, etc.)
            for i in range(1, 7):
                choice_variations = [f'choice_{i}', f'choice{i}', f'option_{i}', f'option{i}']
                for variation in choice_variations:
                    if variation in normalized_fieldnames:
                        column_map[f'choice_{i}'] = normalized_fieldnames[variation]
                        break
            
            # Also check for 'choices' column
            if 'choices' in normalized_fieldnames:
                column_map['choices'] = normalized_fieldnames['choices']
            
            # Check if we have required columns
            if 'exam' not in column_map or 'question_text' not in column_map:
                raise ValueError(
                    f'Missing required columns. Found: {", ".join(fieldnames)}. '
                    f'Need: exam (or Exam) and question_text (or Question Text)'
                )
            
            # Check if we have any choice columns
            has_choice_columns = any(f'choice_{i}' in column_map for i in range(1, 7))
            has_choices_column = 'choices' in column_map
            
            if not (has_choice_columns or has_choices_column):
                raise ValueError(
                    'No choice columns found. Need either separate Choice 1, Choice 2, etc. columns '
                    'or a "choices" column with pipe-separated values'
                )
            
            # Process each row
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                        
                    try:
                        # Convert row to use mapped column names
                        # Clean all values: remove brackets, quotes, and restore commas
                        mapped_row = {}
                        for standard_name, original_name in column_map.items():
                            value = row.get(original_name, '')
                            
                            # Clean value: remove brackets/quotes and restore commas
                            if isinstance(value, str):
                                value = value.strip()
                                # Remove outer brackets if entire field is wrapped (CSV format)
                                if value.startswith('[') and value.endswith(']'):
                                    value = value[1:-1].strip()
                                # Remove quotes if present
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1].strip()
                                # Restore commas from placeholder (commas inside brackets)
                                value = value.replace('___COMMA_PLACEHOLDER___', ',')
                            mapped_row[standard_name] = value
                        
                        # After mapping, remove ALL brackets from text fields (for GUI display)
                        # This ensures no brackets appear in the database
                        text_fields = ['question_text', 'explanation', 'category', 'exam', 'topic']
                        for field in text_fields:
                            if field in mapped_row and isinstance(mapped_row[field], str):
                                # Remove all brackets from text content
                                mapped_row[field] = mapped_row[field].replace('[', '').replace(']', '')
                        
                        # Remove brackets from all choice fields
                        for i in range(1, 7):
                            choice_key = f'choice_{i}'
                            if choice_key in mapped_row and isinstance(mapped_row[choice_key], str):
                                mapped_row[choice_key] = mapped_row[choice_key].replace('[', '').replace(']', '')
                        
                        # Remove brackets from correct_answer
                        if 'correct_answer' in mapped_row and isinstance(mapped_row['correct_answer'], str):
                            mapped_row['correct_answer'] = mapped_row['correct_answer'].replace('[', '').replace(']', '')
                        
                        result = self.process_row(mapped_row, row_num, has_choice_columns)
                        if result['created']:
                            questions_created += 1
                        else:
                            questions_updated += 1
                        choices_created += result['choices_count']
                    except Exception as e:
                        error_msg = f'Row {row_num}: {str(e)}'
                        errors.append(error_msg)
                        # Handle Unicode encoding errors in error messages
                        try:
                            self.stdout.write(self.style.ERROR(f'  {error_msg}'))
                        except UnicodeEncodeError:
                            safe_msg = error_msg.encode('ascii', 'ignore').decode('ascii')
                            self.stdout.write(self.style.ERROR(f'  {safe_msg}'))
            
            # Close file before moving it
            if f:
                f.close()
                f = None
            
            # Process results after file is closed
            if errors:
                # Move to failed folder with error log
                error_log_path = failed_path / f'{csv_file.stem}_errors.txt'
                with open(error_log_path, 'w', encoding='utf-8', errors='replace') as log_file:
                    log_file.write(f'Errors processing {csv_file.name}:\n\n')
                    for error in errors:
                        safe_error = str(error).encode('utf-8', errors='replace').decode('utf-8')
                        log_file.write(f'{safe_error}\n')
                
                dest_path = failed_path / csv_file.name
                # Remove existing file if it exists
                if dest_path.exists():
                    dest_path.unlink()
                csv_file.rename(dest_path)
                self.stdout.write(self.style.WARNING(
                    f'  Moved to failed folder. {questions_created + questions_updated} questions processed, '
                    f'{len(errors)} errors encountered.'
                ))
                return False
            else:
                # Move to processed folder
                dest_path = processed_path / csv_file.name
                # Remove existing file if it exists
                if dest_path.exists():
                    dest_path.unlink()
                csv_file.rename(dest_path)
                self.stdout.write(self.style.SUCCESS(
                    f'  Created: {questions_created}, Updated: {questions_updated}, '
                    f'Choices: {choices_created}'
                ))
                return True
                
        except Exception as e:
            error_msg = f'Error processing file: {str(e)}'
            self.stdout.write(self.style.ERROR(f'  {error_msg}'))
            
            # Move to failed folder
            error_log_path = failed_path / f'{csv_file.stem}_errors.txt'
            with open(error_log_path, 'w', encoding='utf-8', errors='replace') as log_file:
                safe_error_msg = str(error_msg).encode('utf-8', errors='replace').decode('utf-8')
                log_file.write(f'Error processing {csv_file.name}:\n\n{safe_error_msg}\n')
            
                dest_path = failed_path / csv_file.name
            # Remove existing file if it exists
            if dest_path.exists():
                dest_path.unlink()
            csv_file.rename(dest_path)
            return False
        finally:
            # Ensure file is closed
            if f:
                f.close()

    def remove_all_brackets(self, text):
        """Remove all square brackets from text (used for GUI display)"""
        if not isinstance(text, str):
            return text
        # Remove all [ and ] characters
        return text.replace('[', '').replace(']', '')
    
    def process_row(self, row, row_num, has_choice_columns=False):
        """Process a single row and create/update question"""
        # Get or create category
        category_name = row.get('category', 'General').strip()
        if not category_name:
            category_name = 'General'
        # Remove brackets from category name
        category_name = self.remove_all_brackets(category_name)
        category, _ = Category.objects.get_or_create(
            name=category_name,
            defaults={'description': f'Category for {category_name} exams'}
        )
        
        # Get or create exam
        exam_name = row.get('exam', '').strip()
        if not exam_name:
            raise ValueError('exam name cannot be empty')
        # Remove brackets from exam name
        exam_name = self.remove_all_brackets(exam_name)
        
        exam, _ = Exam.objects.get_or_create(
            category=category,
            name=exam_name,
            defaults={
                'description': self.remove_all_brackets(row.get('exam_description', '')),
                'duration_minutes': int(row.get('duration_minutes', 60)) if row.get('duration_minutes', '').strip() else 60,
                'total_questions': int(row.get('total_questions', 10)) if row.get('total_questions', '').strip() else 10,
                'passing_score': int(row.get('passing_score', 60)) if row.get('passing_score', '').strip() else 60,
            }
        )
        
        # Get or create topic (optional)
        topic = None
        if row.get('topic', '').strip():
            topic_name = self.remove_all_brackets(row['topic'].strip())
            topic, _ = Topic.objects.get_or_create(
                exam=exam,
                name=topic_name,
                defaults={
                    'description': self.remove_all_brackets(row.get('topic_description', '')),
                    'order': int(row.get('topic_order', 0)) if row.get('topic_order', '').strip() else 0
                }
            )
        
        # Parse question data - remove all brackets from question text
        question_text = self.remove_all_brackets(row.get('question_text', '').strip())
        if not question_text:
            raise ValueError('question_text cannot be empty')
        
        question_type = row.get('question_type', 'single').strip().lower()
        if question_type not in ['single', 'multiple', 'true_false']:
            question_type = 'single'
        
        difficulty = row.get('difficulty', 'medium').strip().lower()
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
        
        # Remove brackets from explanation
        explanation = self.remove_all_brackets(row.get('explanation', '').strip())
        
        # Safely parse points
        points_str = row.get('points', '1').strip()
        try:
            points = int(points_str) if points_str else 1
        except (ValueError, TypeError):
            points = 1  # Default to 1 if parsing fails
        
        # Safely parse order
        order_str = row.get('order', '0').strip()
        try:
            order = int(order_str) if order_str else 0
        except (ValueError, TypeError):
            order = 0  # Default to 0 if parsing fails
        is_active = row.get('is_active', 'true').strip().lower() in ['true', '1', 'yes', 'y', '']
        
        # Create or update question
        question, created = Question.objects.update_or_create(
            exam=exam,
            question_text=question_text,
            defaults={
                'topic': topic,
                'question_type': question_type,
                'difficulty': difficulty,
                'explanation': explanation,
                'points': points,
                'order': order,
                'is_active': is_active,
            }
        )
        
        # Parse choices - support both formats, and remove brackets from all choices
        choices_list = []
        
        if has_choice_columns:
            # Format with separate columns: Choice 1, Choice 2, etc.
            for i in range(1, 7):  # Support up to 6 choices
                choice_key = f'choice_{i}'
                if choice_key in row and row[choice_key].strip():
                    choice_text = self.remove_all_brackets(row[choice_key].strip())
                    if choice_text:
                        choices_list.append(choice_text)
        else:
            # Format with pipe-separated choices column
            choices_text = row.get('choices', '').strip()
            if choices_text:
                choices_text = self.remove_all_brackets(choices_text)
                choices_list = [self.remove_all_brackets(c.strip()) for c in choices_text.split('|') if c.strip()]
        
        if not choices_list:
            raise ValueError('At least one choice is required')
        
        # Parse correct answer(s) - remove brackets from correct answer text
        correct_answer_text = self.remove_all_brackets(
            row.get('correct_answer', '').strip() or row.get('correct_choices', '').strip()
        )
        correct_indices = []
        
        if correct_answer_text:
            # Try to match by exact text first (case-insensitive, trimmed)
            for idx, choice_text in enumerate(choices_list):
                if choice_text.strip().lower() == correct_answer_text.strip().lower():
                    correct_indices.append(idx)
                    break
            
            # If not found by exact text, try partial/fuzzy matching (case-insensitive)
            if not correct_indices:
                correct_lower = correct_answer_text.strip().lower()
                for idx, choice_text in enumerate(choices_list):
                    choice_lower = choice_text.strip().lower()
                    # Check if correct answer text is contained in choice or vice versa
                    if (correct_lower in choice_lower or choice_lower in correct_lower):
                        correct_indices.append(idx)
                        # For single choice questions, break after first match
                        if question_type == 'single':
                            break
            
            # If still not found, check if correct answer appears in question text
            # This handles cases where the answer value is in the question (e.g., "Odd one out: 5,11,17,22,29" with answer "5")
            if not correct_indices:
                question_lower = question_text.lower()
                correct_lower = correct_answer_text.strip().lower()
                
                # Check if answer appears in question and try to match with choices
                if correct_lower in question_lower:
                    # Try to match answer with choice that contains it or is closest
                    for idx, choice_text in enumerate(choices_list):
                        choice_lower = choice_text.strip().lower()
                        # Check if the correct answer text matches choice exactly when trimmed
                        # or if choice contains the answer
                        if correct_lower == choice_lower or correct_lower in choice_lower:
                            correct_indices.append(idx)
                            break
                        # Also check if answer is a number that appears in choice
                        try:
                            answer_num = int(correct_lower)
                            if str(answer_num) in choice_text or correct_lower in choice_text:
                                correct_indices.append(idx)
                                break
                        except ValueError:
                            pass
            
            # If still not found, try parsing as 1-indexed choice number
            if not correct_indices:
                try:
                    # Try as single number (1-indexed)
                    choice_num = int(correct_answer_text.strip())
                    if 1 <= choice_num <= len(choices_list):
                        correct_indices.append(choice_num - 1)
                except ValueError:
                    # Try comma-separated indices (1-indexed)
                    try:
                        indices = [int(x.strip()) for x in correct_answer_text.split(',')]
                        correct_indices = [idx - 1 for idx in indices if 1 <= idx <= len(choices_list)]
                    except ValueError:
                        # Try pipe-separated indices
                        try:
                            indices = [int(x.strip()) for x in correct_answer_text.split('|')]
                            correct_indices = [idx - 1 for idx in indices if 1 <= idx <= len(choices_list)]
                        except ValueError:
                            # Try pipe-separated choice texts (case-insensitive)
                            correct_choices_list = [c.strip().lower() for c in correct_answer_text.split('|') if c.strip()]
                            for i, choice in enumerate(choices_list):
                                choice_lower = choice.strip().lower()
                                for correct_choice in correct_choices_list:
                                    if correct_choice == choice_lower or correct_choice in choice_lower or choice_lower in correct_choice:
                                        if i not in correct_indices:
                                            correct_indices.append(i)
            
            # For multiple choice questions, try to match all correct answers
            if not correct_indices and '|' in correct_answer_text:
                correct_choices_list = [c.strip().lower() for c in correct_answer_text.split('|') if c.strip()]
                for i, choice in enumerate(choices_list):
                    choice_lower = choice.strip().lower()
                    # Check if any part of the choice matches
                    for correct_choice in correct_choices_list:
                        if correct_choice in choice_lower or choice_lower in correct_choice:
                            if i not in correct_indices:
                                correct_indices.append(i)
        
        if not correct_indices:
            # Last resort: provide helpful error message
            error_msg = f'Could not determine correct answer. Provided: "{correct_answer_text}". Choices: {choices_list}'
            raise ValueError(error_msg)
        
        # Validate indices
        for idx in correct_indices:
            if idx < 0 or idx >= len(choices_list):
                raise ValueError(f'Invalid correct choice index: {idx + 1}')
        
        # Delete existing choices and create new ones
        question.choices.all().delete()
        choices_count = 0
        
        for idx, choice_text in enumerate(choices_list):
            is_correct = idx in correct_indices
            Choice.objects.create(
                question=question,
                choice_text=choice_text,
                is_correct=is_correct,
                order=idx
            )
            choices_count += 1
        
        return {
            'created': created,
            'choices_count': choices_count
        }

