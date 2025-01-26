from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
from config import Config
from datetime import datetime, date
from functools import wraps
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import stripe
import secrets
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal

app = Flask(__name__)
app.config.from_object(Config)

# Initialize MySQL
mysql = MySQL(app)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
mail = Mail(app)

# Configure Stripe
stripe.api_key = 'sk_test_51QP4DXHb1M37dKMaTUOMrGippwaKQ7cj3adcrAhpbnMJV5nsCbK59SZy8kDy4kYLb1SdSK12UN3RVaMjgqPK4XmP00GTJLSTtw'

# Admin middleware
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT is_admin FROM users WHERE id = %s', [session['user_id']])
        user = cursor.fetchone()
        
        if not user or not user['is_admin']:
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    return render_template('products.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check if email already exists
        cursor.execute('SELECT * FROM users WHERE email = %s', [email])
        if cursor.fetchone():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)',
                      (name, email, hashed_password))
        mysql.connection.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        quantity = int(request.json.get('quantity', 1))
        if quantity < 1:
            return jsonify({'error': 'Invalid quantity'}), 400
        
        # Check if product exists and has enough stock
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM products WHERE id = %s', [product_id])
        product = cursor.fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        if product['stock'] < quantity:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = {}
        
        # Update cart quantity
        current_quantity = session['cart'].get(str(product_id), 0)
        new_quantity = current_quantity + quantity
        
        if new_quantity > product['stock']:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        session['cart'][str(product_id)] = new_quantity
        session.modified = True
        
        return jsonify({
            'message': 'Product added to cart',
            'cart_count': sum(session['cart'].values())
        })
        
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/add_to_wishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check if product exists
        cursor.execute('SELECT id FROM products WHERE id = %s', [product_id])
        if not cursor.fetchone():
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if already in wishlist
        cursor.execute('SELECT * FROM wishlist WHERE user_id = %s AND product_id = %s',
                      (session['user_id'], product_id))
        if cursor.fetchone():
            return jsonify({'message': 'Product already in wishlist'})
        
        # Add to wishlist
        cursor.execute('INSERT INTO wishlist (user_id, product_id) VALUES (%s, %s)',
                      (session['user_id'], product_id))
        mysql.connection.commit()
        
        return jsonify({'message': 'Product added to wishlist'})
        
    except Exception as e:
        print(f"Error adding to wishlist: {str(e)}")
        mysql.connection.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'user_id' not in session:
        flash('Please login to book an appointment', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        notes = request.form['notes']
        
        appointment_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO appointments (user_id, appointment_date, notes, status) VALUES (%s, %s, %s, %s)',
                      (session['user_id'], appointment_datetime, notes, 'pending'))
        mysql.connection.commit()
        
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('book_appointment.html')

@app.route('/search_products')
def search_products():
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', '')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    sql = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if query:
        sql += ' AND (name LIKE %s OR description LIKE %s)'
        params.extend([f'%{query}%', f'%{query}%'])
    
    if category:
        sql += ' AND category = %s'
        params.append(category)
    
    if sort == 'low-high':
        sql += ' ORDER BY price ASC'
    elif sort == 'high-low':
        sql += ' ORDER BY price DESC'
    
    cursor.execute(sql, params)
    products = cursor.fetchall()
    
    return jsonify(products)

