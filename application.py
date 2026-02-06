from flask import Flask, render_template, request, redirect, url_for, session
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'prasannatha_secret_key'

# AWS DYNAMODB SETUP
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
user_table = dynamodb.Table('UserTable')
wishlist_table = dynamodb.Table('WishlistTable')

@app.route('/')
def home():
    return render_template('home.html', logged_in='email' in session)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email'].strip().lower()
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
        email = request.form['email'].strip().lower()
        password = request.form['password']
        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')
        
        if user and check_password_hash(user['hashed_password'], password):
            session['email'] = email
            print(f"DEBUG: User logged in as {email}")
            return redirect(url_for('user_dashboard'))
        else:
            return "Invalid Credentials. Please try again."
    return render_template('login.html')

@app.route('/user_dashboard')
def user_dashboard():
    if 'email' not in session: return redirect(url_for('login'))
    return render_template('user_dashboard.html')

@app.route('/virtual_exhibition')
def virtual_exhibition():
    if 'email' not in session: return redirect(url_for('login'))
    return render_template('virtual_exhibition.html')

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session: return redirect(url_for('login'))
    
    email = session['email']
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    
    print(f"DEBUG: Adding {item_name} to wishlist for {email}")
    
    wishlist_table.put_item(
        Item={
            'email': email,
            'item_id': item_id,
            'item_name': item_name,
            'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    return redirect(url_for('wishlist'))

@app.route('/wishlist')
def wishlist():
    if 'email' not in session: return redirect(url_for('login'))
    
    email = session['email']
    # Filter strictly by the logged-in user's email
    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(email)
    )
    items = response.get('Items', [])
    print(f"DEBUG: Found {len(items)} items in wishlist for {email}")
    return render_template('wishlist.html', wishlist=items)

# --- NEW FEATURE: REMOVE FROM WISHLIST ---
@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session: return redirect(url_for('login'))
    
    email = session['email']
    item_id = request.form.get('item_id')
    
    wishlist_table.delete_item(
        Key={
            'email': email,
            'item_id': item_id
        }
    )
    print(f"DEBUG: Removed {item_id} for {email}")
    return redirect(url_for('wishlist'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)