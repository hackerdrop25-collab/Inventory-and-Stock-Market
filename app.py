from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import csv
from io import StringIO
from market_utils import get_market_summary
from validators import (validate_email_address, validate_password, validate_product_input, 
                        validate_sale_input, validate_supplier_input, validate_return_input)
from gemini_ai import ai_assistant

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_inventory_key_change_this')

# MongoDB Connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'inventory_management_system')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validation
        if not username or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        is_valid_email, email_msg = validate_email_address(username)
        if not is_valid_email:
            flash('Invalid email format', 'error')
            return render_template('login.html')
        
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
            role = user.get('role', 'User')
            session['role'] = role
            
            log_entry['status'] = 'Success'
            firewall_logs.insert_one(log_entry)
            
            return redirect(url_for('dashboard'))
        else:
            log_entry['status'] = 'Failed'
            firewall_logs.insert_one(log_entry)
            flash('Incorrect Email or Password', 'error')
            
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'User')
        
        # Validate email
        is_valid_email, email_msg = validate_email_address(username)
        if not is_valid_email:
            flash(f'Invalid email: {email_msg}', 'error')
            return render_template('register.html')
        
        # Validate password
        is_valid_password, password_errors = validate_password(password)
        if not is_valid_password:
            for error in password_errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Check if user exists
        if users_collection.find_one({'username': username}):
            flash('Email already registered. Please login.', 'error')
            return render_template('register.html')
        
        # Prevent non-admin registrations as Admin
        if role == 'Admin' and username != ADMIN_EMAIL:
            role = 'User'
            flash('Only authorized email can register as Admin. Role set to User.', 'warning')
        
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
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', '')
        quantity = request.form.get('quantity', '')
        supplier = request.form.get('supplier', '').strip()
        
        # Validate input
        is_valid, errors = validate_product_input(name, category, price, quantity, supplier)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('products.html', products=products_collection.find(), 
                                   suppliers=suppliers_collection.find())
        
        products_collection.insert_one({
            'name': name,
            'category': category,
            'price': float(price),
            'quantity': int(quantity),
            'supplier': supplier,
            'added_by': session['user'],
            'added_at': datetime.now()
        })
        flash('Product added successfully', 'success')
        return redirect(url_for('products'))
        
    # Show all products
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    
    filter_query = {}
    if search_query:
        filter_query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'category': {'$regex': search_query, '$options': 'i'}},
            {'supplier': {'$regex': search_query, '$options': 'i'}}
        ]
    
    if category_filter:
        filter_query['category'] = category_filter
    
    products_list = products_collection.find(filter_query)
    suppliers_list = suppliers_collection.find()
    categories = [p['category'] for p in products_collection.find({}, {'category': 1})]
    categories = list(set(categories))  # Remove duplicates
    
    return render_template('products.html', products=products_list, suppliers=suppliers_list, 
                          categories=categories, search_query=search_query, category_filter=category_filter)


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
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', '')
    quantity = request.form.get('quantity', '')
    supplier = request.form.get('supplier', '').strip()
    
    # Validate input
    is_valid, errors = validate_product_input(name, category, price, quantity, supplier)
    if not is_valid:
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('products'))
    
    result = products_collection.update_one({'_id': ObjectId(id)}, {'$set': {
        'name': name,
        'category': category,
        'price': float(price),
        'quantity': int(quantity),
        'supplier': supplier
    }})
    
    if result.matched_count > 0:
        flash('Product updated successfully', 'success')
    else:
        flash('Product not found', 'error')
        
    return redirect(url_for('products'))


@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        quantity = request.form.get('quantity', '')
        customer_name = request.form.get('customer_name', 'Walk-in Customer').strip()
        
        # Validate input
        is_valid, errors = validate_sale_input(quantity, customer_name)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('sales'))
        
        if not product_id:
            flash('Please select a product', 'error')
            return redirect(url_for('sales'))
        
        quantity = int(quantity)
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
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
                flash(f'Insufficient stock! Available: {product["quantity"]}', 'error')
        else:
            flash('Product not found!', 'error')
        return redirect(url_for('sales'))

    # Advanced search for sales
    search_query = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    prod_filter = {}
    products_list = products_collection.find(prod_filter).sort('name', 1)
    
    sale_filter = {}
    if search_query:
        sale_filter['$or'] = [
            {'product_name': {'$regex': search_query, '$options': 'i'}},
            {'customer_name': {'$regex': search_query, '$options': 'i'}}
        ]
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            sale_filter.setdefault('date', {})['$gte'] = date_from_obj
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            sale_filter.setdefault('date', {})['$lte'] = date_to_obj
        except:
            pass
    
    recent_transactions = sales_collection.find(sale_filter).sort('date', -1).limit(10)
    return render_template('sales.html', products=products_list, transactions=recent_transactions,
                          search_query=search_query, date_from=date_from, date_to=date_to)


