from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
from models import db
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Import models after db initialization
from models import User, Transaction, Category

# Import routes
from auth import auth_bp
from routes import main_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default categories if they don't exist
    default_categories = [
        'Food', 'Transport', 'Bills', 'Shopping', 'Entertainment',
        'Healthcare', 'Education', 'Salary', 'Freelance', 'Investment', 'Other'
    ]
    for cat_name in default_categories:
        if not Category.query.filter_by(name=cat_name).first():
            category = Category(name=cat_name)
            db.session.add(category)
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

