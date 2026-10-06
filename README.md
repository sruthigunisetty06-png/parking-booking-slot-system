# Parking Slot Booking System

A simple college-project implementation using **Python Flask + SQLite + HTML/CSS**.

## Features
- User registration with vehicle number/type
- User login and booking history
- Two-wheeler and four-wheeler slots
- Date/time-based slot availability checking
- Automatic unique Booking ID
- Operator dashboard
- Add parking slots
- Record vehicle entry and exit
- Automatic parking charge calculation
  - Two-wheeler: ₹20/hour
  - Four-wheeler: ₹40/hour
  - Partial hours are rounded up
- SQLite database created automatically

## Requirements
- Python 3.10+
- pip

## Run on Windows
1. Open Command Prompt in this folder.
2. Create a virtual environment:
   `python -m venv venv`
3. Activate it:
   `venv\Scripts\activate`
4. Install packages:
   `pip install -r requirements.txt`
5. Start:
   `python app.py`
6. Open:
   `http://127.0.0.1:5000`

## Run on Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## Operator
For this starter project, the operator dashboard is available at:
`http://127.0.0.1:5000/operator`

For a production system, add a proper operator account/role and password hashing.

## Important
This is a demonstration/college-project starter. Before production use, add password hashing, CSRF protection, stronger validation, role-based authorization, payment integration, and deployment configuration.
