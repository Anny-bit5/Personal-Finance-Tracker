# Import tools to build the web app
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

# Create a 'Blueprint' to organize the main routes of the app
main_bp = Blueprint('main', __name__)

# The starting page (Home)
@main_bp.route('/')
def index():
    # If the user is already logged in, send them to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    # If not logged in then redirect them to login page
    return redirect(url_for('auth.login'))

# The main Dashboard page
@main_bp.route('/dashboard')
@login_required
def dashboard():
    from prediction import prepare_training_data
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    # Get current date
    now = datetime.now()
    
    # Get the dictionary from the prediction model
    raw_data = predict_next_month_expense(current_user.id)
     # Initialize the variable at the top!
    prediction_value = 0  

    # Extract the actual number from the dictionary
    if isinstance(raw_data, dict):
        actual_number = raw_data.get('prediction', 0)
        conf_level = raw_data.get('confidence', 'N/A')
    else:
        # If the model just returned a number directly
        actual_number = raw_data if raw_data else 0
        conf_level = "Normal"
        prediction_value = {
        "prediction": round(float(actual_number), 2),
        "confidence": conf_level
    }
    # --- Rest of  existing logic ---
    current_month = get_monthly_summary(current_user.id, now.year, now.month)
    
    if now.month == 1:
        prev_month = get_monthly_summary(current_user.id, now.year - 1, 12)
    else:
        prev_month = get_monthly_summary(current_user.id, now.year, now.month - 1)
    
    category_breakdown = get_category_breakdown(current_user.id, now.year, now.month, 'expense')
    category_labels = list(category_breakdown.keys()) if category_breakdown else []
    category_values = list(category_breakdown.values()) if category_breakdown else []
    
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
        .limit(10).all()
    
    trend_labels, trend_values = get_expense_trend(current_user.id, 6)
    # 1. Prepare data for the models
    X, y = prepare_training_data(current_user.id, 12)
    
    # Defaults value
    lr_val = 0
    rf_val = 0
    final_pred = 0



    if X is not None and len(X) >= 3:
        # 2. Train and get Linear Regression result
        lr_model = LinearRegression().fit(X, y)
        lr_val = lr_model.predict([[X[-1][0] + 1]])[0]

        # 3. Train and get Random Forest result
        rf_model = RandomForestRegressor(n_estimators=100).fit(X, y)
        rf_val = rf_model.predict([[X[-1][0] + 1]])[0]
        
        final_pred = (lr_val + rf_val) / 2

    # 4. Create the dictionary with the names our HTML is looking for
    prediction_data = {
        "prediction": final_pred,
        "lr_prediction": lr_val,
        "rf_prediction": rf_val,
       "confidence": "High" if (X is not None and len(X) > 5) else ("Low" if (X is not None and len(X) >= 3) else "No Data")
}

    return render_template('dashboard.html',
                           next_month_pred=prediction_value, 
                           # Now uses real AI data     
                           prediction=prediction_data,
                           current_month=current_month,
                           prev_month=prev_month,
                           category_breakdown=category_breakdown,
                           category_labels=category_labels,
                           category_values=category_values,
                           recent_transactions=recent_transactions,
                           trend_labels=trend_labels,
                           trend_values=trend_values,
                    
                           )
from flask import flash, redirect, url_for, current_app
from models import db, User, Transaction # Ensure db and models are imported

# Route to delete a user
@main_bp.route('/del_user/<int:user_id>')
def del_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User {user_to_delete.username} has been deleted.", "success")
    return redirect(url_for('main.admin'))

# Route to delete a single transaction
@main_bp.route('/del_transaction/<int:t_id>')
def del_transaction(t_id):
    t_to_delete = Transaction.query.get_or_404(t_id)
    db.session.delete(t_to_delete)
    db.session.commit()
    flash("Transaction deleted successfully.", "info")
    return redirect(url_for('main.admin'))
@main_bp.route('/admin')
def admin():
    from models import User, Transaction  # Add Transaction here
    # Security Check: Only allow if the user is an admin
    # Fetch data for the admin to see
    all_users = User.query.all()
    # Fetch all transactions to show in the table
    all_transactions = Transaction.query.all()
    total_users = len(all_users)

    total_t = Transaction.query.count()# Total records in system

    return render_template('admin.html', users=all_users,transactions=all_transactions, total_u=total_users, total_t=total_t)
