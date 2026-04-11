# Personal Finance Tracker with Expense Prediction

A Python-based web application for managing personal finances with machine learning-powered expense prediction.

## Features

- **User Authentication**: Secure registration and login system
- **Dashboard**: Personalized view with income, expenses, and balance summary
- **Income & Expense Management**: Add, edit, view, and delete transactions
- **Categorization**: Organize transactions by categories (food, transport, bills, etc.)
- **Filtering**: Filter by category, date, or amount
- **Visualization**: Interactive charts showing spending trends
- **Expense Prediction**: ML-powered predictions for future expenses
- **Data Export**: Export to CSV or Excel format
- **Backup & Restore**: Backup and restore user data

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Machine Learning**: Scikit-learn
- **Visualization**: Plotly

## Installation

1. Navigate to the project directory:
```bash
cd transaction_project
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://localhost:5000
```

6. Register a new account and start tracking your finances!

## First Time Setup

1. **Register**: Create a new account with a username, email, and password
2. **Add Transactions**: Start by adding your income and expense transactions
3. **Categorize**: Assign categories to each transaction for better tracking
4. **View Dashboard**: Check your financial summary and predictions
5. **Generate Reports**: View detailed reports and visualizations
6. **Export Data**: Export your data to CSV or Excel format
7. **Backup**: Create backups of your data for safekeeping

## Usage

1. Register a new account or login
2. Add your income and expense transactions
3. View your dashboard for financial overview
4. Check visualizations and predictions
5. Export data when needed

## Project Structure

```
transaction_project/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── auth.py                # Authentication routes
├── routes.py              # Main application routes
├── prediction.py          # ML prediction module
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── transactions.html
│   ├── add_transaction.html
│   ├── reports.html
│   └── export.html
├── static/                # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── instance/              # Database files (created automatically)
```

## License

MIT License