@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
@admin_required
def suppliers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validate input
        is_valid, errors = validate_supplier_input(name, contact, email, address)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('suppliers.html', suppliers=suppliers_collection.find())
        
        suppliers_collection.insert_one({
            'name': name,
            'contact': contact,
            'email': email,
            'address': address,
            'added_at': datetime.now()
        })
        flash('Supplier added successfully', 'success')
        return redirect(url_for('suppliers'))

    search_query = request.args.get('search', '').strip()
    filter_query = {}
    if search_query:
        filter_query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'contact': {'$regex': search_query, '$options': 'i'}},
            {'email': {'$regex': search_query, '$options': 'i'}}
        ]
    
    suppliers_list = suppliers_collection.find(filter_query)
    return render_template('suppliers.html', suppliers=suppliers_list, search_query=search_query)


@app.route('/returns', methods=['GET', 'POST'])
@login_required
@admin_required
def returns():
    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        quantity = request.form.get('quantity', '')
        reason = request.form.get('reason', '').strip()
        
        # Validate input
        is_valid, errors = validate_return_input(quantity, reason)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            products_list = products_collection.find().sort('name', 1)
            return render_template('returns.html', products=products_list, returns=returns_collection.find())
        
        if not product_id:
            flash('Please select a product', 'error')
            return redirect(url_for('returns'))
        
        quantity = int(quantity)
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if product:
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
    search_query = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '')
    
    prod_filter = {}
    products_list = products_collection.find(prod_filter).sort('name', 1)
    
    return_filter = {}
    if search_query:
        return_filter['$or'] = [
            {'product_name': {'$regex': search_query, '$options': 'i'}},
            {'reason': {'$regex': search_query, '$options': 'i'}}
        ]
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            return_filter['date'] = {'$gte': date_from_obj}
        except:
            pass
    
    recent_returns = returns_collection.find(return_filter).sort('date', -1)
    
    return render_template('returns.html', products=products_list, returns=recent_returns,
                          search_query=search_query, date_from=date_from)


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

# --- CSV Export Routes ---