@main_bp.route('/download')
@login_required
def download():
    return render_template('download.html')
# The page that lists all transactions with filters

@main_bp.route('/transactions')
@login_required
def transactions():
    # Look at the URL to see if the user clicked any filters (type, category, dates)
    transaction_type = request.args.get('type', 'all')
    category_id = request.args.get('category', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Start a basic search for the current user's transactions
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # If the user filtered by type (Income/Expense), add that to the search
    if transaction_type != 'all':
        query = query.filter_by(type=transaction_type)
    
    # If the user filtered by a specific category, add that to the search
    if category_id != 'all':
        query = query.filter_by(category_id=category_id)
    
    # If a start date was picked, only show things from that day onwards
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    
    # If an end date was picked, only show things before that day
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Finalize the search and sort by newest date first
    transactions_list = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()
    
    # Get all categories so the filter dropdown has choices
    categories = Category.query.order_by(Category.name).all()
    
    # Show the transactions page with the results and filters applied
    return render_template('transactions.html',
                           transactions=transactions_list,
                           categories=categories,
                           current_filters={
                               'type': transaction_type,
                               'category': category_id,
                               'start_date': start_date,
                               'end_date': end_date
                           })

# Page to add a new transaction
@main_bp.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # If the user clicked "Submit" (POST)
    if request.method == 'POST':
        # Get the info from the form
        category_id = request.form.get('category_id')
        transaction_type = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        date = request.form.get('date')
        
        # Check if any main field is empty
        if not category_id or not transaction_type or not amount or not date:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('main.add_transaction'))
        
        try:
            # Convert amount to a number
            amount = float(amount)
            # Make sure they didn't enter a negative number
            if amount <= 0:
                flash('Amount must be greater than 0.', 'danger')
                return redirect(url_for('main.add_transaction'))
            
            # Turn the date string into a real date object
            transaction_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Create a new Transaction object with the user's data
            transaction = Transaction(
                user_id=current_user.id,
                category_id=int(category_id),
                type=transaction_type,
                amount=amount,
                description=description,
                date=transaction_date
            )
            
            # Save the new transaction to the database
            db.session.add(transaction)
            db.session.commit()
            
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('main.transactions'))
            
        except ValueError:
            # Handle mistakes like typing letters in the amount box
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('main.add_transaction'))
        except Exception as e:
            # If something else goes wrong, cancel the database save
            db.session.rollback()
            flash('An error occurred while adding the transaction.', 'danger')
            return redirect(url_for('main.add_transaction'))
    
    # If they just opened the page (GET), show the blank form and categories
    categories = Category.query.order_by(Category.name).all()
    return render_template('add_transaction.html', categories=categories)

# Page to edit an existing transaction
@main_bp.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    # Find the specific transaction or show a 404 error if it doesn't exist
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Security: make sure this transaction actually belongs to the logged-in user
    if transaction.user_id != current_user.id:
        flash('You do not have permission to edit this transaction.', 'danger')
        return redirect(url_for('main.transactions'))
    
    # If the user saved changes (POST)
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        transaction_type = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        date = request.form.get('date')
        
        # Make sure nothing is blank
        if not category_id or not transaction_type or not amount or not date:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0.', 'danger')
                return redirect(url_for('main.edit_transaction', transaction_id=transaction_id))
            
            transaction_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Update the existing transaction with new info
            transaction.category_id = int(category_id)
            transaction.type = transaction_type
            transaction.amount = amount
            transaction.description = description
            transaction.date = transaction_date
            
            # Save the updates
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
    
    # If just viewing the edit page, show the form pre-filled with current data
    categories = Category.query.order_by(Category.name).all()
    return render_template('edit_transaction.html', transaction=transaction, categories=categories)

# Route to delete a transaction
@main_bp.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    # Find the transaction
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Make sure the user owns it
    if transaction.user_id != current_user.id:
        flash('You do not have permission to delete this transaction.', 'danger')
        return redirect(url_for('main.transactions'))
    
    try:
        # Remove it from the database
        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the transaction.', 'danger')
    
    # Go back to the list of transactions
    return redirect(url_for('main.transactions'))

