# tools to help connect to the database
from flask_sqlalchemy import SQLAlchemy
# tools to help manage user logins easily
from flask_login import UserMixin
# tools to hide and check passwords safely
from werkzeug.security import generate_password_hash, check_password_hash
# tools to handle dates and times
from datetime import datetime

# creates the database object to use in the app
db = SQLAlchemy()

# 1. user table setup
class User(UserMixin, db.Model):
    # gives the table a specific name in the database
    __tablename__ = 'users'
    
    # a unique number for every user
    id = db.Column(db.Integer, primary_key=True)
    # the name of the user, must be unique and not empty
    username = db.Column(db.String(80), unique=True, nullable=False)
    # the email of the user, must be unique and not empty
    email = db.Column(db.String(120), unique=True, nullable=False)
    # where we store the scrambled version of the password
    password_hash = db.Column(db.String(255), nullable=False)
    # the date the user joined, set automatically
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # connects this user to all their transactions
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # a function to turn a plain password into a hidden hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    # a function to check if the typed password matches the hidden hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # tells python how to show a user object in the terminal
    def __repr__(self):
        return f'<User {self.username}>'

# 2. category table setup
class Category(db.Model):
    # gives the table a specific name
    __tablename__ = 'categories'
    
    # unique number for the category
    id = db.Column(db.Integer, primary_key=True)
    # name of the category like food or bills
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # connects this category to all related transactions
    # transactions: the name of the link to find all spending for this user
# db.relationship: tells the app that users and transactions are connected
# 'Transaction': the name of the other table we are linking to
# backref='user': lets us type 'transaction.user' to find who spent the money
# lazy=True: tells the app to load data only when we actually need to see it
# cascade='all, delete-orphan': if a user is deleted, delete all their data too

    transactions = db.relationship('Transaction', backref='category', lazy=True)
    
    # tells python how to show the category name
    def __repr__(self):
        return f'<Category {self.name}>'

# 3. transaction table setup
class Transaction(db.Model):
    # gives the table a specific name
    __tablename__ = 'transactions'
    
    # unique number for every single transaction
    id = db.Column(db.Integer, primary_key=True)
    # links the transaction to a specific user id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # links the transaction to a specific category id
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    # says if it is money coming in or going out
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    # the amount of money spent or earned
    amount = db.Column(db.Float, nullable=False)
    # extra notes about the transaction
    description = db.Column(db.Text)
    # the date the spending happened
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    # the exact time the entry was made in the app
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # tells python how to show the transaction details
    def __repr__(self):
        return f'<Transaction {self.id} - {self.type} - {self.amount}>'