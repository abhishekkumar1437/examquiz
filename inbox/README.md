# CSV Import Instructions

Place CSV files in this `inbox` folder to automatically import questions into the database.

## CSV File Format

**Important:** All fields can be wrapped in square brackets `[]` to prevent CSV parsing errors. This is especially useful when fields contain commas. The brackets will be automatically removed during import and will NOT appear in the database.

### Supported Format (all fields in brackets):
```csv
[Category],[Exam],[Question Text],[Choice 1],[Choice 2],[Choice 3],[Choice 4],[Correct Answer],[Explanation],[Difficulty],[Topic],[Points],[Question Type]
[ASI Bihar Exam],[Practice Set-1],[Which river flows through Bihar?],[Ganga],[Yamuna],[Godavari],[Krishna],[Ganga],[The Ganga river flows through Bihar],[easy],[Geography],[1],[single]
```

### Alternative Format (brackets only for fields with commas):
```csv
Category,Exam,Question Text,...
Math,SAT,[Solve for x: x + 5 = 10, find x],...
```

Both formats are supported. When using brackets, they will be automatically stripped from all values before saving to the database.

Your CSV file should have the following columns:

### Required Columns:
- **exam** - Name of the exam (e.g., "SAT Mathematics")
- **question_text** - The question text
- **choices** - Pipe-separated list of choices (e.g., "Option 1|Option 2|Option 3|Option 4")

### Optional Columns:
- **category** - Category name (defaults to "General")
- **topic** - Topic name within the exam (optional)
- **topic_description** - Description of the topic
- **topic_order** - Order number for the topic
- **exam_description** - Description of the exam
- **duration_minutes** - Exam duration in minutes (default: 60)
- **total_questions** - Total questions in exam (default: 10)
- **passing_score** - Passing percentage (default: 60)
- **question_type** - Type of question: "single", "multiple", or "true_false" (default: "single")
- **difficulty** - Difficulty level: "easy", "medium", or "hard" (default: "medium")
- **explanation** - Explanation shown after quiz completion
- **points** - Points for this question (default: 1)
- **order** - Order of question in exam (default: 0)
- **is_active** - Whether question is active: "true" or "false" (default: "true")
- **correct_choices** - Correct choice(s). Can be:
  - Comma-separated indices: "1,3" (1-indexed)
  - Pipe-separated indices: "1|3"
  - Pipe-separated choice texts: "Option 1|Option 3"

## Example CSV Format

```csv
category,exam,question_text,choices,correct_choices,question_type,difficulty,explanation
Mathematics,SAT Math,What is 2+2?,2|3|4|5,3,single,easy,2+2 equals 4
Mathematics,SAT Math,Solve for x: x²-4=0,x=2|x=-2|x=4|x=-4,"1,2",multiple,medium,Factoring gives (x-2)(x+2)=0
Science,Biology,The cell is the basic unit of life,True|False,1,true_false,easy,All living organisms are made of cells
```

## How to Import

1. Create a CSV file following the format above
2. Place it in this `inbox` folder
3. Run the import command:
   ```bash
   python manage.py import_questions_csv
   ```
4. Processed files will be moved to `processed/` folder
5. Failed files will be moved to `failed/` folder with error logs

## Notes

- Categories and exams will be created automatically if they don't exist
- Questions with the same text in the same exam will be updated (not duplicated)
- Choices are replaced when updating a question
- All operations are atomic - either all rows in a file succeed or none are saved