@app.route('/cart')
def cart():
    if 'cart' not in session:
        session['cart'] = {}
    
    cart_items = []
    subtotal = 0
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    for product_id, quantity in session['cart'].items():
        cursor.execute('SELECT * FROM products WHERE id = %s', [product_id])
        product = cursor.fetchone()
        if product:
            # Ensure image_url doesn't include 'products/' prefix
            if product['image_url'] and product['image_url'].startswith('products/'):
                product['image_url'] = product['image_url'].replace('products/', '')
            item_total = product['price'] * quantity
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'image_url': product['image_url'],
                'total': item_total
            })
            subtotal += item_total
    
    # Calculate discount if user is logged in and is a member
    discount = 0
    if 'user_id' in session:
        try:
            cursor.execute('SELECT is_member FROM users WHERE id = %s', [session['user_id']])
            user = cursor.fetchone()
            if user and user.get('is_member'):
                discount = round(subtotal * 0.1)  # 10% member discount
        except Exception as e:
            print(f"Error checking member status: {str(e)}")
    
    # Calculate shipping and total
    shipping = 10000 if cart_items else 0  # Only add shipping if cart has items
    total = subtotal + shipping - discount
    
    return render_template('cart.html', 
                         cart_items=cart_items, 
                         subtotal=subtotal,
                         discount=discount,
                         shipping=shipping,
                         total=total)

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('products'))
    
    cart_items = []
    subtotal = 0
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch cart items
    for product_id, quantity in session['cart'].items():
        cursor.execute('''
            SELECT id, name, price, image_url 
            FROM products 
            WHERE id = %s
        ''', [product_id])
        
        product = cursor.fetchone()
        if product:
            # Ensure image_url doesn't include 'products/' prefix
            if product['image_url'] and product['image_url'].startswith('products/'):
                product['image_url'] = product['image_url'].replace('products/', '')
            item_total = product['price'] * quantity
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'image_url': product['image_url'],
                'total': item_total
            })
            subtotal += item_total
    
    # Calculate shipping and discounts
    shipping = 10000  # Fixed shipping cost
    discount = 0      # Initialize discount
    
    # Check if user is eligible for member discount
    try:
        cursor.execute('SELECT is_member FROM users WHERE id = %s', [session['user_id']])
        user = cursor.fetchone()
        if user and user.get('is_member'):
            discount = round(subtotal * 0.1)  # 10% member discount
    except Exception as e:
        print(f"Error checking member status: {str(e)}")
        discount = 0
    
    # Calculate total
    total = subtotal + shipping - discount
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         discount=discount,
                         total=total)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get user information
    cursor.execute('SELECT * FROM users WHERE id = %s', [session['user_id']])
    user = cursor.fetchone()
    
    # Get orders
    cursor.execute('''
        SELECT o.*, 
               CASE 
                   WHEN o.status = 'pending' THEN 'warning'
                   WHEN o.status = 'completed' THEN 'success'
                   WHEN o.status = 'cancelled' THEN 'danger'
                   ELSE 'primary'
               END as status_color
        FROM orders o 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    ''', [session['user_id']])
    orders = cursor.fetchall()
    
    # Get order items
    for order in orders:
        cursor.execute('''
            SELECT oi.*, p.name 
            FROM order_items oi 
            JOIN products p ON oi.product_id = p.id 
            WHERE order_id = %s
        ''', [order['id']])
        order['items'] = cursor.fetchall()
    
    # Get appointments
    cursor.execute('''
        SELECT *, 
               CASE 
                   WHEN status = 'pending' THEN 'warning'
                   WHEN status = 'confirmed' THEN 'success'
                   WHEN status = 'cancelled' THEN 'danger'
                   ELSE 'primary'
               END as status_color
        FROM appointments 
        WHERE user_id = %s 
        ORDER BY appointment_date DESC
    ''', [session['user_id']])
    appointments = cursor.fetchall()
    
    # Get wishlist items
    cursor.execute('''
        SELECT p.* 
        FROM wishlist w 
        JOIN products p ON w.product_id = p.id 
        WHERE w.user_id = %s
    ''', [session['user_id']])
    wishlist_items = cursor.fetchall()
    
    return render_template('dashboard.html',
                         user=user,
                         orders=orders,
                         appointments=appointments,
                         wishlist_items=wishlist_items)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        UPDATE users 
        SET name = %s, email = %s, phone = %s 
        WHERE id = %s
    ''', (name, email, phone, session['user_id']))
    mysql.connection.commit()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT password FROM users WHERE id = %s', [session['user_id']])
    user = cursor.fetchone()
    
    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('dashboard'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('dashboard'))
    
    hashed_password = generate_password_hash(new_password)
    cursor.execute('UPDATE users SET password = %s WHERE id = %s',
                  (hashed_password, session['user_id']))
    mysql.connection.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        UPDATE appointments 
        SET status = 'cancelled' 
        WHERE id = %s AND user_id = %s
    ''', (appointment_id, session['user_id']))
    mysql.connection.commit()
    
    return jsonify({'message': 'Appointment cancelled successfully'})

