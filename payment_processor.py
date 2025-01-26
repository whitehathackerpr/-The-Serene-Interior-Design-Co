from flask import url_for
from flask_mail import Message
from app import mail, mysql, app
import MySQLdb

def handle_successful_payment(payment_intent):
    user_id = payment_intent.metadata.get('user_id')
    amount = payment_intent.amount / 100  # Convert from cents
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Create order
    cursor.execute('''
        INSERT INTO orders (user_id, total_amount, status, payment_intent_id)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, amount, 'processing', payment_intent.id))
    
    order_id = cursor.lastrowid
    
    # Get cart items
    cursor.execute('SELECT cart FROM users WHERE id = %s', [user_id])
    cart = cursor.fetchone()['cart']
    
    # Create order items
    for product_id, quantity in cart.items():
        cursor.execute('SELECT price FROM products WHERE id = %s', [product_id])
        price = cursor.fetchone()['price']
        
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, %s)
        ''', (order_id, product_id, quantity, price))
        
        # Update product stock
        cursor.execute('''
            UPDATE products 
            SET stock = stock - %s 
            WHERE id = %s
        ''', (quantity, product_id))
    
    # Clear user's cart
    cursor.execute('UPDATE users SET cart = NULL WHERE id = %s', [user_id])
    mysql.connection.commit()
    
    # Send confirmation email
    send_order_confirmation(order_id)

def send_order_confirmation(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get order details
    cursor.execute('''
        SELECT o.*, u.email, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s
    ''', [order_id])
    order = cursor.fetchone()
    
    # Get order items
    cursor.execute('''
        SELECT oi.*, p.name
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    ''', [order_id])
    items = cursor.fetchall()
    
    # Create email content
    subject = f'Order Confirmation - Order #{order_id}'
    
    body = f'''
    Dear {order['customer_name']},

    Thank you for your order! We're pleased to confirm that your order has been received and is being processed.

    Order Details:
    Order ID: #{order_id}
    Total Amount: ${order['total_amount']:.2f}

    Items Ordered:
    '''
    
    for item in items:
        body += f"\n- {item['name']} x{item['quantity']} (${item['price']:.2f} each)"
    
    body += f'''

    You can track your order at: {url_for('order_tracking', order_id=order_id, _external=True)}

    Thank you for shopping with The Serene Interior Design Co.!

    Best regards,
    The Serene Interior Design Co. Team
    '''
    
    msg = Message(subject,
                 sender=app.config['MAIL_USERNAME'],
                 recipients=[order['email']])
    msg.body = body
    mail.send(msg) 