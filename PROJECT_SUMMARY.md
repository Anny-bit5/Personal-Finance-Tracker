# Personal Finance Tracker - Project Summary

## Project Overview
A complete web application for personal finance management with machine learning-powered expense prediction.

## Features Implemented

### ✅ User Authentication & Dashboard
- Secure user registration with password hashing
- Login/logout functionality
- Personalized dashboard showing:
  - Total income, expenses, and balance
  - Month-over-month comparison
  - Recent transactions
  - Expense prediction

### ✅ Expense and Income Management
- Add new transactions (income/expense)
- Edit existing transactions
- Delete transactions
- View all transactions with filtering by:
  - Type (income/expense)
  - Category
  - Date range
  - Amount

### ✅ Visualization of Financial Data
- Interactive pie charts for category breakdown (Plotly)
- Line charts for expense trends
- Bar charts for yearly income vs expenses
- Monthly and yearly reports
- Real-time data visualization

### ✅ Expense Prediction Module
- Machine learning models (Linear Regression + Random Forest)
- Predicts next month's expenses based on historical data
- Confidence levels (high/medium/low)
- Requires minimum 3 months of data

### ✅ Data Export and Backup
- Export to CSV format
- Export to Excel format
- Create JSON backup files
- Restore from backup files
- Duplicate detection during restore

## Technology Stack

### Backend
- **Flask**: Web framework
- **Flask-Login**: User session management
- **Flask-SQLAlchemy**: Database ORM
- **SQLite**: Database (easy to use, no setup required)

### Frontend
- **HTML5/CSS3**: Structure and styling
- **Bootstrap 5**: Responsive UI framework
- **JavaScript**: Client-side interactions
- **Plotly**: Interactive charts and graphs

### Machine Learning
- **Scikit-learn**: ML models (Linear Regression, Random Forest)
- **Pandas**: Data manipulation
- **NumPy**: Numerical operations

### Data Export
- **Pandas**: Data processing
- **OpenPyXL**: Excel file generation

## Project Structure

```
transaction_project/
├── app.py                 # Main Flask application
├── models.py              # Database models (User, Transaction, Category)
├── auth.py                # Authentication routes (login, register, logout)
├── routes.py              # Main application routes (dashboard, transactions, reports, etc.)
├── prediction.py          # ML prediction module
├── utils.py               # Utility functions (summaries, breakdowns)
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── SETUP.md              # Setup instructions
├── .gitignore            # Git ignore file
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── transactions.html
│   ├── add_transaction.html
│   ├── edit_transaction.html
│   ├── reports.html
│   └── restore.html
└── static/               # Static files
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Database Schema

### Users Table
- id (Primary Key)
- username (Unique)
- email (Unique)
- password_hash
- created_at

### Categories Table
- id (Primary Key)
- name (Unique)

### Transactions Table
- id (Primary Key)
- user_id (Foreign Key → Users)
- category_id (Foreign Key → Categories)
- type (income/expense)
- amount
- description
- date
- created_at

## Default Categories
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

## Security Features
- Password hashing using Werkzeug
- User session management
- Ownership verification for transactions
- SQL injection protection (SQLAlchemy ORM)

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Open browser:
   ```
   http://localhost:5000
   ```

## Key Features Highlights

1. **Easy to Use**: Clean, intuitive interface with Bootstrap styling
2. **Comprehensive**: All required features implemented
3. **ML-Powered**: Expense prediction using scikit-learn
4. **Visual**: Interactive charts with Plotly
5. **Exportable**: Multiple export formats (CSV, Excel, JSON)
6. **Secure**: Password hashing and session management
7. **Responsive**: Works on desktop and mobile devices

## Future Enhancements (Optional)
- Budget setting and tracking
- Recurring transactions
- Email notifications
- Multi-currency support
- Advanced analytics
- Mobile app version

## Notes
- Database is created automatically on first run
- Default categories are created automatically
- All user data is stored locally in SQLite database
- ML predictions improve with more historical data

