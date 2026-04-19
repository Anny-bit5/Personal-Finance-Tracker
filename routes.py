from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Transaction, Category, User
from datetime import datetime, timedelta
from utils import get_monthly_summary, get_category_breakdown, get_yearly_summary
from prediction import predict_next_month_expense, get_expense_trend
import pandas as pd
import numpy as np
import json
import os
import io

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get current month summary
    now = datetime.now()
    current_month = get_monthly_summary(current_user.id, now.year, now.month)
    # 1. Calculate or fetch your data
    # data:
    prediction_value = {"prediction": 2934.75, "confidence": "low"}
    
    # Get previous month for comparison
    if now.month == 1:
        prev_month = get_monthly_summary(current_user.id, now.year - 1, 12)
    else:
        prev_month = get_monthly_summary(current_user.id, now.year, now.month - 1)
    
    # Get category breakdown
    category_breakdown = get_category_breakdown(current_user.id, now.year, now.month, 'expense')
    
    # Convert category breakdown to lists for template
    category_labels = list(category_breakdown.keys()) if category_breakdown else []
    category_values = list(category_breakdown.values()) if category_breakdown else []
    
    # Get expense prediction
    prediction = predict_next_month_expense(current_user.id)
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
        .limit(10).all()
    
    # Get expense trend
    trend_labels, trend_values = get_expense_trend(current_user.id, 6)
    
    return render_template('dashboard.html',
    next_month_pred=prediction_value,
                         current_month=current_month,
                         prev_month=prev_month,
                         category_breakdown=category_breakdown,
                         category_labels=category_labels,
                         category_values=category_values,
                         prediction=prediction,
                         recent_transactions=recent_transactions,
                         trend_labels=trend_labels,
                         trend_values=trend_values,
                         report_data=chart_data
                         )

