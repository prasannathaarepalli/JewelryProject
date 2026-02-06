from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# AWS DYNAMODB SETUP
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
user_table = dynamodb.Table('UserTable')
wishlist_table = dynamodb.Table('WishlistTable')

@app.route('/')
def home():
    logged_in = 'email' in session
    return render_template('home.html', logged_in=logged_in)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower() # Standardize
        password = request.form['password']
        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')
        if user and check_password_hash(user['hashed_password'], password):
            session['email'] = user['email'] # Store standardized email
            return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # Get form data from the POST request
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    
    wishlist_table.put_item(
        Item={
            'email': session['email'], # Partition Key
            'item_id': item_id,        # Sort Key
            'item_name': item_name,
            'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    return redirect(url_for('wishlist'))

@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Query items belonging to current session
    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    items = response.get('Items', [])
    # Pass 'wishlist' to the template
    return render_template('wishlist.html', wishlist=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)