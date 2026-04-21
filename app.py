from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# 1. setting up the app
app = Flask(__name__)

# this is a secret code to keep user sessions safe
app.config['SECRET_KEY'] = 'anny123'

# this tells the app where the database file is saved
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'

# this turns off extra tracking to save computer memory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. adding extra tools (extensions)
from models import db
db.init_app(app) # connects the database to the app

login_manager = LoginManager()
login_manager.init_app(app) # connects the login system to the app

# if someone is not logged in, send them back to the login page
login_manager.login_view = 'auth.login'
# the message shown if a user tries to enter without logging in
login_manager.login_message = 'please log in to access this page.'

# 3. loading database models and routes
from models import User, Transaction, Category

# blueprints help keep the code organized in different files
from auth import auth_bp
from routes import main_bp

app.register_blueprint(auth_bp) # starts the login/register pages
app.register_blueprint(main_bp) # starts the main dashboard pages

# this helper finds a user in the database by using their id number
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 4. creating tables and starting data
with app.app_context():
    # this creates the actual database tables
    db.create_all()
    
    # a list of basic categories for every user
    default_categories = [
        'food', 'transport', 'bills', 'shopping', 'entertainment',
        'healthcare', 'education', 'salary', 'freelance', 'investment', 'other'
    ]

    # this loop checks if the categories are already in the database
    for cat_name in default_categories:
        # if the category is missing, create it
        if not Category.query.filter_by(name=cat_name).first():
            category = Category(name=cat_name)
            db.session.add(category)
    
    # save all the new categories permanently 
    db.session.commit()
@app.route('/admin-portal')
def admin_portal():
    # Security Check: Only allow if the user is an admin
    # Fetch data for the admin to see
    all_users = User.query.all()
    total_users = len(all_users)
    total_expenses = Expense.query.count() # Total records in system

    return render_template('admin.html', users=all_users, total_u=total_users, total_e=total_expenses)
# 5. starting the app
if __name__ == '__main__':
    # runs the website on port 5001 so you can see it in your browser
    app.run(debug=True, host='0.0.0.0', port=5001)