# Page for detailed financial reports
@main_bp.route('/reports')
@login_required
def reports():
    # Get the year and month the user wants to see (defaults to today)
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # If month is 0, it means the user wants to see the whole year
    if month == 0:
        # Create a blank summary
        monthly_summary = {'income': 0, 'expense': 0, 'balance': 0, 'transactions': 0}
        # Get data for the whole year
        yearly_data = get_yearly_summary(current_user.id, year)
        # Add up all 12 months
        for m in range(1, 13):
            monthly_summary['income'] += yearly_data[m]['income']
            monthly_summary['expense'] += yearly_data[m]['expense']
        monthly_summary['balance'] = monthly_summary['income'] - monthly_summary['expense']
        
        # Calculate category spending for the entire year
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
        # Otherwise, just get data for one specific month
        monthly_summary = get_monthly_summary(current_user.id, year, month)
        expense_breakdown = get_category_breakdown(current_user.id, year, month, 'expense')
        income_breakdown = get_category_breakdown(current_user.id, year, month, 'income')
    
    # Get data for the bar charts showing the whole year's trend
    yearly_data = get_yearly_summary(current_user.id, year)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    income_data = [yearly_data[m]['income'] for m in range(1, 13)]
    expense_data = [yearly_data[m]['expense'] for m in range(1, 13)]
    
    # Prepare labels for the charts
    expense_labels = list(expense_breakdown.keys()) if expense_breakdown else []
    expense_values = list(expense_breakdown.values()) if expense_breakdown else []
    
    # Show the reports page with all the charts and numbers
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

# The Prediction page (AI features)
@main_bp.route('/prediction')
@login_required
def prediction():
    """Prediction page showing monthly expense predictions"""
    # Import special AI tools here
    from prediction import prepare_training_data, predict_next_month_expense, get_expense_trend
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    
    # Get the AI's best guess for next month
    next_month_pred = predict_next_month_expense(current_user.id)
    
    # Look back at the last year (360 days) of transactions
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=12 * 30)
    
    # Get all expenses in that timeframe
    transactions = Transaction.query.filter_by(user_id=current_user.id, type='expense')\
        .filter(Transaction.date >= start_date, Transaction.date <= end_date)\
        .order_by(Transaction.date).all()
    
    # Group the expenses by month (e.g., "2024-05": 500.00)
    monthly_expenses = {}
    for transaction in transactions:
        month_key = f"{transaction.date.year}-{transaction.date.month:02d}"
        monthly_expenses[month_key] = monthly_expenses.get(month_key, 0) + transaction.amount
    
    # Pick the last 6 months to show in a "recent" list
    recent_data = []
    recent_months_list = []
    recent_amounts_list = []
    sorted_keys = sorted(monthly_expenses.keys())
    
    for month_key in sorted_keys[-6:]:
        recent_data.append({'month': month_key, 'amount': monthly_expenses[month_key]})
        recent_months_list.append(month_key)
        recent_amounts_list.append(monthly_expenses[month_key])
    
    # Prepare the data to "teach" the AI
    X, y = prepare_training_data(current_user.id, 12)
    
    predictions_data = []
    # If we have enough data (at least 3 months), train the AI
    if X is not None and len(X) >= 3:
        # Linear Regression (looks for a straight-line trend)
        lr_model = LinearRegression()
        lr_model.fit(X, y)
        
        # Random Forest (looks for complex patterns)
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X, y)
        
        # Predict the next 3 months
        current_month_num = X[-1][0] if len(X) > 0 else 0
        for i in range(1, 4):
            month_num = current_month_num + i
            lr_pred = lr_model.predict([[month_num]])[0]
            rf_pred = rf_model.predict([[month_num]])[0]
            # Average the two models for a safer guess
            avg_pred = (lr_pred + rf_pred) / 2
            
            # Figure out the names of the future months
            now = datetime.now()
            future_date = now + timedelta(days=30 * i)
            month_name = future_date.strftime('%B %Y')
            
            predictions_data.append({
                'month': month_name,
                'prediction': round(float(avg_pred), 2),
                'lr_prediction': round(float(lr_pred), 2),
                'rf_prediction': round(float(rf_pred), 2)
            })
    
    # Get overall trend data for the chart
    trend_labels, trend_values = get_expense_trend(current_user.id, 12)
    
    # Format the labels and numbers specifically for the chart library
    chart_labels = [item['month'] for item in recent_data]
    chart_historical = [float(item['amount']) for item in recent_data]
    chart_predictions = []
    
    # Add predicted months to the chart data
    if predictions_data:
        for pred in predictions_data:
            chart_labels.append(pred['month'])
            chart_predictions.append(float(pred['prediction']))
    
    # Show the prediction page with all the AI results
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

