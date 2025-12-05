#!/bin/bash

echo "Setting up ExamPrepQuiz Django Project..."
echo

echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error creating virtual environment"
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing dependencies"
    exit 1
fi

echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

echo
echo "Setup complete!"
echo
echo "Next steps:"
echo "1. Create a superuser: python manage.py createsuperuser"
echo "2. Seed example data: python manage.py seed_data"
echo "3. Run server: python manage.py runserver"
echo

