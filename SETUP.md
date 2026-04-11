# Quick Setup Guide

## Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

## Step-by-Step Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

The application will:
- Create the SQLite database automatically
- Initialize default categories
- Start the Flask development server on http://localhost:5000

### 3. Access the Application
Open your web browser and go to:
```
http://localhost:5000
```

### 4. Create Your Account
- Click "Register" to create a new account
- Fill in your username, email, and password
- Login with your credentials

### 5. Start Using the Application
- Add your first transaction (income or expense)
- View your dashboard for financial overview
- Check predictions and visualizations
- Export or backup your data

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, edit `app.py` and change:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```
to a different port (e.g., 5001).

### Database Issues
If you encounter database errors, delete the `finance_tracker.db` file and restart the application. The database will be recreated automatically.

### Missing Dependencies
If you get import errors, make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Default Categories
The application comes with these default categories:
- Food
- Transport
- Bills
- Shopping
- Entertainment
- Healthcare
- Education
- Salary
- Freelance
- Investment
- Other

You can use these categories when adding transactions.

