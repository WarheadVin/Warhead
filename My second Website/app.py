from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import datetime

# --- CONFIGURATION CONSTANTS ---
# Use this password to access the Admin Dashboard: http://127.0.0.1:5000/admin/orders
ADMIN_PASSWORD = "admin123" 
SHIPMENT_FEE = 3000 # KSh 3000 fixed shipping fee
DB_NAME = "car_orders.db"
API_PORT = 5000

# --- FLASK SETUP ---
app = Flask(__name__)
# Enable CORS for frontend running on a different port (e.g., Live Server)
CORS(app) 
# --- CAR DATA (Mutable state for demonstration) ---
CARS_DATA = [
    {"brand": "Toyota", "model": "Corolla", "price": 2500000, "image": "images/corolla.jpg", "desc": "Reliable sedan, fuel-efficient."},
    {"brand": "Toyota", "model": "RAV4", "price": 3500000, "image": "images/rav4.jpg", "desc": "Compact SUV, great for families."},
    {"brand": "Toyota", "model": "Land Cruiser", "price": 8500000, "image": "images/landcruiser.jpg", "desc": "Powerful off-road SUV."},
    {"brand": "Honda", "model": "Civic", "price": 2300000, "image": "images/civic.jpg", "desc": "Sporty compact with modern features."},
    {"brand": "Honda", "model": "CRV", "price": 3300000, "image": "images/crv.jpg", "desc": "Comfortable crossover."},
    {"brand": "Honda", "model": "Pilot", "price": 4500000, "image": "images/pilot.jpg", "desc": "Spacious 7-seater."},
    {"brand": "BMW", "model": "X1", "price": 4200000, "image": "images/x1.jpg", "desc": "Entry luxury crossover."},
    {"brand": "BMW", "model": "X3", "price": 5200000, "image": "images/x3.jpg", "desc": "Sporty and refined."},
    {"brand": "BMW", "model": "X5", "price": 7200000, "image": "images/x5.jpg", "desc": "Luxury SUV with power."},
]

# --- DATABASE SETUP ---
def get_db_connection():
    """Establishes and returns a SQLite database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def setup_database():
    """Initializes the 'orders' table if it does not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            country TEXT,
            county TEXT,
            brand TEXT,
            model TEXT,
            quantity INTEGER,
            price INTEGER,
            total_cost INTEGER,
            payment_method TEXT,
            order_time TEXT
        )
    """)
    conn.commit()
    conn.close()

setup_database()

# --- API ENDPOINTS ---

@app.route('/api/cars', methods=['GET'])
def get_cars():
    """Returns the current list of cars and the shipment fee."""
    return jsonify({"cars": CARS_DATA, "shipment_fee": SHIPMENT_FEE})

@app.route('/api/order', methods=['POST'])
def submit_order():
    """
    Receives order data, checks for Sunday closure, and saves the order to the database.
    (Sunday is day 6 in Python's weekday(), Monday is 0)
    """
    # Check for Sunday closure
    if datetime.datetime.now().weekday() == 6:
        return jsonify({"message": "Sorry, our online ordering system is closed on Sundays. Please try again tomorrow."}), 403

    data = request.get_json() 

    if not data or 'items' not in data:
        return jsonify({"message": "Invalid data received."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    order_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Calculate total order cost with shipment fee for the success message
        subtotal = sum(item['price'] * item['quantity'] for item in data['items'])
        final_total = subtotal + SHIPMENT_FEE
        
        # Insert a row for each car item in the order
        for item in data['items']:
            unit_price = item['price'] 
            item_total_cost = unit_price * item['quantity']

            cursor.execute("""
                INSERT INTO orders (name, phone, country, county, brand, model, quantity, price, total_cost, payment_method, order_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['name'], 
                data['phone'], 
                data['country'], 
                data['county'], 
                item['brand'], 
                item['model'], 
                item['quantity'], 
                unit_price, 
                item_total_cost, # Item subtotal (excluding shipping)
                data['payment'], 
                order_time
            ))
        
        conn.commit()
        return jsonify({"message": f"Order placed successfully! Total including KSh {SHIPMENT_FEE:,} shipment fee: KSh {final_total:,}."}), 201

    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
        return jsonify({"message": "Error processing order."}), 500
    finally:
        conn.close()


