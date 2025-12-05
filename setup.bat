@echo off
echo Setting up ExamPrepQuiz Django Project...
echo.

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error creating virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies
    pause
    exit /b 1
)

echo Running migrations...
python manage.py makemigrations
python manage.py migrate

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Create a superuser: python manage.py createsuperuser
echo 2. Seed example data: python manage.py seed_data
echo 3. Run server: python manage.py runserver
echo.
pause