@app.route('/export/products/csv')
@login_required
def export_products_csv():
    """Export products to CSV"""
    try:
        products_list = list(products_collection.find())
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Category', 'Price', 'Quantity', 'Supplier', 'Added By', 'Added At'])
        
        for product in products_list:
            writer.writerow([
                product.get('name', ''),
                product.get('category', ''),
                f"${product.get('price', 0):.2f}",
                product.get('quantity', 0),
                product.get('supplier', ''),
                product.get('added_by', ''),
                product.get('added_at', '').strftime('%Y-%m-%d %H:%M') if product.get('added_at') else ''
            ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash(f'Error exporting products: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/export/sales/csv')
@login_required
def export_sales_csv():
    """Export sales to CSV"""
    try:
        sales_list = list(sales_collection.find().sort('date', -1))
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Quantity', 'Price/Unit', 'Total Price', 'Customer', 'Date', 'Sold By'])
        
        for sale in sales_list:
            writer.writerow([
                sale.get('product_name', ''),
                sale.get('quantity', 0),
                f"${sale.get('price_per_unit', 0):.2f}",
                f"${sale.get('total_price', 0):.2f}",
                sale.get('customer_name', ''),
                sale.get('date', '').strftime('%Y-%m-%d %H:%M') if sale.get('date') else '',
                sale.get('sold_by', '')
            ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sales_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash(f'Error exporting sales: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/export/returns/csv')
@login_required
def export_returns_csv():
    """Export returns to CSV"""
    try:
        returns_list = list(returns_collection.find().sort('date', -1))
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Quantity', 'Reason', 'Supplier', 'Date', 'Processed By'])
        
        for ret in returns_list:
            writer.writerow([
                ret.get('product_name', ''),
                ret.get('quantity', 0),
                ret.get('reason', ''),
                ret.get('supplier_name', ''),
                ret.get('date', '').strftime('%Y-%m-%d %H:%M') if ret.get('date') else '',
                ret.get('processed_by', '')
            ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'returns_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash(f'Error exporting returns: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/export/low-stock/csv')
@login_required
def export_low_stock_csv():
    """Export low stock items to CSV"""
    try:
        low_stock = list(products_collection.find({'quantity': {'$lte': 5}}))
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Category', 'Current Stock', 'Price', 'Supplier', 'Alert Level'])
        
        for product in low_stock:
            alert_level = 'Critical' if product.get('quantity', 0) == 0 else 'Low'
            writer.writerow([
                product.get('name', ''),
                product.get('category', ''),
                product.get('quantity', 0),
                f"${product.get('price', 0):.2f}",
                product.get('supplier', ''),
                alert_level
            ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'low_stock_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash(f'Error exporting low stock: {str(e)}', 'error')
        return redirect(url_for('reports'))

# --- Analytics API Routes ---

@app.route('/api/analytics/dashboard')
@login_required
def api_analytics_dashboard():
    """Get dashboard analytics data"""
    try:
        # Total sales by category
        category_sales = list(sales_collection.aggregate([
            {'$lookup': {
                'from': 'products',
                'localField': 'product_id',
                'foreignField': '_id',
                'as': 'product'
            }},
            {'$unwind': '$product'},
            {'$group': {
                '_id': '$product.category',
                'total': {'$sum': '$total_price'},
                'units': {'$sum': '$quantity'}
            }},
            {'$sort': {'total': -1}}
        ]))
        
        # Top 5 products by sales
        top_products = list(sales_collection.aggregate([
            {'$group': {
                '_id': '$product_name',
                'units_sold': {'$sum': '$quantity'},
                'revenue': {'$sum': '$total_price'}
            }},
            {'$sort': {'revenue': -1}},
            {'$limit': 5}
        ]))
        
        # Monthly sales trend (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        monthly_trend = list(sales_collection.aggregate([
            {'$match': {'date': {'$gte': thirty_days_ago}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date'}},
                'total': {'$sum': '$total_price'}
            }},
            {'$sort': {'_id': 1}}
        ]))
        
        # Inventory overview
        inventory_stats = {
            'total_items': products_collection.count_documents({}),
            'in_stock': products_collection.count_documents({'quantity': {'$gt': 0}}),
            'low_stock': products_collection.count_documents({'quantity': {'$lte': 5, '$gt': 0}}),
            'out_of_stock': products_collection.count_documents({'quantity': 0})
        }
        
        return jsonify({
            'category_sales': category_sales,
            'top_products': top_products,
            'monthly_trend': monthly_trend,
            'inventory_stats': inventory_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- API Routes ---

@app.route('/api/summary')
@login_required
def api_summary():
    total_products = products_collection.count_documents({})
    low_stock = products_collection.count_documents({'quantity': {'$lte': 5}})
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales = sales_collection.aggregate([
        {'$match': {'date': {'$gte': today_start}}},
        {'$group': {'_id': None, 'total': {'$sum': '$total_price'}}}
    ])
    today_revenue = list(today_sales)[0]['total'] if today_sales else 0
    
    recent_sales = list(sales_collection.find().sort('date', -1).limit(5))
    for s in recent_sales:
        s['_id'] = str(s['_id'])
        s['product_id'] = str(s['product_id'])
        s['date'] = s['date'].strftime('%Y-%m-%d %H:%M')
        
    return jsonify({
        'total_products': total_products,
        'low_stock': low_stock,
        'today_revenue': today_revenue,
        'recent_sales': recent_sales
    })

@app.route('/api/products')
@login_required
def api_products():
    products_list = list(products_collection.find())
    for p in products_list:
        p['_id'] = str(p['_id'])
    
    suppliers_list = list(suppliers_collection.find())
    for s in suppliers_list:
        s['_id'] = str(s['_id'])
        
    return jsonify({'products': products_list, 'suppliers': suppliers_list})

@app.route('/api/sales')
@login_required
def api_sales():
    products_list = list(products_collection.find())
    for p in products_list:
        p['_id'] = str(p['_id'])
        
    transactions = list(sales_collection.find().sort('date', -1).limit(10))
    for t in transactions:
        t['_id'] = str(t['_id'])
        t['product_id'] = str(t['product_id'])
        t['date'] = t['date'].strftime('%Y-%m-%d %H:%M')
        
    return jsonify({'products': products_list, 'transactions': transactions})

@app.route('/api/suppliers')
@login_required
@admin_required
def api_suppliers():
    suppliers_list = list(suppliers_collection.find())
    for s in suppliers_list:
        s['_id'] = str(s['_id'])
    return jsonify({'suppliers': suppliers_list})

@app.route('/api/reports')
@login_required
def api_reports():
    # Similar logic to /reports but returning JSON
    prod_filter = {'quantity': {'$lte': 5}}
    if session.get('role') != 'Admin':
        prod_filter['added_by'] = session['user']
        
    low_stock = list(products_collection.find(prod_filter))
    for p in low_stock: p['_id'] = str(p['_id'])
    
    # Chart data
    seven_days_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
    chart_match = {'date': {'$gte': seven_days_ago}}
    if session.get('role') != 'Admin': chart_match['sold_by'] = session['user']
    
    daily_sales = list(sales_collection.aggregate([
        {'$match': chart_match},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date'}},
            'total': {'$sum': '$total_price'}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    return jsonify({
        'low_stock': low_stock,
        'chart_labels': [d['_id'] for d in daily_sales],
        'chart_data': [d['total'] for d in daily_sales]
    })

@app.route('/market')
@login_required
def market():
    return render_template('market.html')

@app.route('/api/market')
@login_required
def api_market_data():
    try:
        data = get_market_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/search')
@login_required
def api_market_search():
    symbol = request.args.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'No symbol provided'}), 400
    
    # Advanced security check for symbol
    if not symbol.replace('.','').replace('-','').isalnum() or len(symbol) > 10:
        return jsonify({'error': 'Invalid symbol format'}), 400
    
    # Import here to avoid circular dependency if any, or just ensure it's available
    from market_utils import get_stock_data
    
    data = get_stock_data(symbol)
    return jsonify(data)

@app.route('/api/market/watchlist', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_watchlist():
    user_query = {'username': session['user']}
    
    if request.method == 'GET':
        from market_utils import get_stock_data
        
        user = users_collection.find_one(user_query)
        watchlist = user.get('watchlist', [])
        
        # Always include major indices if watchlist is empty, or just return empty?
        # Let's return the user's list. Frontend can handle defaults.
        
        data = []
        for symbol in watchlist:
            stock_data = get_stock_data(symbol)
            if not stock_data.get('error'):
                data.append(stock_data)
                
        return jsonify(data)

    if request.method == 'POST':
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        
        if not symbol or not symbol.replace('.','').replace('-','').isalnum() or len(symbol) > 10:
             return jsonify({'error': 'Invalid symbol format'}), 400
        
        users_collection.update_one(
            user_query, 
            {'$addToSet': {'watchlist': symbol}}
        )
        return jsonify({'success': True, 'message': f'{symbol} added to watchlist'})

    if request.method == 'DELETE':
        symbol = request.args.get('symbol').upper()
        
        users_collection.update_one(
            user_query,
            {'$pull': {'watchlist': symbol}}
        )
        return jsonify({'success': True, 'message': f'{symbol} removed from watchlist'})

@app.route('/api/market/portfolio', methods=['GET'])
@login_required
def api_portfolio():
    user = users_collection.find_one({'username': session['user']})
    
    # Initialize wallet if not exists
    if 'wallet' not in user:
        users_collection.update_one(
            {'username': session['user']},
            {'$set': {'wallet': 10000.0, 'portfolio': [], 'transactions': []}}
        )
        return api_portfolio() # Retry once
        
    portfolio = user.get('portfolio', [])
    
    # Calculate current value
    from market_utils import get_stock_data
    
    total_value = 0
    updated_portfolio = []
    
    for item in portfolio:
        stock = get_stock_data(item['symbol'])
        if not stock.get('error'):
            current_price = stock['price']
            current_val = current_price * item['quantity']
            total_value += current_val
            
            # Add realtime data to item for frontend
            item['current_price'] = current_price
            item['current_value'] = current_val
            item['pl'] = current_val - (item['avg_price'] * item['quantity'])
            item['pl_percent'] = (item['pl'] / (item['avg_price'] * item['quantity'])) * 100 if item['avg_price'] else 0
            
        updated_portfolio.append(item)
        
    return jsonify({
        'wallet': user.get('wallet', 10000.0),
        'portfolio_value': total_value,
        'total_account_value': user.get('wallet', 10000.0) + total_value,
        'portfolio': updated_portfolio,
        'transactions': user.get('transactions', [])
    })

@app.route('/api/market/trade', methods=['POST'])
@login_required
def api_trade():
    """
    Handle Buy/Sell orders
    Payload: { symbol: 'AAPL', quantity: 10, type: 'BUY'|'SELL' }
    """
    data = request.get_json()
    symbol = data.get('symbol').upper()
    quantity = int(data.get('quantity', 0))
    trade_type = data.get('type').upper()
    
    if quantity <= 0:
        return jsonify({'error': 'Invalid quantity'}), 400
        
    # Get Real Price
    from market_utils import get_stock_data
    stock = get_stock_data(symbol)
    if stock.get('error'):
        return jsonify({'error': 'Failed to get stock price'}), 400
        
    price = stock['price']
    total_cost = price * quantity
    
    user = users_collection.find_one({'username': session['user']})
    wallet = user.get('wallet', 10000.0)
    portfolio = user.get('portfolio', [])
    
    if trade_type == 'BUY':
        if wallet < total_cost:
            return jsonify({'error': 'Insufficient funds'}), 400
            
        # Update Wallet
        new_wallet = wallet - total_cost
        
        # Update Portfolio
        existing_item = next((item for item in portfolio if item['symbol'] == symbol), None)
        if existing_item:
            # Avg Price Calculation
            old_qty = existing_item['quantity']
            old_avg = existing_item['avg_price']
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_avg) + total_cost) / new_qty
            
            existing_item['quantity'] = new_qty
            existing_item['avg_price'] = new_avg
        else:
            portfolio.append({
                'symbol': symbol,
                'quantity': quantity,
                'avg_price': price
            })
            
    elif trade_type == 'SELL':
        existing_item = next((item for item in portfolio if item['symbol'] == symbol), None)
        if not existing_item or existing_item['quantity'] < quantity:
            return jsonify({'error': 'Insufficient holdings'}), 400
            
        # Update Wallet
        new_wallet = wallet + total_cost
        
        # Update Portfolio
        existing_item['quantity'] -= quantity
        if existing_item['quantity'] == 0:
            portfolio.remove(existing_item)
            
    else:
        return jsonify({'error': 'Invalid trade type'}), 400
        
    # Record Transaction
    transaction = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'type': trade_type,
        'quantity': quantity,
        'price': price,
        'total': total_cost
    }
    
    users_collection.update_one(
        {'username': session['user']},
        {
            '$set': {'wallet': new_wallet, 'portfolio': portfolio},
            '$push': {'transactions': transaction}
        }
    )
    
    return jsonify({
        'success': True, 
        'message': f'Successfully {trade_type} {quantity} {symbol} @ ${price}',
        'new_balance': new_wallet,
        'portfolio': portfolio
    })

@app.route('/api/realtime-updates')
@login_required
def api_realtime_updates():
    """Unified API for real-time dashboard updates"""
    try:
        # 1. Statistics
        total_products = products_collection.count_documents({})
        low_stock = products_collection.count_documents({'quantity': {'$lte': 5}})
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sales = sales_collection.aggregate([
            {'$match': {'date': {'$gte': today_start}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total_price'}}}
        ])
        today_revenue = list(today_sales)[0]['total'] if today_sales else 0
        
        # 2. Market Highlight (S&P 500)
        from market_utils import get_stock_data
        market_highlight = get_stock_data('^GSPC')

        # 3. Recent Sales (last 3)
        recent_sales = list(sales_collection.find().sort('date', -1).limit(3))
        for s in recent_sales:
            s['_id'] = str(s['_id'])
            s['product_id'] = str(s['product_id'])
            s['date'] = s['date'].strftime('%H:%M:%S')

        return jsonify({
            'stats': {
                'total_products': total_products,
                'low_stock': low_stock,
                'today_revenue': today_revenue
            },
            'market': market_highlight,
            'recent_sales': recent_sales,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/market-insights')
@login_required
def api_ai_market_insights():
    from market_utils import get_market_summary
    data = get_market_summary()
    insights = ai_assistant.get_market_insights(data)
    return jsonify({'insights': insights})

@app.route('/api/ai/inventory-advice')
@login_required
def api_ai_inventory_advice():
    low_stock = list(products_collection.find({'quantity': {'$lte': 5}}))
    for p in low_stock: p['_id'] = str(p['_id'])
    
    # Top 5 products by revenue for trending items
    top_products = list(sales_collection.aggregate([
        {'$group': {
            '_id': '$product_name',
            'revenue': {'$sum': '$total_price'}
        }},
        {'$sort': {'revenue': -1}},
        {'$limit': 5}
    ]))
    
    advice = ai_assistant.get_inventory_advice(low_stock, top_products)
    return jsonify({'advice': advice})

@app.route('/api/market/news')
@login_required
def api_market_news():
    symbol = request.args.get('symbol', '').strip().upper()
    from news_service import news_service
    if symbol:
        news = news_service.get_symbol_news(symbol)
    else:
        news = news_service.get_market_news()
    return jsonify(news)

@app.route('/api/market/indicators')
@login_required
def api_market_indicators():
    symbol = request.args.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'No symbol provided'}), 400
    
    from market_utils import get_technical_indicators
    indicators = get_technical_indicators(symbol)
    if indicators:
        return jsonify(indicators)
    else:
        return jsonify({'error': 'Could not calculate indicators'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
