from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Transaction
from app import app, db
from datetime import datetime, timedelta

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
        return redirect(url_for('login'))
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(10).all()
    balance = sum(t.amount if t.type == 'income' else -t.amount for t in Transaction.query.filter_by(user_id=current_user.id).all())
    return render_template('dashboard.html', transactions=transactions, balance=balance)

# Add Transaction
@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        type = request.form['type']
        new_transaction = Transaction(user_id=current_user.id, amount=amount, category=category, date=date, type=type)
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully')
        return redirect(url_for('dashboard'))
    return render_template('add_transaction.html')

# View Transactions
@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    query = Transaction.query.filter_by(user_id=current_user.id)
    if request.method == 'POST':
        if 'search' in request.form:
            search_term = request.form['search']
            query = query.filter((Transaction.category.like(f'%{search_term}%')) | (Transaction.type.like(f'%{search_term}%')))
        if 'filter_date' in request.form:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            query = query.filter(Transaction.date.between(start_date, end_date))
    transactions = query.order_by(Transaction.date.desc()).all()
    return render_template('transactions.html', transactions=transactions)

# Update Transaction
@app.route('/update_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def update_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        flash('You do not have permission to edit this transaction')
        return redirect(url_for('transactions'))
    if request.method == 'POST':
        transaction.amount = float(request.form['amount'])
        transaction.category = request.form['category']
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        transaction.type = request.form['type']
        db.session.commit()
        flash('Transaction updated successfully')
        return redirect(url_for('transactions'))
    return render_template('update_transaction.html', transaction=transaction)

# Delete Transaction
@app.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        flash('You do not have permission to delete this transaction')
        return redirect(url_for('transactions'))
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('transactions'))

# Summary
@app.route('/summary')
@login_required
def summary():
    period = request.args.get('period', 'monthly')
    days = 7 if period == 'weekly' else 30
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    transactions = Transaction.query.filter_by(user_id=current_user.id).filter(Transaction.date >= start_date).all()
    income = sum(t.amount for t in transactions if t.type == 'income')
    expenses = sum(t.amount for t in transactions if t.type == 'expense')
    categories = {}
    for t in transactions:
        if t.type == 'expense':
            categories[t.category] = categories.get(t.category, 0) + t.amount
    return render_template('summary.html', income=income, expenses=expenses, categories=categories, period=period)
