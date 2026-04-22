from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Transaction, Category, User
from datetime import datetime, timedelta
from utils import get_monthly_summary, get_category_breakdown, get_yearly_summary
from prediction import prepare_training_data, predict_next_month_expense, get_expense_trend
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import io, json

main_bp = Blueprint('main', __name__)

# --- HELPER LOGIC ---
def get_date_context():
    now = datetime.now()
    prev = now.replace(day=1) - timedelta(days=1)
    return now, prev

# --- NAVIGATION ---
@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard' if current_user.is_authenticated else 'auth.login'))
#dashboard page
@main_bp.route('/dashboard')
@login_required
def dashboard():
    from prediction import prepare_training_data, predict_next_month_expense, get_expense_trend
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor

    now = datetime.now()
    
    # 1. Handle Prediction Values (Fixed to prevent NoneType error)
    raw = predict_next_month_expense(current_user.id)
    is_dict = isinstance(raw, dict)
    
    # Safely get the value first
    if is_dict:
        raw_prediction = raw.get('prediction')
    else:
        raw_prediction = raw

    # Convert to float safely: if it's None or empty, default to 0.0
    try:
        if raw_prediction is None:
            clean_prediction = 0.0
        else:
            clean_prediction = float(raw_prediction)
    except (ValueError, TypeError):
        clean_prediction = 0.0

    p_val = {
        "prediction": round(clean_prediction, 2),
        "confidence": raw.get('confidence', 'Normal') if is_dict else "Normal"
    }
    # 2. Monthly Summaries
    curr_m = get_monthly_summary(current_user.id, now.year, now.month)
    prev_date = now.replace(day=1) - timedelta(days=1)
    prev_m = get_monthly_summary(current_user.id, prev_date.year, prev_date.month)
    
    # 3. Categories & Transactions
    cats = get_category_breakdown(current_user.id, now.year, now.month, 'expense') or {}
    recent = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(10).all()
    t_labels, t_values = get_expense_trend(current_user.id, 6)
    
    # 4. AI Model Training (Fixed NameError)
    X, y = prepare_training_data(current_user.id, 12)
    
    # Define data_count immediately after getting X
    data_count = len(X) if X is not None else 0
    lr_v, rf_v, final_p = 0, 0, 0
    
    if data_count >= 3:
        next_idx = [[X[-1][0] + 1]]
        lr_v = LinearRegression().fit(X, y).predict(next_idx)[0]
        rf_v = RandomForestRegressor(n_estimators=100).fit(X, y).predict(next_idx)[0]
        final_p = (lr_v + rf_v) / 2

    # 5. Build Prediction Data Dictionary
    p_data = {
        "prediction": round(float(final_p), 2), 
        "lr_prediction": round(float(lr_v), 2), 
        "rf_prediction": round(float(rf_v), 2),
        "confidence": "High" if data_count > 5 else ("Low" if data_count >= 3 else "No Data")
    }

    return render_template('dashboard.html', next_month_pred=p_val, prediction=p_data,
        current_month=curr_m, prev_month=prev_m, category_breakdown=cats,
        category_labels=list(cats.keys()), category_values=list(cats.values()),
        recent_transactions=recent, trend_labels=t_labels, trend_values=t_values)
# --- TRANSACTION CRUD ---
@main_bp.route('/transactions')
@login_required
def transactions():
    # 1. Get filter values from the URL
    t_type = request.args.get('type', 'all')
    cat_id = request.args.get('category', 'all')
    s_date = request.args.get('start_date', '')

    # 2. Start the query
    q = Transaction.query.filter_by(user_id=current_user.id)
    
    # 3. Apply filters
    if t_type != 'all': q = q.filter_by(type=t_type)
    if cat_id != 'all': q = q.filter_by(category_id=cat_id)
    if s_date: q = q.filter(Transaction.date >= s_date)
    
    return render_template('transactions.html', 
        transactions=q.order_by(Transaction.date.desc()).all(),
        categories=Category.query.all(),
        # This line fixes the error:
        current_filters={'type': t_type, 'category': cat_id, 'start_date': s_date})
#edit transaction
@main_bp.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    # Use the name 'transaction_id' to match your HTML link
    tx = Transaction.query.get_or_404(transaction_id)
    
    if tx.user_id != current_user.id:
        return redirect(url_for('main.transactions'))

    if request.method == 'POST':
        try:
            tx.amount = float(request.form['amount'])
            tx.type = request.form['type']
            tx.category_id = int(request.form['category_id'])
            tx.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            tx.description = request.form.get('description', '')
            
            db.session.commit()
            flash('Updated successfully!', 'success')
            return redirect(url_for('main.transactions'))
        except Exception:
            db.session.rollback()
            flash('Error updating transaction', 'danger')

    return render_template('edit_transaction.html', transaction=tx, categories=Category.query.all())
