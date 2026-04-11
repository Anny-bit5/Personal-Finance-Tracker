from datetime import datetime, timedelta
from models import Transaction, Category
import json

def get_monthly_summary(user_id, year=None, month=None):
    """Get monthly income and expense summary"""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    transactions = Transaction.query.filter_by(user_id=user_id).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()
    
    income = sum(t.amount for t in transactions if t.type == 'income')
    expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = income - expense
    
    return {
        'income': income,
        'expense': expense,
        'balance': balance,
        'transactions': len(transactions)
    }

def get_category_breakdown(user_id, year=None, month=None, transaction_type='expense'):
    """Get breakdown of expenses/income by category"""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    transactions = Transaction.query.filter_by(
        user_id=user_id,
        type=transaction_type
    ).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()
    
    category_totals = {}
    for transaction in transactions:
        cat_name = transaction.category.name
        category_totals[cat_name] = category_totals.get(cat_name, 0) + transaction.amount
    
    return category_totals

def get_yearly_summary(user_id, year=None):
    """Get yearly income and expense summary"""
    if year is None:
        year = datetime.now().year
    
    # Calculate date range for the year
    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year + 1, 1, 1).date()
    
    transactions = Transaction.query.filter_by(user_id=user_id).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()
    
    monthly_data = {}
    for month in range(1, 13):
        monthly_data[month] = {'income': 0, 'expense': 0}
    
    for transaction in transactions:
        month = transaction.date.month
        if transaction.type == 'income':
            monthly_data[month]['income'] += transaction.amount
        else:
            monthly_data[month]['expense'] += transaction.amount
    
    return monthly_data

