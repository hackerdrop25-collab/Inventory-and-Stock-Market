from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "super_secret_inventory_key"

# MongoDB Connection
# Assuming local instance by default. User can change URI if needed.
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "inventory_management_system"

try:
    # Set timeout to 2 seconds to fail fast if no DB
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    # Check connection
    client.server_info()
    db = client[DB_NAME]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    print("Falling back to IN-MEMORY database (mongomock). Data will be lost on restart.")
    import mongomock
    client = mongomock.MongoClient()
    db = client[DB_NAME]

# Collections
users_collection = db['users']
products_collection = db['products']
sales_collection = db['sales']
suppliers_collection = db['suppliers']
returns_collection = db['returns']
firewall_logs = db['firewall_logs']


# Context Processor for User Info
@app.context_processor
def inject_user():
    return dict(current_user=session.get('user'), current_role=session.get('role'))

# Authentication Decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Admin Required Decorator
def admin_required(f):
    def wrap(*args, **kwargs):
        if session.get('role') != 'Admin':
            flash('Access Denied: Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# --- Routes ---

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        
        # Log entry
        log_entry = {
            'username': username,
            'ip_address': request.remote_addr,
            'timestamp': datetime.now(),
            'event_type': 'Login Attempt'
        }
        
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            
            # Auto-upgrade personal ID to Admin for security
            if username == 'hackerdrop25@gmail.com':
                role = 'Admin'
                if user.get('role') != 'Admin':
                    users_collection.update_one({'username': username}, {'$set': {'role': 'Admin'}})
            else:
                role = user.get('role', 'Student')
                
            session['role'] = role
            
            log_entry['status'] = 'Success'
            firewall_logs.insert_one(log_entry)
            
            return redirect(url_for('dashboard'))
        else:
            log_entry['status'] = 'Failed'
            firewall_logs.insert_one(log_entry)
            flash('Incorrect Email Id or Password', 'error')
            
    return render_template('login.html')

@app.route('/security-logs')
@login_required
@admin_required
def security_logs():
    logs = list(firewall_logs.find().sort('timestamp', -1).limit(100))
    return render_template('security_logs.html', logs=logs)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'Student') # Default to Student if not specified
        
        # Security: Only personal ID can register as Admin
        if role == 'Admin' and username != 'hackerdrop25@gmail.com':
            role = 'Student'
            flash('Security Restriction: Only personal ID can be Admin. Role set to Student.', 'warning')
        
        if users_collection.find_one({'username': username}):
            flash('Incorrect Email Id or Password', 'error')
        else:
            hashed_password = generate_password_hash(password)
            users_collection.insert_one({
                'username': username, 
                'password': hashed_password,
                'role': role,
                'created_at': datetime.now()
            })
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Filter based on role
    query_filter = {}
    # Statistics are global for now, or you can keep filters if you want personal stats.
    # Let's show global stats for Admin, and maybe global for Student too since they process everything.
    query_filter = {}

    # Gather Statistics
    total_products = products_collection.count_documents(query_filter)
    
    # Low Stock (combine filter with low stock condition)
    low_stock_filter = {'quantity': {'$lte': 5}}
    low_stock_products = products_collection.count_documents(low_stock_filter)
    
    # Calculate Total Sales (Today)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Sales Aggregation match stage
    match_stage = {'date': {'$gte': today_start}}
    match_stage = {'date': {'$gte': today_start}}
        
    today_sales = sales_collection.aggregate([
        {'$match': match_stage},
        {'$group': {'_id': None, 'total': {'$sum': '$total_price'}}}
    ])
    
    today_revenue = 0
    today_sales_list = list(today_sales)
    if today_sales_list:
        today_revenue = today_sales_list[0]['total']
        
    # Recent Sales
    sales_filter = {}
    sales_filter = {}
        
    recent_sales = sales_collection.find(sales_filter).sort('date', -1).limit(5)
    
    return render_template('dashboard.html', 
                           total_products=total_products,
                           low_stock=low_stock_products,
                           today_revenue=today_revenue,
                           recent_sales=recent_sales)

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    if request.method == 'POST':
        # Add Product
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        supplier = request.form['supplier']
        
        products_collection.insert_one({
            'name': name,
            'category': category,
            'price': price,
            'quantity': quantity,
            'supplier': supplier,
            'added_by': session['user'],  # Link product to user
            'added_at': datetime.now()
        })
        flash('Product added successfully', 'success')
        return redirect(url_for('products'))
        
    # Show all products for both Admin and Student
    filter_query = {}
        
    products_list = products_collection.find(filter_query)
    suppliers_list = suppliers_collection.find()
    return render_template('products.html', products=products_list, suppliers=suppliers_list)

@app.route('/products/delete/<id>')
@login_required
@admin_required
def delete_product(id):
    # Admin required decorator handles permission
    filter_query = {'_id': ObjectId(id)}

    result = products_collection.delete_one(filter_query)
    if result.deleted_count > 0:
        flash('Product deleted', 'success')
    else:
        flash('Permission denied or product not found', 'error')
    return redirect(url_for('products'))

