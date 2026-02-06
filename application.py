from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------------- AWS DYNAMODB SETUP ----------------
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

user_table = dynamodb.Table('UserTable')
wishlist_table = dynamodb.Table('WishlistTable')

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    logged_in = 'email' in session
    return render_template('home.html', logged_in=logged_in)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            hashed_pw = generate_password_hash(password)

            user_table.put_item(
                Item={
                    'email': email,
                    'username': username,
                    'hashed_password': hashed_pw,
                    'login_count': 0
                }
            )
            return redirect(url_for('login'))
        except Exception as e:
            return f"Registration Error: {str(e)}"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['hashed_password'], password):
            session['email'] = user['email']  # Using 'email' consistently
            session['username'] = user['username']
            return redirect(url_for('user_dashboard'))
        else:
            return "Invalid Credentials."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')

@app.route('/virtual_exhibition')
def virtual_exhibition():
    return render_template('virtual_exhibition.html')

# --- UPDATED ADD TO WISHLIST (FIXES EMPTY WISHLIST) ---
@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email'] # Fixed to match login session key
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    added_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Save to DynamoDB
        wishlist_table.put_item(
            Item={
                'email': user_email,
                'item_id': item_id,
                'item_name': item_name,
                'added_date': added_date
            }
        )
        return redirect(url_for('wishlist'))
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Query items for the logged-in user
    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    items = response.get('Items', [])
    return render_template('wishlist.html', wishlist=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)