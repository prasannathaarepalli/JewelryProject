from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong random key for production

# ---------------- AWS DYNAMODB SETUP ----------------
# NOTE: Ensure your EC2 instance has an IAM Role with 'AmazonDynamoDBFullAccess'
# We do not hardcode keys here; boto3 will automatically use the IAM Role credentials.
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

            # Store user in DynamoDB UserTable [cite: 349]
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

        # Fetch user from DynamoDB UserTable [cite: 369]
        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['hashed_password'], password):
            session['email'] = user['email']
            session['username'] = user['username']
            
            # Update login count (Optional feature from your doc)
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

# --- DYNAMIC EXHIBITION ROUTE ---
@app.route('/virtual_exhibition')
def virtual_exhibition():
    # Dynamic Product List (Frontend Display)
    products = [
        {'name': 'Temple Necklace', 'image': 'https://via.placeholder.com/250?text=Temple+Necklace', 'price': '₹1,50,000', 'details': '22K Gold, 140g'},
        {'name': 'Gold Bangles', 'image': 'https://via.placeholder.com/250?text=Gold+Bangles', 'price': '₹80,000', 'details': '22K Gold, 60g'},
        {'name': 'Antique Jhumkas', 'image': 'https://via.placeholder.com/250?text=Jhumkas', 'price': '₹45,000', 'details': '18K Gold, 35g'},
        {'name': 'Kasu Mala', 'image': 'https://via.placeholder.com/250?text=Kasu+Mala', 'price': '₹2,10,000', 'details': '24K Gold, 160g'},
        {'name': 'Diamond Vanki', 'image': 'https://via.placeholder.com/250?text=Vanki', 'price': '₹1,20,000', 'details': '18K Gold, Diamond'},
        {'name': 'Pearl Haram', 'image': 'https://via.placeholder.com/250?text=Pearl+Haram', 'price': '₹95,000', 'details': '22K Gold, Pearls'}
    ]
    return render_template('virtual_exhibition.html', products=products)

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})

    data = request.json
    added_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    # Store item in DynamoDB WishlistTable [cite: 402]
    # Note: We use 'item_name' as 'item_id' for simplicity in this logic
    wishlist_table.put_item(
        Item={
            'email': session['email'],          # Partition Key
            'item_id': data['item_name'],       # Sort Key
            'item_name': data['item_name'],
            'item_image': data['item_image'],
            'item_details': data.get('item_details', 'Exclusive Collection'),
            'added_date': added_date
        }
    )
    return jsonify({'success': True, 'message': 'Added to Wishlist'})

@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Query DynamoDB for all items belonging to this user [cite: 423]
    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    items = response.get('Items', [])
    
    return render_template('wishlist.html', wishlist=items)

@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return jsonify({'success': False})

    data = request.json
    # Remove item from DynamoDB [cite: 445]
    wishlist_table.delete_item(
        Key={
            'email': session['email'],
            'item_id': data['item_id'] # Ensure frontend sends the correct identifier
        }
    )
    return jsonify({'success': True})

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        # Logic: You can expand this to store score in DynamoDB if needed
        return redirect(url_for('user_dashboard'))
    return render_template('quiz.html')

@app.route('/order')
def order():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('order.html')

if __name__ == '__main__':
    # Configuration for EC2 Deployment [cite: 637]
    # host='0.0.0.0' allows external access
    # port=80 is the standard HTTP port
    app.run(host='0.0.0.0', port=80, debug=True)