@app.route('/admin')
@admin_required
def admin_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get statistics
    today = date.today()
    
    # Orders statistics
    cursor.execute('SELECT COUNT(*) as total FROM orders')
    total_orders = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as today FROM orders WHERE DATE(created_at) = %s', [today])
    orders_today = cursor.fetchone()['today']
    
    # Revenue statistics
    cursor.execute('SELECT SUM(total_amount) as total FROM orders WHERE status = "completed"')
    total_revenue = cursor.fetchone()['total'] or 0
    
    cursor.execute('''
        SELECT SUM(total_amount) as today 
        FROM orders 
        WHERE status = "completed" AND DATE(created_at) = %s
    ''', [today])
    revenue_today = cursor.fetchone()['today'] or 0
    
    # User statistics
    cursor.execute('SELECT COUNT(*) as total FROM users')
    total_users = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as today FROM users WHERE DATE(created_at) = %s', [today])
    new_users_today = cursor.fetchone()['today']
    
    # Appointment statistics
    cursor.execute('SELECT COUNT(*) as total FROM appointments')
    total_appointments = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as today FROM appointments WHERE DATE(appointment_date) = %s', [today])
    appointments_today = cursor.fetchone()['today']
    
    stats = {
        'total_orders': total_orders,
        'orders_today': orders_today,
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'total_users': total_users,
        'new_users_today': new_users_today,
        'total_appointments': total_appointments,
        'appointments_today': appointments_today
    }
    
    # Get recent orders
    cursor.execute('''
        SELECT o.*, u.name as customer_name,
               CASE 
                   WHEN o.status = 'pending' THEN 'warning'
                   WHEN o.status = 'completed' THEN 'success'
                   WHEN o.status = 'cancelled' THEN 'danger'
                   ELSE 'primary'
               END as status_color
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 5
    ''')
    recent_orders = cursor.fetchall()
    
    # Get today's appointments
    cursor.execute('''
        SELECT a.*, u.name as customer_name,
               CASE 
                   WHEN a.status = 'pending' THEN 'warning'
                   WHEN a.status = 'confirmed' THEN 'success'
                   WHEN a.status = 'cancelled' THEN 'danger'
                   ELSE 'primary'
               END as status_color
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        WHERE DATE(appointment_date) = %s
        ORDER BY appointment_date ASC
    ''', [today])
    todays_appointments = cursor.fetchall()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_orders=recent_orders,
                         todays_appointments=todays_appointments)

@app.route('/admin/products')
@admin_required
def admin_products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products ORDER BY id DESC')
    products = cursor.fetchall()
    return render_template('admin/products.html', products=products)

@app.route('/admin/product', methods=['POST'])
@admin_required
def add_product():
    if 'image' not in request.files:
        flash('No image file', 'error')
        return redirect(url_for('admin_products'))
    
    file = request.files['image']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('admin_products'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, category, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            request.form['name'],
            request.form['description'],
            request.form['price'],
            request.form['category'],
            request.form['stock'],
            filename
        ))
        mysql.connection.commit()
        
        flash('Product added successfully', 'success')
        return redirect(url_for('admin_products'))
    
    flash('Invalid file type', 'error')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
