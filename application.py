from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Standard secret key for session management

# ---------------- AWS DYNAMODB SETUP ----------------
# Boto3 uses the IAM Role assigned to your EC2 instance automatically
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Define Table References - Ensure these names match your AWS Console exactly
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
            email = request.form['email'].strip().lower() # Standardize email input
            username = request.form['username']
            password = request.form['password']
            hashed_pw = generate_password_hash(password)

            # Store user in DynamoDB
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

        # Fetch user from DynamoDB
        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['hashed_password'], password):
            # IMPORTANT: Use 'email' consistently in the session
            session['email'] = user['email']
            session['username'] = user['username']
            
            # Update login count
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

# --- FIX: ADD TO WISHLIST ROUTE ---
@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Pulling data from the HTML form names
    current_user = session['email']
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    added_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Store item in DynamoDB
        wishlist_table.put_item(
            Item={
                'email': current_user,      # Partition Key (must match your Table setup)
                'item_id': item_id,         # Sort Key (must match your Table setup)
                'item_name': item_name,
                'added_date': added_date
            }
        )
        # Success: Go to the wishlist page immediately
        return redirect(url_for('wishlist'))
    except Exception as e:
        return f"Database Error: {str(e)}"

# --- FIX: WISHLIST VIEW ROUTE ---
@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Query items belonging to the current session email
    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    items = response.get('Items', [])
    
    return render_template('wishlist.html', wishlist=items)

@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    item_id = request.form.get('item_id')
    
    # Remove item from DynamoDB
    wishlist_table.delete_item(
        Key={
            'email': session['email'],
            'item_id': item_id
        }
    )
    return redirect(url_for('wishlist'))

if __name__ == '__main__':
    # host='0.0.0.0' allows access via EC2 Public IP
    app.run(host='0.0.0.0', port=80, debug=True)