@main_bp.route('/transactions')
@login_required
def transactions():
    # Get filter parameters
    transaction_type = request.args.get('type', 'all')
    category_id = request.args.get('category', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if transaction_type != 'all':
        query = query.filter_by(type=transaction_type)
    
    if category_id != 'all':
        query = query.filter_by(category_id=category_id)
    
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Get transactions
    transactions_list = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()
    
    # Get all categories for filter dropdown
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('transactions.html',
                         transactions=transactions_list,
                         categories=categories,
                         current_filters={
                             'type': transaction_type,
                             'category': category_id,
                             'start_date': start_date,
                             'end_date': end_date
                         })

@main_bp.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        transaction_type = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        date = request.form.get('date')
        
        # Validation
        if not category_id or not transaction_type or not amount or not date:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('main.add_transaction'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0.', 'danger')
                return redirect(url_for('main.add_transaction'))
            
            transaction_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            transaction = Transaction(
                user_id=current_user.id,
                category_id=int(category_id),
                type=transaction_type,
                amount=amount,
                description=description,
                date=transaction_date
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('main.transactions'))
            
        except ValueError:
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('main.add_transaction'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the transaction.', 'danger')
            return redirect(url_for('main.add_transaction'))
    
    # GET request - show form
    categories = Category.query.order_by(Category.name).all()
    return render_template('add_transaction.html', categories=categories)

@main_bp.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Check ownership
    if transaction.user_id != current_user.id:
        flash('You do not have permission to edit this transaction.', 'danger')
        return redirect(url_for('main.transactions'))
    
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        transaction_type = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        date = request.form.get('date')
        
        # Validation
        if not category_id or not transaction_type or not amount or not date:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0.', 'danger')
                return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
            
            transaction_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            transaction.category_id = int(category_id)
            transaction.type = transaction_type
            transaction.amount = amount
            transaction.description = description
            transaction.date = transaction_date
            
            db.session.commit()
            
            flash('Transaction updated successfully!', 'success')
            return redirect(url_for('main.transactions'))
            
        except ValueError:
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the transaction.', 'danger')
            return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
    
    # GET request - show form
    categories = Category.query.order_by(Category.name).all()
    return render_template('edit_transaction.html', transaction=transaction, categories=categories)

@main_bp.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Check ownership
    if transaction.user_id != current_user.id:
        flash('You do not have permission to delete this transaction.', 'danger')
        return redirect(url_for('main.transactions'))
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the transaction.', 'danger')
    
    return redirect(url_for('main.transactions'))

@main_bp.route('/reports')
@login_required
def reports():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Handle "All Months" case (month = 0)
    if month == 0:
        # Get yearly summary instead of monthly
        monthly_summary = {
            'income': 0,
            'expense': 0,
            'balance': 0,
            'transactions': 0
        }
        yearly_data = get_yearly_summary(current_user.id, year)
        for m in range(1, 13):
            monthly_summary['income'] += yearly_data[m]['income']
            monthly_summary['expense'] += yearly_data[m]['expense']
        monthly_summary['balance'] = monthly_summary['income'] - monthly_summary['expense']
        
        # Get category breakdown for entire year
        expense_breakdown = {}
        income_breakdown = {}
        for m in range(1, 13):
            exp_break = get_category_breakdown(current_user.id, year, m, 'expense')
            inc_break = get_category_breakdown(current_user.id, year, m, 'income')
            for cat, amount in exp_break.items():
                expense_breakdown[cat] = expense_breakdown.get(cat, 0) + amount
            for cat, amount in inc_break.items():
                income_breakdown[cat] = income_breakdown.get(cat, 0) + amount
    else:
        # Get monthly summary
        monthly_summary = get_monthly_summary(current_user.id, year, month)
        
        # Get category breakdown
        expense_breakdown = get_category_breakdown(current_user.id, year, month, 'expense')
        income_breakdown = get_category_breakdown(current_user.id, year, month, 'income')
    
    # Get yearly data for charts
    yearly_data = get_yearly_summary(current_user.id, year)
    
    # Format data for charts
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    income_data = [yearly_data[m]['income'] for m in range(1, 13)]
    expense_data = [yearly_data[m]['expense'] for m in range(1, 13)]
    
    # Convert breakdown dictionaries to lists for template
    expense_labels = list(expense_breakdown.keys()) if expense_breakdown else []
    expense_values = list(expense_breakdown.values()) if expense_breakdown else []
    
    return render_template('reports.html',
                         monthly_summary=monthly_summary,
                         expense_breakdown=expense_breakdown,
                         expense_labels=expense_labels,
                         expense_values=expense_values,
                         income_breakdown=income_breakdown,
                         months=months,
                         income_data=income_data,
                         expense_data=expense_data,
                         selected_year=year,
                         selected_month=month)

@main_bp.route('/prediction')
@login_required
def prediction():
    """Prediction page showing monthly expense predictions"""
    from prediction import prepare_training_data, predict_next_month_expense, get_expense_trend
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    import pandas as pd
    import numpy as np  # Ensure numpy is imported
    
    # Get next month prediction
    next_month_pred = predict_next_month_expense(current_user.id)
    
    # Get historical monthly data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=12 * 30)
    
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        type='expense'
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    # Group by month
    monthly_expenses = {}
    for transaction in transactions:
        month_key = f"{transaction.date.year}-{transaction.date.month:02d}"
        monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + transaction.amount
    
    # Get recent months data (last 6 months)
    recent_data = []
    recent_months_list = []
    recent_amounts_list = []
    sorted_keys = sorted(monthly_expenses.keys())
    
    for month_key in sorted_keys[-6:]:
        recent_data.append({
            'month': month_key,
            'amount': monthly_expenses[month_key]
        })
        recent_months_list.append(month_key)
        recent_amounts_list.append(monthly_expenses[month_key])
    
    # Prepare data for multi-month prediction
    X, y = prepare_training_data(current_user.id, 12)
    
    predictions_data = []
    if X is not None and len(X) >= 3:
        # Train models
        lr_model = LinearRegression()
        lr_model.fit(X, y)
        
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X, y)
        
        # Predict next 3 months
        current_month_num = X[-1][0] if len(X) > 0 else 0
        for i in range(1, 4):
            month_num = current_month_num + i
            lr_pred = lr_model.predict([[month_num]])[0]
            rf_pred = rf_model.predict([[month_num]])[0]
            avg_pred = (lr_pred + rf_pred) / 2
            
            now = datetime.now()
            future_date = now + timedelta(days=30 * i)
            month_name = future_date.strftime('%B %Y')
            
            predictions_data.append({
                'month': month_name,
                'prediction': round(float(avg_pred), 2),
                'lr_prediction': round(float(lr_pred), 2),
                'rf_prediction': round(float(rf_pred), 2)
            })
    
    # Get trend data for chart
    trend_labels, trend_values = get_expense_trend(current_user.id, 12)
    
    # FIX: Ensure chart data uses clean lists or numpy arrays
    chart_labels = [item['month'] for item in recent_data]
    
    # Use float() to ensure these are pure numbers, not complex objects
    chart_historical = [float(item['amount']) for item in recent_data]
    chart_predictions = []
    
    if predictions_data:
        for pred in predictions_data:
            chart_labels.append(pred['month'])
            chart_predictions.append(float(pred['prediction']))
    
    return render_template('prediction.html',
                         next_month_pred=next_month_pred,
                         recent_data=recent_data,
                         recent_months=recent_months_list,
                         recent_amounts=recent_amounts_list,
                         predictions_data=predictions_data,
                         chart_labels=chart_labels,
                         chart_historical=chart_historical,
                         chart_predictions=chart_predictions,
                         trend_labels=trend_labels,
                         trend_values=trend_values)

@main_bp.route('/export')
@login_required
def export():
    format_type = request.args.get('format', 'csv')
    
    # Get all user transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).all()
    
    # Prepare data
    data = []
    for t in transactions:
        data.append({
            'Date': t.date.strftime('%Y-%m-%d'),
            'Type': t.type.capitalize(),
            'Category': t.category.name,
            'Amount': t.amount,
            'Description': t.description or ''
        })
    
    df = pd.DataFrame(data)
    
    if format_type == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'finance_export_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    elif format_type == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'finance_export_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    flash('Invalid export format.', 'danger')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/backup')
@login_required
def backup():
    """Create a backup of user's transactions"""
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    backup_data = {
        'user_id': current_user.id,
        'username': current_user.username,
        'backup_date': datetime.now().isoformat(),
        'transactions': []
    }
    
    for t in transactions:
        backup_data['transactions'].append({
            'category': t.category.name,
            'type': t.type,
            'amount': float(t.amount),
            'description': t.description,
            'date': t.date.isoformat()
        })
    
    output = io.BytesIO()
    output.write(json.dumps(backup_data, indent=2).encode())
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'finance_backup_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.json'
    )

@main_bp.route('/restore', methods=['GET', 'POST'])
@login_required
def restore():
    """Restore transactions from backup file"""
    if request.method == 'GET':
        return render_template('restore.html')
    
    if 'backup_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('main.restore'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('main.restore'))
    
    try:
        backup_data = json.loads(file.read().decode('utf-8'))
        
        # Validate backup data
        if 'transactions' not in backup_data:
            flash('Invalid backup file format.', 'danger')
            return redirect(url_for('main.restore'))
        
        # Get category mapping
        categories = {cat.name: cat.id for cat in Category.query.all()}
        
        restored_count = 0
        for t_data in backup_data['transactions']:
            # Check if category exists
            if t_data['category'] not in categories:
                # Create category if it doesn't exist
                new_category = Category(name=t_data['category'])
                db.session.add(new_category)
                db.session.flush()
                categories[t_data['category']] = new_category.id
            
            # Check if transaction already exists (simple duplicate check)
            existing = Transaction.query.filter_by(
                user_id=current_user.id,
                category_id=categories[t_data['category']],
                type=t_data['type'],
                amount=t_data['amount'],
                date=datetime.fromisoformat(t_data['date']).date()
            ).first()
            
            if not existing:
                transaction = Transaction(
                    user_id=current_user.id,
                    category_id=categories[t_data['category']],
                    type=t_data['type'],
                    amount=t_data['amount'],
                    description=t_data.get('description', ''),
                    date=datetime.fromisoformat(t_data['date']).date()
                )
                db.session.add(transaction)
                restored_count += 1
        
        db.session.commit()
        flash(f'Successfully restored {restored_count} transactions from backup.', 'success')
        return redirect(url_for('main.transactions'))
        
    except json.JSONDecodeError:
        flash('Invalid JSON file format.', 'danger')
        return redirect(url_for('main.restore'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error restoring backup: {str(e)}', 'danger')
        return redirect(url_for('main.restore'))

@main_bp.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for chart data"""
    chart_type = request.args.get('type', 'monthly')
    
    if chart_type == 'monthly':
        now = datetime.now()
        breakdown = get_category_breakdown(current_user.id, now.year, now.month, 'expense')
        return jsonify({
            'labels': list(breakdown.keys()),
            'values': list(breakdown.values())
        })
    elif chart_type == 'trend':
        labels, values = get_expense_trend(current_user.id, 6)
        return jsonify({
            'labels': labels,
            'values': values
        })
    
    return jsonify({'error': 'Invalid chart type'}), 400