#delete transaction
@main_bp.route('/delete_transaction/<int:transaction_id>', methods=['POST', 'GET'])
@login_required
def delete_transaction(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    
    # Check if the transaction belongs to the current user
    if tx.user_id == current_user.id:
        try:
            db.session.delete(tx)
            db.session.commit()
            flash('Transaction deleted!', 'success')
        except Exception:
            db.session.rollback()
            flash('Error deleting transaction.', 'danger')
            
    return redirect(url_for('main.transactions'))
#add new trans
@main_bp.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        try:
            tx = Transaction(user_id=current_user.id, amount=float(request.form['amount']),
                             type=request.form['type'], category_id=int(request.form['category_id']),
                             date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                             description=request.form.get('description', ''))
            db.session.add(tx); db.session.commit()
            flash('Success!', 'success'); return redirect(url_for('main.transactions'))
        except: flash('Error adding transaction', 'danger')
    return render_template('add_transaction.html', categories=Category.query.all())


# --- REPORTS & ANALYTICS ---
@main_bp.route('/reports')
@login_required
def reports():
    # Get year/month from URL, default to current date
    y = request.args.get('year', datetime.now().year, type=int)
    m = request.args.get('month', datetime.now().month, type=int)
    
    # Get summaries for the charts and tables
    # If month is 0, logic in utils usually handles "Yearly View"
    monthly_summary = get_monthly_summary(current_user.id, y, m)
    expense_breakdown = get_category_breakdown(current_user.id, y, m, 'expense')
    income_breakdown = get_category_breakdown(current_user.id, y, m, 'income')
    
    # Get full year data for the bar chart trend
    yearly_data = get_yearly_summary(current_user.id, y)
    months_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    return render_template('reports.html',
        monthly_summary=monthly_summary,
        expense_breakdown=expense_breakdown,
        income_breakdown=income_breakdown,
        expense_labels=list(expense_breakdown.keys()),
        expense_values=list(expense_breakdown.values()),
        months=months_labels,
        income_data=[yearly_data[i]['income'] for i in range(1, 13)],
        expense_data=[yearly_data[i]['expense'] for i in range(1, 13)],
        selected_year=y,
        selected_month=m)
# --- PREDICTION & AI ---
@main_bp.route('/prediction')
@login_required
def prediction():
    from prediction import prepare_training_data, predict_next_month_expense, get_expense_trend
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor

    next_month_pred = predict_next_month_expense(current_user.id)
    
    # 1. Fetch & Group last 12 months of expenses
    start_date = datetime.now().date() - timedelta(days=360)
    txs = Transaction.query.filter_by(user_id=current_user.id, type='expense')\
        .filter(Transaction.date >= start_date).order_by(Transaction.date).all()
    
    monthly_expenses = {}
    for t in txs:
        k = t.date.strftime('%Y-%m')
        monthly_expenses[k] = monthly_expenses.get(k, 0) + t.amount
    
    # 2. Extract recent data (Last 6 months)
    keys = sorted(monthly_expenses.keys())[-6:]
    recent_data = [{'month': k, 'amount': monthly_expenses[k]} for k in keys]
    
    # 3. AI Training (Forecast next 3 months)
    X, y = prepare_training_data(current_user.id, 12)
    preds_data = []
    
    if X is not None and len(X) >= 3:
        lr, rf = LinearRegression().fit(X, y), RandomForestRegressor(n_estimators=100).fit(X, y)
        curr_idx = X[-1][0]
        for i in range(1, 4):
            m_idx = curr_idx + i
            p_lr, p_rf = lr.predict([[m_idx]])[0], rf.predict([[m_idx]])[0]
            f_month = (datetime.now() + timedelta(days=30 * i)).strftime('%B %Y')
            preds_data.append({
                'month': f_month, 'prediction': round((p_lr + p_rf) / 2, 2),
                'lr_prediction': round(p_lr, 2), 'rf_prediction': round(p_rf, 2)
            })

    # 4. Chart Data Preparation
    t_labels, t_vals = get_expense_trend(current_user.id, 12)
    c_labels = [d['month'] for d in recent_data] + [p['month'] for p in preds_data]
    c_hist = [float(d['amount']) for d in recent_data]
    c_preds = [p['prediction'] for p in preds_data]

    return render_template('prediction.html', next_month_pred=next_month_pred,
        recent_data=recent_data, recent_months=[d['month'] for d in recent_data],
        recent_amounts=[d['amount'] for d in recent_data], predictions_data=preds_data,
        chart_labels=c_labels, chart_historical=c_hist, chart_predictions=c_preds,
        trend_labels=t_labels, trend_values=t_vals)
# --- ADMIN & MANAGEMENT ---
@main_bp.route('/admin')
@login_required
def admin():
    return render_template('admin.html', users=User.query.all(), 
                           transactions=Transaction.query.all(), 
                           total_u=User.query.count(), total_t=Transaction.query.count())
@main_bp.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def del_user(user_id):
    # Security: Ensure only admins or the owner can delete
    if not current_user.is_admin and current_user.id != user_id:
        return redirect(url_for('main.dashboard'))

    try:
        # Delete user's transactions first to avoid database errors
        Transaction.query.filter_by(user_id=user_id).delete()
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            
        # If admin is deleting someone else, stay on admin page
        if current_user.is_admin and current_user.id != user_id:
            flash("User deleted successfully.", "success")
            return redirect(url_for('main.admin'))
            
        # If user deleted themselves, log out
        return redirect(url_for('auth.login'))
    except:
        db.session.rollback()
        return redirect(url_for('main.admin'))
@main_bp.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # Only allow access if the current user is an admin
    if current_user.is_admin:
        return redirect(url_for('main.edit_user.html'))
        
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.is_admin = 'is_admin' in request.form
        db.session.commit()
        flash(f"User {user.username} updated!", "success")
        return redirect(url_for('main.admin'))

    return render_template('edit_user.html', user=user)
@main_bp.route('/del_transaction/<int:t_id>', methods=['GET', 'POST'])
@login_required
def del_transaction(t_id):
    # 1. Fetch the transaction using the label 't_id'
    tx = Transaction.query.get_or_404(t_id)
    
    # 2. Security Check
    if tx.user_id == current_user.id:
        try:
            db.session.delete(tx)
            db.session.commit()
            flash('Transaction deleted!', 'success')
        except:
            db.session.rollback()
            
    return redirect(url_for('main.transactions'))
# --- DATA & EXPORT ---
@main_bp.route('/export')
@login_required
def export():
    txs = Transaction.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{'Date': t.date, 'Type': t.type, 'Amount': t.amount, 'Category': t.category.name} for t in txs])
    out = io.BytesIO()
    if request.args.get('format') == 'excel':
        df.to_excel(out, index=False)
        mtype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        out.write(df.to_csv(index=False).encode())
        mtype = 'text/csv'
    out.seek(0)
    return send_file(out, mimetype=mtype, as_attachment=True, download_name=f"export.{request.args.get('format', 'csv')}")