# Route to download data as CSV or Excel
@main_bp.route('/export')
@login_required
def export():
    # Check if user wants 'csv' or 'excel'
    format_type = request.args.get('format', 'csv')
    
    # Get all of the user's transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).all()
    
    # Turn the database objects into a simple list of dictionaries
    data = []
    for t in transactions:
        data.append({
            'Date': t.date.strftime('%Y-%m-%d'),
            'Type': t.type.capitalize(),
            'Category': t.category.name,
            'Amount': t.amount,
            'Description': t.description or ''
        })
    
    # Use Pandas to create a data table
    df = pd.DataFrame(data)
    
    # If CSV format
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
    # If Excel format
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

# Route to create a JSON backup file
@main_bp.route('/backup')
@login_required
def backup():
    """Create a backup of user's transactions"""
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    # Create a dictionary with user info and all their transactions
    backup_data = {
        'user_id': current_user.id,
        'username': current_user.username,
        'backup_date': datetime.now().isoformat(),
        'transactions': []
    }
    
    # Add each transaction to the backup list
    for t in transactions:
        backup_data['transactions'].append({
            'category': t.category.name,
            'type': t.type,
            'amount': float(t.amount),
            'description': t.description,
            'date': t.date.isoformat()
        })
    
    # Create the JSON file in memory
    output = io.BytesIO()
    output.write(json.dumps(backup_data, indent=2).encode())
    output.seek(0)
    
    # Send the file to the user's browser for download
    return send_file(
        output,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'finance_backup_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.json'
    )

# Route to upload and restore data from a backup file
@main_bp.route('/restore', methods=['GET', 'POST'])
@login_required
def restore():
    """Restore transactions from backup file"""
    # If just visiting the page, show the upload form
    if request.method == 'GET':
        return render_template('restore.html')
    
    # If they uploaded a file
    if 'backup_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('main.restore'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('main.restore'))
    
    try:
        # Read the JSON file
        backup_data = json.loads(file.read().decode('utf-8'))
        
        # Check if it's a valid backup file
        if 'transactions' not in backup_data:
            flash('Invalid backup file format.', 'danger')
            return redirect(url_for('main.restore'))
        
        # Get a list of all existing categories to match IDs
        categories = {cat.name: cat.id for cat in Category.query.all()}
        
        restored_count = 0
        for t_data in backup_data['transactions']:
            # If a category in the backup doesn't exist in the database, create it
            if t_data['category'] not in categories:
                new_category = Category(name=t_data['category'])
                db.session.add(new_category)
                db.session.flush() # Get an ID for the new category immediately
                categories[t_data['category']] = new_category.id
            
            # Avoid adding the exact same transaction twice
            existing = Transaction.query.filter_by(
                user_id=current_user.id,
                category_id=categories[t_data['category']],
                type=t_data['type'],
                amount=t_data['amount'],
                date=datetime.fromisoformat(t_data['date']).date()
            ).first()
            
            # If it's a new transaction, add it to the list to be saved
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
        
        # Save everything to the database at once
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

# A special route that returns raw data for charts (used by JavaScript)
@main_bp.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for chart data"""
    chart_type = request.args.get('type', 'monthly')
    
    # If the chart needs monthly category info
    if chart_type == 'monthly':
        now = datetime.now()
        breakdown = get_category_breakdown(current_user.id, now.year, now.month, 'expense')
        return jsonify({
            'labels': list(breakdown.keys()),
            'values': list(breakdown.values())
        })
    # If the chart needs the 6-month trend line
    elif chart_type == 'trend':
        labels, values = get_expense_trend(current_user.id, 6)
        return jsonify({
            'labels': labels,
            'values': values
        })
    
    return jsonify({'error': 'Invalid chart type'}), 400