# --- ADMIN ENDPOINTS ---

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Checks the provided password against the hardcoded ADMIN_PASSWORD."""
    data = request.get_json()
    password = data.get('password')
    
    if password == ADMIN_PASSWORD:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "message": "Invalid Admin Password"}), 401

@app.route('/admin/orders', methods=['GET'])
def admin_orders_dashboard():
    """Renders the HTML for the Admin Dashboard with real-time data."""

    conn = get_db_connection()
    
    # Get summary data
    today_date = datetime.date.today().strftime("%Y-%m-%d")
    today_orders = conn.execute("SELECT * FROM orders WHERE order_time LIKE ?", (today_date + '%',)).fetchall()
    total_purchases_today = len(today_orders)

    # Get all orders
    all_orders = conn.execute("SELECT * FROM orders ORDER BY order_time DESC").fetchall()
    
    conn.close()
    
    # --- Start HTML Generation ---
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Admin Dashboard - Orders & Pricing</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; background: #f5f7fb; color: #333; }}
            h1 {{ color: #0b6d3a; border-bottom: 2px solid #e8f7ef; padding-bottom: 10px; }}
            h2 {{ color: #0b6d3a; margin-top: 30px; }}
            .summary {{ background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #0b6d3a; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .back-link {{ display: inline-block; margin-bottom: 20px; color: #0b6d3a; text-decoration: none; font-weight: bold; }}
            
            /* Price Management Table */
            .price-management table {{ width: 50%; min-width: 400px; margin-top: 15px; background: white; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .price-management th, .price-management td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            .price-management th {{ background-color: #e8f7ef; }}
            .price-management input[type="number"] {{ padding: 5px; width: 100px; border: 1px solid #ccc; border-radius: 4px; }}
            .price-management button {{ background-color: #0b6d3a; color: white; border: none; padding: 6px 10px; cursor: pointer; border-radius: 4px; }}
            .price-management button:hover {{ background-color: #084c26; }}

            /* Orders Table */
            #ordersTable {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            #ordersTable th, #ordersTable td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            #ordersTable th {{ background-color: #e8f7ef; color: #111; font-weight: bold; }}
            #ordersTable tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .delete-btn {{ background-color: #d9534f; color: white; border: none; padding: 5px 8px; cursor: pointer; border-radius: 4px; }}
            .delete-btn:hover {{ background-color: #c9302c; }}
        </style>
        <script>
            // Utility function to make API calls
            async function apiCall(url, method = 'GET', data = null) {{
                const options = {{
                    method: method,
                    headers: {{ 'Content-Type': 'application/json' }},
                }};
                if (data) {{
                    options.body = JSON.stringify(data);
                }}
                try {{
                    // Note: The Flask server is running locally on port 5000
                    const response = await fetch("http://127.0.0.1:5000" + url, options);
                    const result = await response.json();
                    if (!response.ok) {{
                        throw new Error(result.message || 'API call failed');
                    }}
                    return result;
                }} catch (error) {{
                    console.error('API Error:', error);
                    alert('Error: ' + error.message);
                    return null;
                }}
            }}

            // Function to handle price update
            window.updatePrice = async (brand, model) => {{
                // Construct ID safely
                const inputId = 'price-' + brand + '-' + model.replace(/ /g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
                const newPrice = parseInt(document.getElementById(inputId).value);

                if (isNaN(newPrice) || newPrice <= 0) {{
                    alert('Please enter a valid price.');
                    return;
                }}

                const result = await apiCall('/api/admin/set_price', 'POST', {{ brand, model, new_price: newPrice }});
                if (result) {{
                    alert('Price updated successfully! Refreshing the page...');
                    window.location.reload(); 
                }}
            }};

            // Function to handle order deletion
            window.deleteOrder = async (orderId) => {{
                if (confirm('Are you sure you want to delete this order ID: ' + orderId + '?')) {{
                    const result = await apiCall(`/api/admin/delete_order/${{orderId}}`, 'POST');
                    if (result) {{
                        alert('Order deleted successfully!');
                        // Remove the row from the table for instant feedback
                        const row = document.getElementById('order-row-' + orderId);
                        if(row) row.remove();
                    }}
                }}
            }};
        </script>
    </head>
    <body>
        <a href="/" class="back-link">&larr; Back to Shop</a>
        <h1>Admin Dashboard</h1>
        
        <h2>Sales Summary</h2>
        <div class="summary">
            <h3>Total Orders Today: <span style="color:#0b6d3a;">{total_purchases_today}</span></h3>
            <p>Shipment Fee Applied to All Orders: KSh {SHIPMENT_FEE:,}</p>
            <p>Ordering is currently disabled on Sundays. ({datetime.datetime.now().strftime("%A")})</p>
        </div>

        <h2>Car Price Management</h2>
        <div class="price-management">
            <table>
                <thead>
                    <tr>
                        <th>Brand</th>
                        <th>Model</th>
                        <th>Current Price (KSh)</th>
                        <th>New Price (KSh)</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Price Management Table Rows
    for car in CARS_DATA:
        # Create a clean ID for the input field
        car_id = f"{car['brand']}-{car['model']}".replace(' ', '_').replace('.', '')
        html += f"""
            <tr>
                <td>{car['brand']}</td>
                <td>{car['model']}</td>
                <td>{car['price']:,}</td>
                <td><input type="number" id="price-{car_id}" value="{car['price']}" min="1000"></td>
                <td><button onclick="updatePrice('{car['brand']}', '{car['model']}')">Update</button></td>
            </tr>
        """
        
    html += """
                </tbody>
            </table>
        </div>

        <h2>Order Management (All Time)</h2>
    """

    # Order Management Table
    if all_orders:
        html += "<table id='ordersTable'><thead><tr>"
        columns = ['ID', 'NAME', 'PHONE', 'COUNTRY', 'COUNTY', 'BRAND', 'MODEL', 'QTY', 'UNIT PRICE', 'ITEM TOTAL', 'PAYMENT', 'TIME', 'ACTION']
        for col in columns:
            html += f"<th>{col}</th>"
        html += "</tr></thead><tbody>"
        
        for order in all_orders:
            order_id = order['id']
            # Using Row objects to access data
            html += f"<tr id='order-row-{order_id}'>"
            html += f"<td>{order['id']}</td>"
            html += f"<td>{order['name']}</td>"
            html += f"<td>{order['phone']}</td>"
            html += f"<td>{order['country']}</td>"
            html += f"<td>{order['county']}</td>"
            html += f"<td>{order['brand']}</td>"
            html += f"<td>{order['model']}</td>"
            html += f"<td>{order['quantity']}</td>"
            html += f"<td>KSh {order['price']:,}</td>"
            html += f"<td>KSh {order['total_cost']:,}</td>" # This is the item's subtotal
            html += f"<td>{order['payment_method']}</td>"
            html += f"<td>{order['order_time']}</td>"
            html += f"<td><button class='delete-btn' onclick='deleteOrder({order_id})'>Delete</button></td>"
            html += "</tr>"
        html += "</tbody></table>"
    else:
        html += "<p>No orders have been placed yet.</p>"
        
    html += "</body></html>"
        
    return Response(html, mimetype='text/html')

@app.route('/api/admin/set_price', methods=['POST'])
def set_car_price():
    """Updates the price of a car model in the in-memory CARS_DATA."""
    data = request.get_json()
    brand = data.get('brand')
    model = data.get('model')
    new_price = data.get('new_price')
    
    if not all([brand, model, new_price]):
        return jsonify({"message": "Missing required fields."}), 400
    
    try:
        new_price = int(new_price)
    except ValueError:
        return jsonify({"message": "Price must be an integer."}), 400

    found = False
    for car in CARS_DATA:
        if car['brand'] == brand and car['model'] == model:
            car['price'] = new_price
            found = True
            break
    
    if found:
        return jsonify({"success": True, "message": f"Price for {brand} {model} updated to KSh {new_price:,}"}), 200
    else:
        return jsonify({"success": False, "message": "Car model not found."}), 404

@app.route('/api/admin/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    """Deletes an order entry from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted_count > 0:
        return jsonify({"success": True, "message": f"Order ID {order_id} deleted."}), 200
    else:
        return jsonify({"success": False, "message": f"Order ID {order_id} not found."}), 404


if __name__ == '__main__':
    print(f"Starting Flask server on http://127.0.0.1:{API_PORT}")
    app.run(port=API_PORT, debug=True)