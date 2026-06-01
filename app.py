from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # 'Income' or 'Expense'
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Transaction {self.type}: {self.amount}>'

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    total_income = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.type == 'Income').scalar() or 0
    total_expense = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.type == 'Expense').scalar() or 0
    balance = total_income - total_expense
    
    # Data for Chart.js (Category-wise expenses)
    category_data = db.session.query(Transaction.category, db.func.sum(Transaction.amount))\
        .filter(Transaction.type == 'Expense')\
        .group_by(Transaction.category).all()
    
    labels = [row[0] for row in category_data]
    values = [row[1] for row in category_data]

    return render_template('index.html', 
                           transactions=transactions, 
                           total_income=total_income, 
                           total_expense=total_expense, 
                           balance=balance,
                           labels=labels,
                           values=values)

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        type = request.form.get('type')
        category = request.form.get('category')
        amount = float(request.form.get('amount'))
        date_str = request.form.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        description = request.form.get('description')

        new_transaction = Transaction(type=type, category=category, amount=amount, date=date, description=description)
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_transaction.html')

@app.route('/delete/<int:id>')
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted!', 'info')
    return redirect(url_for('index'))

@app.route('/reports')
def reports():
    # Monthly summary
    monthly_data = db.session.query(
        db.func.strftime('%Y-%m', Transaction.date).label('month'),
        db.func.sum(db.case((Transaction.type == 'Income', Transaction.amount), else_=0)).label('income'),
        db.func.sum(db.case((Transaction.type == 'Expense', Transaction.amount), else_=0)).label('expense')
    ).group_by('month').order_by('month').all()

    return render_template('reports.html', monthly_data=monthly_data)

if __name__ == '__main__':
    app.run(debug=True)
