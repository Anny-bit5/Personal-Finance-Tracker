from models import Transaction, db
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np

def prepare_training_data(user_id, months_back=12):
    """Prepare historical data for training"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months_back * 30)
    
    transactions = Transaction.query.filter_by(
        user_id=user_id,
        type='expense'
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    if len(transactions) < 3:
        return None, None
    
    # Group by month
    monthly_expenses = {}
    for transaction in transactions:
        month_key = f"{transaction.date.year}-{transaction.date.month:02d}"
        monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + transaction.amount
    
    # Convert to DataFrame
    data = []
    for month_key, amount in sorted(monthly_expenses.items()):
        year, month = map(int, month_key.split('-'))
        # Create a numeric feature (months since start)
        months_since_start = (year - start_date.year) * 12 + (month - start_date.month)
        data.append({
            'month': months_since_start,
            'amount': amount,
            'year': year,
            'month_num': month
        })
    
    df = pd.DataFrame(data)
    
    if len(df) < 3:
        return None, None
    
    X = df[['month']].values
    y = df['amount'].values
    
    return X, y

def predict_next_month_expense(user_id):
    """Predict expense for the next month using ML models"""
    X, y = prepare_training_data(user_id)
    
    if X is None or len(X) < 3:
        return {
            'prediction': None,
            'confidence': 'low',
            'message': 'Insufficient data for prediction. Need at least 3 months of expense data.'
        }
    
    # Train Linear Regression model
    lr_model = LinearRegression()
    lr_model.fit(X, y)
    
    # Train Random Forest model
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)
    
    # Predict next month
    next_month = X[-1][0] + 1
    lr_prediction = lr_model.predict([[next_month]])[0]
    rf_prediction = rf_model.predict([[next_month]])[0]
    
    # Average of both models
    avg_prediction = (lr_prediction + rf_prediction) / 2
    
    # Calculate confidence based on data quality
    if len(X) >= 6:
        confidence = 'high'
    elif len(X) >= 4:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return {
        'prediction': round(avg_prediction, 2),
        'lr_prediction': round(lr_prediction, 2),
        'rf_prediction': round(rf_prediction, 2),
        'confidence': confidence,
        'data_points': len(X),
        'message': f'Based on {len(X)} months of historical data'
    }

def get_expense_trend(user_id, months=6):
    """Get expense trend for visualization"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months * 30)
    
    transactions = Transaction.query.filter_by(
        user_id=user_id,
        type='expense'
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    monthly_expenses = {}
    for transaction in transactions:
        month_key = f"{transaction.date.year}-{transaction.date.month:02d}"
        monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + transaction.amount
    
    # Format for chart
    labels = []
    values = []
    for month_key in sorted(monthly_expenses.keys()):
        labels.append(month_key)
        values.append(monthly_expenses[month_key])
    
    return labels, values