@app.route('/products/update/<id>', methods=['POST'])
@login_required
@admin_required
def update_product(id):
    name = request.form['name']
    category = request.form['category']
    price = float(request.form['price'])
    quantity = int(request.form['quantity'])
    supplier = request.form['supplier']
    
    # Admin required decorator handles permission
    filter_query = {'_id': ObjectId(id)}
        
    result = products_collection.update_one(filter_query, {'$set': {
        'name': name,
        'category': category,
        'price': price,
        'quantity': quantity,
        'supplier': supplier
    }})
    
    if result.matched_count > 0:
        flash('Product updated', 'success')
    else:
        flash('Permission denied or product not found', 'error')
        
    return redirect(url_for('products'))

@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        customer_name = request.form.get('customer_name', 'Walk-in Customer')
        
        prod_filter = {'_id': ObjectId(product_id)}
            
        product = products_collection.find_one(prod_filter)
        
        if product:
            if product['quantity'] >= quantity:
                total_price = product['price'] * quantity
                
                # Deduct Stock
                products_collection.update_one({'_id': ObjectId(product_id)}, {'$inc': {'quantity': -quantity}})
                
                # Record Sale
                sales_collection.insert_one({
                    'product_name': product['name'],
                    'product_id': ObjectId(product_id),
                    'quantity': quantity,
                    'price_per_unit': product['price'],
                    'total_price': total_price,
                    'customer_name': customer_name,
                    'supplier_name': product.get('supplier', 'Unknown'),
                    'date': datetime.now(),
                    'sold_by': session['user']
                })
                flash(f'Sale successful! Total: ${total_price:.2f}', 'success')
            else:
                flash('Insufficient stock!', 'error')
        else:
            flash('Product not found or permission denied!', 'error')
        return redirect(url_for('sales'))

    # All users can see complete product list for sales dropdown
    prod_filter = {}
    products_list = products_collection.find(prod_filter)
    
    # Filter transactions based on role
    sale_filter = {}
    sale_filter = {}
        
    recent_transactions = sales_collection.find(sale_filter).sort('date', -1).limit(10)
    return render_template('sales.html', products=products_list, transactions=recent_transactions)

@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
@admin_required
def suppliers():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        
        suppliers_collection.insert_one({
            'name': name,
            'contact': contact,
            'email': email,
            'address': address
        })
        flash('Supplier added', 'success')
        return redirect(url_for('suppliers'))

    suppliers_list = suppliers_collection.find()
    return render_template('suppliers.html', suppliers=suppliers_list)

@app.route('/returns', methods=['GET', 'POST'])
@login_required
@admin_required
def returns():
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        reason = request.form['reason']
        
        prod_filter = {'_id': ObjectId(product_id)}
            
        product = products_collection.find_one(prod_filter)
        
        if product:
            # Record the return without removing from main stock
            returns_collection.insert_one({
                'product_name': product['name'],
                'product_id': ObjectId(product_id),
                'supplier_name': product.get('supplier', 'Unknown'),
                'quantity': quantity,
                'reason': reason,
                'date': datetime.now(),
                'processed_by': session['user']
            })
            flash('Return processed successfully', 'success')
        else:
            flash('Product not found!', 'error')
        return redirect(url_for('returns'))

    # Get all products for return selection
    prod_filter = {}
    products_list = products_collection.find(prod_filter)
    
    # Get returns list
    return_filter = {}
    recent_returns = returns_collection.find(return_filter).sort('date', -1)
    
    return render_template('returns.html', products=products_list, returns=recent_returns)

@app.route('/reports')
@login_required
def reports():
    # Filters based on role
    prod_filter = {'quantity': {'$lte': 5}}
    sale_filter = {}
    return_filter = {}
    
    if session.get('role') != 'Admin':
        prod_filter['added_by'] = session['user']
        sale_filter['sold_by'] = session['user']
        return_filter['processed_by'] = session['user']
        
    # Low Stock Report
    low_stock = list(products_collection.find(prod_filter))
    
    # Sales Report (Last 7 Days) - For Chart
    seven_days_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    seven_days_ago = seven_days_ago - timedelta(days=7)
    
    chart_match = {'date': {'$gte': seven_days_ago}}
    if session.get('role') != 'Admin':
        chart_match['sold_by'] = session['user']
        
    daily_sales = list(sales_collection.aggregate([
        {'$match': chart_match},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date'}},
            'total': {'$sum': '$total_price'}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    chart_labels = [d['_id'] for d in daily_sales]
    chart_data = [d['total'] for d in daily_sales]

    # Recent Sales List
    sales = list(sales_collection.find(sale_filter).sort('date', -1).limit(50))
    
    # Returns Report
    returns_list = list(returns_collection.find(return_filter).sort('date', -1))
    
    return render_template('reports.html', 
                           low_stock=low_stock, 
                           sales=sales,
                           returns=returns_list,
                           chart_labels=chart_labels,
                           chart_data=chart_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