@admin_required
def manage_product(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'GET':
        cursor.execute('SELECT * FROM products WHERE id = %s', [product_id])
        product = cursor.fetchone()
        return jsonify(product)
    
    elif request.method == 'PUT':
        data = request.get_json()
        cursor.execute('''
            UPDATE products 
            SET name = %s, description = %s, price = %s, category = %s, stock = %s
            WHERE id = %s
        ''', (
            data['name'],
            data['description'],
            data['price'],
            data['category'],
            data['stock'],
            product_id
        ))
        mysql.connection.commit()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        cursor.execute('DELETE FROM products WHERE id = %s', [product_id])
        mysql.connection.commit()
        return jsonify({'success': True})

@app.route('/admin/orders')
@admin_required
def admin_orders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get filter parameters
    status = request.args.get('status')
    date = request.args.get('date')
    search = request.args.get('search')
    
    query = '''
        SELECT o.*, u.name as customer_name,
               CASE 
                   WHEN o.status = 'pending' THEN 'warning'
                   WHEN o.status = 'processing' THEN 'info'
                   WHEN o.status = 'shipped' THEN 'primary'
                   WHEN o.status = 'delivered' THEN 'success'
                   WHEN o.status = 'cancelled' THEN 'danger'
               END as status_color
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if status:
        query += ' AND o.status = %s'
        params.append(status)
    
    if date:
        query += ' AND DATE(o.created_at) = %s'
        params.append(date)
    
    if search:
        query += ' AND (o.id LIKE %s OR u.name LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += ' ORDER BY o.created_at DESC'
    
    cursor.execute(query, params)
    orders = cursor.fetchall()
    
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@admin_required
def get_order_details(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get order details
    cursor.execute('''
        SELECT o.*, u.name as customer_name, u.email as customer_email,
               u.phone as customer_phone
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s
    ''', [order_id])
    order = cursor.fetchone()
    
    # Get order items
    cursor.execute('''
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    ''', [order_id])
    order['items'] = cursor.fetchall()
    
    return jsonify(order)

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    note = data.get('note')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Update order status
    cursor.execute('''
        UPDATE orders 
        SET status = %s, updated_at = NOW()
        WHERE id = %s
    ''', (new_status, order_id))
    
    # Add status history
    cursor.execute('''
        INSERT INTO order_status_history (order_id, status, note)
        VALUES (%s, %s, %s)
    ''', (order_id, new_status, note))
    
    mysql.connection.commit()
    
    # Get order details for email notification
    cursor.execute('''
        SELECT o.*, u.email, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s
    ''', [order_id])
    order = cursor.fetchone()
    
    # Send email notification
    send_order_status_email(order, new_status)
    
    return jsonify({'success': True})

def send_order_status_email(order, status):
    subject = f'Order #{order["id"]} Status Update'
    
    status_messages = {
        'processing': 'Your order is being processed',
        'shipped': 'Your order has been shipped',
        'delivered': 'Your order has been delivered',
        'cancelled': 'Your order has been cancelled'
    }
    
    body = f'''
    Dear {order['customer_name']},

    {status_messages.get(status, 'Your order status has been updated')}

    Order Details:
    Order ID: #{order['id']}
    Total Amount: ${order['total_amount']:.2f}
    New Status: {status.title()}

    You can track your order at: {url_for('order_tracking', order_id=order['id'], _external=True)}

    Thank you for shopping with us!

    Best regards,
    The Serene Interior Design Co.
    '''
    
    msg = Message(subject,
                 sender=app.config['MAIL_USERNAME'],
                 recipients=[order['email']])
    msg.body = body
    mail.send(msg)

# API Routes
@app.route('/api/products', methods=['GET'])
def api_products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort')
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = %s'
        params.append(category)
    
    if search:
        query += ' AND (name LIKE %s OR description LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if sort == 'price_asc':
        query += ' ORDER BY price ASC'
    elif sort == 'price_desc':
        query += ' ORDER BY price DESC'
    elif sort == 'newest':
        query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    return jsonify(products)

@app.route('/api/product/<int:product_id>', methods=['GET'])
def api_product_detail(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products WHERE id = %s', [product_id])
    product = cursor.fetchone()
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(product)

@app.route('/api/cart', methods=['GET', 'PUT', 'DELETE'])
def api_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    if request.method == 'GET':
        if 'cart' not in session:
            return jsonify([])
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cart_items = []
        
        for product_id, quantity in session['cart'].items():
            cursor.execute('SELECT * FROM products WHERE id = %s', [product_id])
            product = cursor.fetchone()
            if product:
                product['quantity'] = quantity
                cart_items.append(product)
        
        return jsonify(cart_items)
    
    elif request.method == 'PUT':
        data = request.get_json()
        product_id = str(data.get('product_id'))
        quantity = int(data.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            return jsonify({'error': 'Invalid quantity'}), 400
        
        # Check product stock
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT stock FROM products WHERE id = %s', [product_id])
        product = cursor.fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        if quantity > product['stock']:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        # Update cart
        if 'cart' not in session:
            session['cart'] = {}
        
        session['cart'][product_id] = quantity
        session.modified = True
        
        # Calculate new totals
        subtotal = Decimal('0.00')
        for pid, qty in session['cart'].items():
            cursor.execute('SELECT price FROM products WHERE id = %s', [pid])
            price = cursor.fetchone()['price']
            subtotal += price * Decimal(str(qty))
        
        discount = subtotal * Decimal('0.1')
        total = subtotal - discount
        
        return jsonify({
            'message': 'Cart updated',
            'quantity': quantity,
            'subtotal': float(subtotal),
            'discount': float(discount),
            'total': float(total)
        })
    
    elif request.method == 'DELETE':
        data = request.get_json()
        product_id = str(data.get('product_id'))
        
        if 'cart' in session and product_id in session['cart']:
            del session['cart'][product_id]
            session.modified = True
            
            # Calculate new totals
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            subtotal = Decimal('0.00')
            for pid, qty in session['cart'].items():
                cursor.execute('SELECT price FROM products WHERE id = %s', [pid])
                price = cursor.fetchone()['price']
                subtotal += price * Decimal(str(qty))
            
            discount = subtotal * Decimal('0.1')
            total = subtotal - discount
            
            return jsonify({
                'message': 'Product removed from cart',
                'subtotal': float(subtotal),
                'discount': float(discount),
                'total': float(total)
            })
        
        return jsonify({'error': 'Product not found in cart'}), 404

@app.route('/api/create-payment-intent', methods=['POST'])
def create_payment_intent():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    try:
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        cart_items = data.get('cart_items', [])
        if not cart_items:
            print("No cart items found")
            return jsonify({'error': 'Cart is empty'}), 400
        
        print(f"Received cart items: {cart_items}")  # Debug log
        
        # Calculate total amount in UGX
        total_amount_ugx = 0
        for item in cart_items:
            try:
                price = float(item.get('price', 0))
                quantity = int(item.get('quantity', 0))
                print(f"Processing item - Price UGX: {price}, Quantity: {quantity}")
                total_amount_ugx += price * quantity
            except (ValueError, TypeError) as e:
                print(f"Error processing item {item}: {str(e)}")
                return jsonify({'error': f'Invalid price or quantity in cart item'}), 400
        
        print(f"Total amount UGX before discount: {total_amount_ugx}")
        
        # Apply discount for registered users
        if 'user_id' in session:
            total_amount_ugx = total_amount_ugx * 0.9  # 10% discount
            print(f"Total amount UGX after discount: {total_amount_ugx}")
        
        # Convert UGX to USD (using approximate exchange rate: 1 USD = 3800 UGX)
        EXCHANGE_RATE_UGX_TO_USD = 3800
        total_amount_usd = total_amount_ugx / EXCHANGE_RATE_UGX_TO_USD
        print(f"Total amount in USD: {total_amount_usd}")
        
        # Validate USD amount
        if total_amount_usd <= 0:
            print(f"Invalid amount USD: {total_amount_usd}")
            return jsonify({'error': 'Invalid amount'}), 400
        if total_amount_usd > 999999.99:
            print(f"Amount exceeds limit USD: {total_amount_usd}")
            return jsonify({'error': 'Amount exceeds maximum limit'}), 400
        
        # Convert to cents for Stripe
        stripe_amount = int(round(total_amount_usd * 100))
        print(f"Stripe amount in cents: {stripe_amount}")
        
        # Create PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=stripe_amount,
            currency='usd',
            metadata={
                'user_id': str(session['user_id']),
                'amount_ugx': str(total_amount_ugx)  # Store original UGX amount in metadata
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret,
            'amount_usd': total_amount_usd,
            'amount_ugx': total_amount_ugx
        })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook', methods=['POST'])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, 'your_webhook_secret'
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_successful_payment(payment_intent)
    
    return jsonify({'received': True})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', [email])
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user.get('is_admin', 0)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', [email])
        user = cursor.fetchone()
        
        if user:
            # Generate password reset token
            token = generate_reset_token()
            
            # Store token in database
            cursor.execute('UPDATE users SET reset_token = %s WHERE id = %s',
                         (token, user['id']))
            mysql.connection.commit()
            
            # Send reset email
            send_reset_email(email, token)
            
            flash('Password reset instructions sent to your email', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email not found', 'error')
    
    return render_template('reset_password.html')

# Add near the top of the file, with other configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_successful_payment(payment_intent):
    user_id = payment_intent.metadata.get('user_id')
    amount = payment_intent.amount / 100  # Convert from cents to dollars
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        UPDATE orders 
        SET status = 'paid', 
            payment_id = %s,
            paid_amount = %s
        WHERE user_id = %s AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
    ''', (payment_intent.id, amount, user_id))
    mysql.connection.commit()

def send_reset_email(email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    subject = 'Password Reset Request'
    body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, please ignore this email.
'''
    msg = Message(subject,
                 sender=app.config['MAIL_USERNAME'],
                 recipients=[email])
    msg.body = body
    mail.send(msg)

def generate_reset_token():
    return secrets.token_urlsafe(32)

@app.route('/admin/toggle_membership/<int:user_id>', methods=['POST'])
@admin_required
def toggle_membership(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE users 
            SET is_member = NOT is_member 
            WHERE id = %s
        """, [user_id])
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        flash('Please login to view your wishlist', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT w.*, p.name, p.price, p.image_url, p.description 
        FROM wishlist w 
        JOIN products p ON w.product_id = p.id 
        WHERE w.user_id = %s
    ''', [session['user_id']])
    
    wishlist_items = cursor.fetchall()
    return render_template('wishlist.html', wishlist_items=wishlist_items)

if __name__ == '__main__':
    app.run(debug=True)
