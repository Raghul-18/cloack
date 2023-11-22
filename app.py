from flask import Flask, render_template, request, redirect, url_for, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash

import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 16 bytes to generate a 32-character hexadecimal string

# MongoDB Configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/UserDB'
mongo = PyMongo(app)

# User collection in MongoDB
users_collection = mongo.db.users


@app.route('/')
def index():
    # Redirect to the sign-up page
    return redirect(url_for('signup'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        if users_collection.find_one({'username': username}):
            flash('Username already exists. Choose a different one.', 'error')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password, method='sha256')

        # Insert user into the database
        users_collection.insert_one({'username': username, 'password': hashed_password})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Retrieve user from the database
        user = users_collection.find_one({'username': username})

        print(f"user: {user}")  # Print the user data to the console

        # Check if the user exists and the password is correct
        if user and check_password_hash(user['password'], password):
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            print("Login failed")  # Print a message to the console
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
