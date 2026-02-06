from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong key for production

# ---------------- AWS DYNAMODB SETUP ----------------
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Define Table References
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
            session['email'] = user['email']
            session['username'] = user['username']
            
            user_table.update_item(
                Key={'email': email},
                UpdateExpression='SET login_count = login_count + :val',
                ExpressionAttributeValues={':val': 1}
            )
            return redirect(url_for('user_dashboard'))
        else:
            return "Invalid Credentials. Please try again."
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

# --- UPDATED ADD TO WISHLIST (FIXES 415 ERROR) ---
@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Use request.form to get data from the HTML form
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    added_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Store item in DynamoDB WishlistTable
        wishlist_table.put_item(
            Item={
                'email': session['email'],      # Partition Key
                'item_id': item_id,             # Sort Key
                'item_name': item_name,
                'added_date': added_date
            }
        )
        # Redirect directly to wishlist page after success
        return redirect(url_for('wishlist'))
    except Exception as e:
        return f"Error adding to wishlist: {str(e)}"

@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    items = response.get('Items', [])
    return render_template('wishlist.html', wishlist=items)

# --- UPDATED REMOVE FROM WISHLIST ---
@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Accept item_id from a standard form
    item_id = request.form.get('item_id')
    
    try:
        wishlist_table.delete_item(
            Key={
                'email': session['email'],
                'item_id': item_id
            }
        )
        return redirect(url_for('wishlist'))
    except Exception as e:
        return f"Error removing item: {str(e)}"

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'email' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        return redirect(url_for('user_dashboard'))
    return render_template('quiz.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)