@main_bp.route('/backup')
@login_required
def backup():
    txs = Transaction.query.filter_by(user_id=current_user.id).all()
    data = {"user": current_user.username, "data": [{"amt": float(t.amount), "date": t.date.isoformat(), "type": t.type, "cat": t.category.name} for t in txs]}
    return send_file(io.BytesIO(json.dumps(data).encode()), as_attachment=True, download_name="backup.json")
# --- DATA MANAGEMENT (DOWNLOAD & RESTORE) ---
@main_bp.route('/download')
@login_required
def download():
    # Simply renders the page where the export buttons (CSV/Excel/JSON) are
    return render_template('download.html')

@main_bp.route('/restore', methods=['GET', 'POST'])
@login_required
def restore():
    if request.method == 'POST':
        file = request.files.get('backup_file')
        if not file:
            flash('No file selected', 'danger')
            return redirect(url_for('main.restore'))
        
        try:
            data = json.loads(file.read().decode('utf-8'))
            cats = {c.name: c.id for c in Category.query.all()}
            count = 0

            for t in data.get('transactions', []):
                # Only add if it doesn't already exist
                if not Transaction.query.filter_by(user_id=current_user.id, amount=t['amount'], date=datetime.fromisoformat(t['date']).date()).first():
                    new_tx = Transaction(
                        user_id=current_user.id,
                        category_id=cats.get(t['category'], 1), # Default to first category if missing
                        type=t['type'], amount=t['amount'],
                        description=t.get('description', ''),
                        date=datetime.fromisoformat(t['date']).date()
                    )
                    db.session.add(new_tx)
                    count += 1
            
            db.session.commit()
            flash(f'Restored {count} transactions!', 'success')
            return redirect(url_for('main.transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Restore failed: {str(e)}', 'danger')

    return render_template('download.html')