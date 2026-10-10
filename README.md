# Automated Grant Proposal Evaluation

This repository contains the Django project and its `myapp` application.

## Setup

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set a private Django secret key for the current PowerShell session:

```powershell
$env:DJANGO_SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Initialize the local database and start the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

The secret key, local database, virtual environments, and generated Python files are excluded from Git.
