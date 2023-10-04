from datetime import datetime  # Import the datetime module
import plotly.express as px
from pymongo import MongoClient
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import pandas as pd
import io
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '12345678' 

login_manager = LoginManager()
login_manager.init_app(app)

client = MongoClient('mongodb+srv://sreesara02:ma2002ma@cluster0.i9wh6iw.mongodb.net/?retryWrites=true&w=majority')
db = client['expense_tracker']
expense_collection = db['expenses']
users = db['users']

class User(UserMixin):
    def __init__(self, user_id = None):
        self.id = user_id

def is_valid_credentials(username, password):
    if users.find({"username.password": {"$exists": True}}):
        return True
    else:
        return False
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None 
    
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']

        existing_user = users.find_one({'username': new_username})

        if existing_user:
            error_message = 'Username already exists.'
        else:
            users.insert_one({'username': new_username, 'password': new_password})
            return render_template('login.html', error_message=error_message)


    return render_template('register.html', error_message=error_message)

@app.route('/delete_user', methods=['GET','POST'])
@login_required
def delete_user():
    users.delete_one({'username': current_user.id})
    expense_collection.delete_many({'user_id': current_user.id})
    logout_user()
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users.find_one({'username': username})

        if user and user['password'] == password:
            user_obj = User()
            user_obj.id = username
            login_user(user_obj)
            return redirect(url_for('add_expense'))
        else:
            flash('Incorrect username or password', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('login.html')


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        current_time = datetime.now()  # Get the current date and time

        # Add the expense with date and time information
        expense_collection.insert_one({'category': category, 'amount': amount, 'user_id': current_user.id, 'timestamp': current_time})

        return redirect(url_for('add_expense'))

    return render_template('add_expense.html')



@app.route('/clear_expenses')
@login_required
def clear_expenses():
    expense_collection.delete_many({'user_id': current_user.id})

    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    selected_month = request.args.get('month')

    # Filter expenses by month if a specific month is selected
    if selected_month and selected_month != 'all':
        user_expense_data = list(expense_collection.find({'user_id': current_user.id, '$expr': {'$eq': [{'$month': '$timestamp'}, int(selected_month)]}}))
    else:
        user_expense_data = list(expense_collection.find({'user_id': current_user.id}))


    categories = set(item['category'] for item in user_expense_data)
    category_expenses = {category: sum(item['amount'] for item in user_expense_data if item['category'] == category)
                         for category in categories}

    pie_chart = px.pie(names=list(category_expenses.keys()), values=list(category_expenses.values()))

    pie_chart_html = pie_chart.to_html(full_html=False)

    return render_template('dashboard.html', pie_chart=pie_chart_html, category_expenses=category_expenses, expense_data=user_expense_data)

@app.route('/export_expenses', methods=['GET'])
@login_required
def export_expenses():
    user_expense_data = list(expense_collection.find({'user_id': current_user.id}))
    df = pd.DataFrame(user_expense_data)
    excel_output = io.BytesIO()
    with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Expenses', index=False)
    excel_output.seek(0)

    response = make_response(excel_output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=expenses.xlsx'

    return response

def create_app():
    app.run(debug=True)

if __name__ == '__main__':
    create_app()
