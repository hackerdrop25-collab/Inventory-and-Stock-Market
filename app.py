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
        
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['role'] = user.get('role', 'Student')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'Student') # Default to Student if not specified
        
        if users_collection.find_one({'username': username}):
            flash('Username already exists', 'error')
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
    if session.get('role') != 'Admin':
        query_filter['added_by'] = session['user']

    # Gather Statistics
    total_products = products_collection.count_documents(query_filter)
    
    # Low Stock (combine filter with low stock condition)
    low_stock_filter = {'quantity': {'$lte': 5}}
    low_stock_filter.update(query_filter)
    low_stock_products = products_collection.count_documents(low_stock_filter)
    
    # Calculate Total Sales (Today)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Sales Aggregation match stage
    match_stage = {'date': {'$gte': today_start}}
    if session.get('role') != 'Admin':
        match_stage['sold_by'] = session['user']
        
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
    if session.get('role') != 'Admin':
        sales_filter['sold_by'] = session['user']
        
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
        
    # Filter products based on role
    filter_query = {}
    if session.get('role') != 'Admin':
        filter_query['added_by'] = session['user']
        
    products_list = products_collection.find(filter_query)
    suppliers_list = suppliers_collection.find()
    return render_template('products.html', products=products_list, suppliers=suppliers_list)

@app.route('/products/delete/<id>')
@login_required
def delete_product(id):
    # Ensure user owns the product or is admin
    filter_query = {'_id': ObjectId(id)}
    if session.get('role') != 'Admin':
        filter_query['added_by'] = session['user']

    result = products_collection.delete_one(filter_query)
    if result.deleted_count > 0:
        flash('Product deleted', 'success')
    else:
        flash('Permission denied or product not found', 'error')
    return redirect(url_for('products'))

@app.route('/products/update/<id>', methods=['POST'])
@login_required
def update_product(id):
    name = request.form['name']
    category = request.form['category']
    price = float(request.form['price'])
    quantity = int(request.form['quantity'])
    supplier = request.form['supplier']
    
    # Ensure user owns the product or is admin
    filter_query = {'_id': ObjectId(id)}
    if session.get('role') != 'Admin':
        filter_query['added_by'] = session['user']
        
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
        
        # Determine product filter (checking ownership/admin implicit in logic?)
        # Strict check: Can only sell own products (unless Admin?)
        # Let's assume you can only sell what you can see.
        prod_filter = {'_id': ObjectId(product_id)}
        if session.get('role') != 'Admin':
            prod_filter['added_by'] = session['user']
            
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
                    'date': datetime.now(),
                    'sold_by': session['user']
                })
                flash(f'Sale successful! Total: ${total_price:.2f}', 'success')
            else:
                flash('Insufficient stock!', 'error')
        else:
            flash('Product not found or permission denied!', 'error')
        return redirect(url_for('sales'))

    # Helper filter for retrieving products to populate the dropdown
    prod_filter = {}
    if session.get('role') != 'Admin':
        prod_filter['added_by'] = session['user']
    products_list = products_collection.find(prod_filter)
    
    # Filter transactions based on role
    sale_filter = {}
    if session.get('role') != 'Admin':
        sale_filter['sold_by'] = session['user']
        
    recent_transactions = sales_collection.find(sale_filter).sort('date', -1).limit(10)
    return render_template('sales.html', products=products_list, transactions=recent_transactions)

@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
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

@app.route('/reports')
@login_required
def reports():
    # Filters based on role
    prod_filter = {'quantity': {'$lte': 5}}
    sale_filter = {}
    
    if session.get('role') != 'Admin':
        prod_filter['added_by'] = session['user']
        sale_filter['sold_by'] = session['user']
        
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
    
    return render_template('reports.html', 
                           low_stock=low_stock, 
                           sales=sales,
                           chart_labels=chart_labels,
                           chart_data=chart_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
