# ExamPrepQuiz - Django Exam Practice Quiz Platform

A comprehensive Django web application for practicing exams with multiple question types, detailed analytics, and a user-friendly interface.

## Features

### User System
- User registration and login (email or username + password)
- Password reset functionality
- User profile page with quiz history and statistics

### Exams & Categories
- Admin panel to create exam categories (e.g., Math, English, Biology)
- Create exams under each category (e.g., SAT, IELTS, Driving Test)
- Optional topics inside each exam

### Quiz/Question Management
- **Question Types:**
  - Multiple choice (single correct answer)
  - Multiple correct choices
  - True/False
- Each question includes:
  - Question text
  - Multiple choice options
  - Correct answer(s)
  - Explanation
  - Difficulty level (Easy, Medium, Hard)

### Taking a Quiz
- Randomized questions
- One-question-per-page interface
- Track current question progress
- Save answers as you go
- Submit quiz and view results

### Results Page
- Score summary with pass/fail indication
- Correct/incorrect breakdown
- Detailed explanations for each question
- Performance analytics:
  - Accuracy percentage
  - Time spent
  - Performance by difficulty level
  - Performance by topic

### Dashboard
- List of available exams
- User progress charts (Chart.js)
- Recently attempted quizzes
- Performance statistics

### Admin Panel
- Powerful Django admin customization
- Bulk import/export questions using CSV/Excel
- Comprehensive question management

### UI/Frontend
- Responsive layout using Bootstrap 5
- Clean exam-style interface
- Modern and intuitive design

## Technical Requirements

- **Backend:** Python 3.x, Django 4.x+, Django REST Framework
- **Database:** SQLite (default, easily switchable to PostgreSQL/MySQL)
- **Frontend:** Bootstrap 5, Chart.js

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download the Project
```bash
cd examquiz
```

### Step 2: Create a Virtual Environment (Recommended)
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Create a Superuser
```bash
python manage.py createsuperuser
```
Follow the prompts to create an admin account.

### Step 6: Seed Example Data (Optional)
```bash
python manage.py seed_data
```
This will create sample categories, exams, and questions for testing.

### Step 7: Run the Development Server
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Project Structure

```
examquiz/
├── examquiz/          # Main project directory
│   ├── settings.py   # Django settings
│   ├── urls.py       # Main URL configuration
│   └── wsgi.py       # WSGI configuration
├── quiz/             # Main app directory
│   ├── models.py     # Database models
│   ├── views.py      # View functions
│   ├── urls.py       # App URL routing
│   ├── admin.py      # Admin panel customization
│   ├── api_views.py  # REST API views
│   ├── serializers.py # API serializers
│   └── management/
│       └── commands/
│           └── seed_data.py  # Seed data command
├── templates/        # HTML templates
│   ├── base.html
│   └── quiz/
│       ├── home.html
│       ├── dashboard.html
│       ├── exam_list.html
│       ├── quiz_question.html
│       ├── quiz_result.html
│       └── ...
├── static/           # Static files (CSS, JS, images)
│   └── css/
│       └── style.css
├── manage.py        # Django management script
└── requirements.txt # Python dependencies
```

## Database Models

- **Category**: Exam categories (Math, English, etc.)
- **Exam**: Exams under each category
- **Topic**: Optional topics within exams
- **Question**: Questions with type, difficulty, and explanation
- **Choice**: Answer choices for questions
- **QuizSession**: Each quiz attempt by a user
- **UserAnswer**: User's answer to each question

## API Endpoints

The application includes REST API endpoints (using Django REST Framework):

- `GET /api/categories/` - List all categories
- `GET /api/exams/` - List all exams
- `GET /api/exams/{id}/questions/` - Get questions for an exam
- `POST /api/quiz-sessions/` - Start a new quiz session
- `POST /api/quiz-sessions/{id}/submit_answer/` - Submit an answer
- `POST /api/quiz-sessions/{id}/complete/` - Complete a quiz
- `GET /api/quiz-sessions/{id}/results/` - Get quiz results
- `GET /api/user-answers/` - List user answers

All API endpoints require authentication (except categories and exams listing).

## Switching Databases

### PostgreSQL
1. Install PostgreSQL and psycopg2:
```bash
pip install psycopg2-binary
```

2. Update `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'examquiz',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### MySQL
1. Install MySQL and mysqlclient:
```bash
pip install mysqlclient
```

2. Update `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'examquiz',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

## Admin Panel Features

Access the admin panel at `http://127.0.0.1:8000/admin/`

### Bulk Operations
- Export questions to CSV
- Export questions to Excel
- Import questions from CSV (placeholder - can be extended)

### Admin Features
- Inline editing for choices within questions
- Filtering and searching
- Custom display columns
- Score visualization

## Usage Guide

### For Students/Users
1. Register an account or login
2. Browse available exams from the dashboard or exam list
3. Start a quiz by clicking "Start Quiz"
4. Answer questions one by one (you can save answers and navigate)
5. Submit the quiz when finished
6. View detailed results with explanations
7. Track your progress on the dashboard

### For Administrators
1. Login to the admin panel (`/admin/`)
2. Create categories, exams, and topics
3. Add questions with choices
4. Mark correct answers
5. Export/import questions as needed
6. Monitor user quiz sessions and performance

## Customization

### Adding New Question Types
Edit `quiz/models.py` and add new choices to `QUESTION_TYPE_CHOICES` in the Question model.

### Styling
Modify `static/css/style.css` or update Bootstrap classes in templates.

### Email Configuration
For password reset emails, configure email settings in `settings.py`:
```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_password'
```

## Production Deployment

Before deploying to production:

1. Set `DEBUG = False` in `settings.py`
2. Change `SECRET_KEY` to a secure random value
3. Configure proper database (PostgreSQL recommended)
4. Set up static file serving (WhiteNoise or similar)
5. Configure proper email backend
6. Set `ALLOWED_HOSTS` in `settings.py`
7. Use environment variables for sensitive settings
8. Enable HTTPS

## Contributing

Feel free to fork this project and submit pull requests for improvements.

## License

This project is open source and available for educational purposes.

## Support

For issues or questions, please check the Django documentation or create an issue in the repository.

---

**Built with Django 4.x and Bootstrap 5**

