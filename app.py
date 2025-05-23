from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import requests
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "your_secret_key"


def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',  
        password='puneetha@1204',  
        database='StockManagement1'
    )
    return connection

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Stocks table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Stocks (
            stock_id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL UNIQUE,
            company_name VARCHAR(100) NOT NULL,
            sector VARCHAR(50),
            current_price DECIMAL(10,2) NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Stock_Price_History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Stock_Price_History (
            history_id INT AUTO_INCREMENT PRIMARY KEY,
            stock_id INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            price_change DECIMAL(10,2),
            price_change_percent DECIMAL(10,2),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id)
        )
    ''')
    
    # Create Brokers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Brokers (
            broker_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            commission_rate DECIMAL(5,2) NOT NULL,
            contact_email VARCHAR(100) NOT NULL
        )
    ''')
    
    # Create Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            stock_id INT NOT NULL,
            broker_id INT NOT NULL,
            transaction_type ENUM('BUY', 'SELL') NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id),
            FOREIGN KEY (broker_id) REFERENCES Brokers(broker_id)
        )
    ''')
    
    # Create Portfolio_Holdings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Portfolio_Holdings (
            holding_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            stock_id INT NOT NULL,
            quantity INT NOT NULL,
            purchase_price DECIMAL(10,2) NOT NULL,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (stock_id) REFERENCES Stocks(stock_id)
        )
    ''')
    
    # Add initial stocks if the table is empty
    cursor.execute('SELECT COUNT(*) FROM Stocks')
    if cursor.fetchone()[0] == 0:
        initial_stocks = [
            ('AAPL', 'Apple Inc.', 'Technology', 150.00),
            ('MSFT', 'Microsoft Corporation', 'Technology', 280.00),
            ('GOOGL', 'Alphabet Inc.', 'Technology', 140.00),
            ('AMZN', 'Amazon.com Inc.', 'Consumer Cyclical', 130.00),
            ('META', 'Meta Platforms Inc.', 'Technology', 300.00),
            ('TSLA', 'Tesla Inc.', 'Automotive', 200.00),
            ('JPM', 'JPMorgan Chase & Co.', 'Financial Services', 150.00),
            ('V', 'Visa Inc.', 'Financial Services', 250.00),
            ('WMT', 'Walmart Inc.', 'Retail', 150.00),
            ('JNJ', 'Johnson & Johnson', 'Healthcare', 150.00)
        ]
        cursor.executemany('''
            INSERT INTO Stocks (symbol, company_name, sector, current_price)
            VALUES (%s, %s, %s, %s)
        ''', initial_stocks)
    
    # Add initial brokers if the table is empty
    cursor.execute('SELECT COUNT(*) FROM Brokers')
    if cursor.fetchone()[0] == 0:
        initial_brokers = [
            ('Charles Schwab', 0.25, 'support@schwab.com'),
            ('Fidelity Investments', 0.30, 'support@fidelity.com'),
            ('E*TRADE', 0.35, 'support@etrade.com'),
            ('TD Ameritrade', 0.28, 'support@tdameritrade.com'),
            ('Interactive Brokers', 0.20, 'support@interactivebrokers.com')
        ]
        cursor.executemany('''
            INSERT INTO Brokers (name, commission_rate, contact_email)
            VALUES (%s, %s, %s)
        ''', initial_brokers)
    
    conn.commit()
    cursor.close()
    conn.close()

def update_db_structure():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if purchase_price column exists
        cursor.execute("SHOW COLUMNS FROM Portfolio_Holdings LIKE 'purchase_price'")
        if not cursor.fetchone():
            # Add purchase_price column
            cursor.execute('''
                ALTER TABLE Portfolio_Holdings 
                ADD COLUMN purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0.00
            ''')
            
            # Update existing records with default purchase price
            cursor.execute('''
                UPDATE Portfolio_Holdings ph
                JOIN Stocks s ON ph.stock_id = s.stock_id
                SET ph.purchase_price = s.current_price
                WHERE ph.purchase_price = 0.00
            ''')
            
            conn.commit()
            print("Database structure updated successfully")
    except Exception as e:
        print(f"Error updating database structure: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# Initialize database on startup
init_db()
# Update database structure
update_db_structure()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['is_admin'] = user.get('is_admin', 0)
            if user.get('is_admin', 0) == 1:
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_index'))
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        nationality = request.form['nationality']
        date_of_birth = request.form['date_of_birth']
        pan_card = request.form['pan_card']
        aadhar_card = request.form['aadhar_card']
        address = request.form['address']
        income = request.form['income']
        emergency_contact = request.form['emergency_contact']
        email = request.form['email']
        phone = request.form['phone']
        city = request.form['city']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = first_name + ' ' + last_name
        # Password validation
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            flash('Password must contain at least 8 characters, including uppercase, lowercase, numbers, and special characters.', 'danger')
            return redirect(url_for('signup'))
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))
        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO Users (name, email, phone, city, password_hash, first_name, last_name, gender, nationality, date_of_birth, pan_card, aadhar_card, address, income, emergency_contact)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (name, email, phone, city, password_hash, first_name, last_name, gender, nationality, date_of_birth, pan_card, aadhar_card, address, income, emergency_contact))
            conn.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            if err.errno == 1062:  # Duplicate entry error
                flash('Email already exists!', 'danger')
            else:
                flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Add login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Modify existing routes to require login
@app.route('/')
@login_required
def index():
    if session.get('is_admin', 0):
        return redirect(url_for('admin_index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get portfolio value
    cursor.execute('''
        SELECT SUM(quantity * current_price) as total_value
        FROM Portfolio_Holdings p
        JOIN Stocks s ON p.stock_id = s.stock_id
        WHERE p.user_id = %s
    ''', (session['user_id'],))
    portfolio_value = cursor.fetchone()['total_value'] or 0
    
    # Get active stocks count
    cursor.execute('''
        SELECT COUNT(DISTINCT stock_id) as count
        FROM Portfolio_Holdings
        WHERE user_id = %s AND quantity > 0
    ''', (session['user_id'],))
    active_stocks = cursor.fetchone()['count']
    
    # Get watchlist count
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM Watchlist
        WHERE user_id = %s
    ''', (session['user_id'],))
    watchlist_count = cursor.fetchone()['count']
    
    # Get recent transactions count (last 30 days)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM Transactions
        WHERE user_id = %s AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    ''', (session['user_id'],))
    recent_transactions = cursor.fetchone()['count']
    
    # Get recent transactions list
    cursor.execute('''
        SELECT t.*, s.symbol as stock_symbol, s.company_name
        FROM Transactions t
        JOIN Stocks s ON t.stock_id = s.stock_id
        WHERE t.user_id = %s
        ORDER BY t.transaction_date DESC
        LIMIT 5
    ''', (session['user_id'],))
    recent_transactions_list = cursor.fetchall()
    
    # Get watchlist with current prices
    cursor.execute('''
        SELECT w.*, s.symbol, s.company_name, s.current_price,
               COALESCE(
                   (SELECT price_change_percent 
                    FROM Stock_Price_History 
                    WHERE stock_id = s.stock_id 
                    ORDER BY recorded_at DESC 
                    LIMIT 1), 0
               ) as price_change
        FROM Watchlist w
        JOIN Stocks s ON w.stock_id = s.stock_id
        WHERE w.user_id = %s
        ORDER BY s.symbol
    ''', (session['user_id'],))
    watchlist = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('user_index.html',
                         portfolio_value=portfolio_value,
                         active_stocks=active_stocks,
                         watchlist_count=watchlist_count,
                         recent_transactions=recent_transactions,
                         recent_transactions_list=recent_transactions_list,
                         watchlist=watchlist)

#userscd 
@app.route('/users')
@login_required
def users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('view_users.html', users=users)

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    city = request.form['city']
    password = request.form.get('password', 'default_password')  # Get password if provided
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Hash the password
    password_hash = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Users (name, email, phone, city, password_hash, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, email, phone, city, password_hash, created_at))
        conn.commit()
        flash('User added successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('users'))

@app.route('/edit_user/<int:user_id>')
def edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_user.html', user=user)

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    gender = request.form['gender']
    nationality = request.form['nationality']
    date_of_birth = request.form['date_of_birth']
    pan_card = request.form['pan_card']
    aadhar_card = request.form['aadhar_card']
    address = request.form['address']
    income = request.form['income']
    emergency_contact = request.form['emergency_contact']
    email = request.form['email']
    phone = request.form['phone']
    city = request.form['city']
    name = first_name + ' ' + last_name
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Users SET name=%s, email=%s, phone=%s, city=%s, first_name=%s, last_name=%s, gender=%s, nationality=%s, date_of_birth=%s, pan_card=%s, aadhar_card=%s, address=%s, income=%s, emergency_contact=%s WHERE user_id=%s
        ''', (name, email, phone, city, first_name, last_name, gender, nationality, date_of_birth, pan_card, aadhar_card, address, income, emergency_contact, user_id))
        conn.commit()
        flash('User updated successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('profile'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM Users WHERE user_id = %s', (user_id,))
        conn.commit()
        flash('User deleted successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('users'))


#stocks
@app.route('/stocks')
def stocks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT s.*, 
               COALESCE((SELECT price_change FROM Stock_Price_History 
                WHERE stock_id = s.stock_id 
                ORDER BY recorded_at DESC LIMIT 1), 0) as price_change,
               COALESCE((SELECT price_change_percent FROM Stock_Price_History 
                WHERE stock_id = s.stock_id 
                ORDER BY recorded_at DESC LIMIT 1), 0) as price_change_percent
        FROM Stocks s
        ORDER BY s.symbol
    ''')
    stocks = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('stocks.html', stocks=stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    symbol = request.form['symbol']
    company_name = request.form['company_name']
    sector = request.form['sector']
    current_price = request.form['current_price']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO Stocks (symbol, company_name, sector, current_price) VALUES (%s, %s, %s, %s)',
                      (symbol, company_name, sector, current_price))
        conn.commit()
        flash('Stock added successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('stocks'))

@app.route('/brokers')
@login_required
def brokers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Brokers')
    brokers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('brokers.html', brokers=brokers, is_admin=session.get('is_admin', 0))

@app.route('/admin/brokers')
@login_required
def admin_brokers():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Brokers ORDER BY name')
    brokers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_brokers.html', brokers=brokers)

@app.route('/admin/add_broker', methods=['POST'])
@login_required
def admin_add_broker():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    name = request.form['name']
    commission_rate = request.form['commission_rate']
    contact_email = request.form['contact_email']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Brokers (name, commission_rate, contact_email) 
            VALUES (%s, %s, %s)
        ''', (name, commission_rate, contact_email))
        conn.commit()
        flash('Broker added successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_brokers'))

@app.route('/admin/edit_broker/<int:broker_id>', methods=['POST'])
@login_required
def admin_edit_broker(broker_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    name = request.form['name']
    commission_rate = request.form['commission_rate']
    contact_email = request.form['contact_email']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Brokers 
            SET name = %s, commission_rate = %s, contact_email = %s 
            WHERE broker_id = %s
        ''', (name, commission_rate, contact_email, broker_id))
        conn.commit()
        flash('Broker updated successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_brokers'))

@app.route('/admin/delete_broker/<int:broker_id>', methods=['POST'])
@login_required
def admin_delete_broker(broker_id):
    if not session.get('is_admin', 0):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if broker is used in any transactions
        cursor.execute('SELECT COUNT(*) FROM Transactions WHERE broker_id = %s', (broker_id,))
        if cursor.fetchone()[0] > 0:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete broker: They have associated transactions'
            }), 400
        
        cursor.execute('DELETE FROM Brokers WHERE broker_id = %s', (broker_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Broker deleted successfully'})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

#transactions
@app.route('/transactions')
@login_required
def transactions():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT t.*, s.symbol, s.company_name, b.name as broker_name 
        FROM Transactions t
        JOIN Stocks s ON t.stock_id = s.stock_id
        LEFT JOIN Brokers b ON t.broker_id = b.broker_id
        WHERE t.user_id = %s
        ORDER BY t.transaction_date DESC
    ''', (user_id,))
    transactions = cursor.fetchall()

    # Convert transaction_date strings to datetime objects
    for transaction in transactions:
        if isinstance(transaction['transaction_date'], str):
            transaction['transaction_date'] = datetime.datetime.strptime(
                transaction['transaction_date'], 
                '%Y-%m-%d %H:%M:%S'
            )

    cursor.execute('SELECT * FROM Stocks')
    stocks = cursor.fetchall()
    cursor.execute('SELECT * FROM Brokers')
    brokers = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('transactions.html', transactions=transactions, stocks=stocks, brokers=brokers)

@app.route('/get_stock_price/<int:stock_id>')
@login_required
def get_stock_price(stock_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT current_price FROM Stocks WHERE stock_id = %s', (stock_id,))
        stock = cursor.fetchone()
        if stock:
            return jsonify({'success': True, 'price': float(stock['current_price'])})
        return jsonify({'success': False, 'message': 'Stock not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    user_id = session['user_id']  # Get user_id from session instead of form
    stock_id = request.form['stock_id']
    broker_id = request.form['broker_id']
    transaction_type = request.form['transaction_type']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    transaction_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Transactions 
            (user_id, stock_id, broker_id, transaction_type, quantity, price, transaction_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, stock_id, broker_id, transaction_type, quantity, price, transaction_date))

        if transaction_type == 'BUY':
            cursor.execute('SELECT * FROM Portfolio_Holdings WHERE user_id = %s AND stock_id = %s',
                           (user_id, stock_id))
            holding = cursor.fetchone()

            if holding:
                cursor.execute('''
                    UPDATE Portfolio_Holdings 
                    SET quantity = quantity + %s,
                        purchase_price = ((quantity * purchase_price) + (%s * %s)) / (quantity + %s)
                    WHERE user_id = %s AND stock_id = %s
                ''', (quantity, quantity, price, quantity, user_id, stock_id))
            else:
                cursor.execute('''
                    INSERT INTO Portfolio_Holdings 
                    (user_id, stock_id, quantity, purchase_price, purchase_date) 
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, stock_id, quantity, price, transaction_date))

        elif transaction_type == 'SELL':
            cursor.execute('''
                UPDATE Portfolio_Holdings 
                SET quantity = quantity - %s 
                WHERE user_id = %s AND stock_id = %s
            ''', (quantity, user_id, stock_id))

            cursor.execute('''
                DELETE FROM Portfolio_Holdings 
                WHERE user_id = %s AND stock_id = %s AND quantity <= 0
            ''', (user_id, stock_id))

        conn.commit()
        flash('Transaction recorded successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('transactions'))


#portfolio
@app.route('/portfolio')
@login_required
def portfolio():
    user_id = session['user_id']
    portfolio_data = calculate_portfolio_value(user_id)
    return render_template('portfolio.html', 
                         holdings=portfolio_data['holdings'],
                         total_value=portfolio_data['total_value'],
                         total_profit_loss=portfolio_data['total_profit_loss'])

#watchlist
@app.route('/watchlist')
@login_required
def watchlist():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT w.*, s.symbol, s.company_name, s.current_price, s.sector,
               COALESCE((SELECT price_change FROM Stock_Price_History 
                WHERE stock_id = s.stock_id 
                ORDER BY recorded_at DESC LIMIT 1), 0) as price_change,
               COALESCE((SELECT price_change_percent FROM Stock_Price_History 
                WHERE stock_id = s.stock_id 
                ORDER BY recorded_at DESC LIMIT 1), 0) as price_change_percent
        FROM Watchlist w
        JOIN Stocks s ON w.stock_id = s.stock_id
        WHERE w.user_id = %s
        ORDER BY w.added_on DESC
    ''', (session['user_id'],))
    watchlist = cursor.fetchall()
    
    # Convert added_on to datetime objects
    for item in watchlist:
        if isinstance(item['added_on'], str):
            item['added_on'] = datetime.datetime.strptime(item['added_on'], '%Y-%m-%d %H:%M:%S')
    
    cursor.close()
    conn.close()
    return render_template('watchlist.html', watchlist=watchlist)

@app.route('/add_to_watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to add stocks to watchlist'}), 401
        
    stock_id = request.form.get('stock_id')
    if not stock_id:
        return jsonify({'success': False, 'message': 'Stock ID is required'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if stock exists
        cursor.execute('SELECT stock_id FROM Stocks WHERE stock_id = %s', (stock_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Stock not found'}), 404
            
        # Check if already in watchlist
        cursor.execute('''
            SELECT * FROM Watchlist 
            WHERE user_id = %s AND stock_id = %s
        ''', (session['user_id'], stock_id))
        
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Stock is already in your watchlist'}), 400
            
        # Add to watchlist
        added_on = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO Watchlist (user_id, stock_id, added_on) 
            VALUES (%s, %s, %s)
        ''', (session['user_id'], stock_id, added_on))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Stock added to watchlist successfully'
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'Error adding to watchlist: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/remove_from_watchlist', methods=['POST'])
@login_required
def remove_from_watchlist():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to manage your watchlist'}), 401
        
    stock_id = request.form.get('stock_id')
    if not stock_id:
        return jsonify({'success': False, 'message': 'Stock ID is required'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if stock exists in user's watchlist
        cursor.execute('''
            SELECT * FROM Watchlist 
            WHERE user_id = %s AND stock_id = %s
        ''', (session['user_id'], stock_id))
        
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Stock not found in your watchlist'}), 404
            
        # Remove from watchlist
        cursor.execute('''
            DELETE FROM Watchlist 
            WHERE user_id = %s AND stock_id = %s
        ''', (session['user_id'], stock_id))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Stock removed from watchlist successfully'
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'Error removing from watchlist: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def log_action(action, performed_by):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Logs (action, performed_by, log_timestamp) VALUES (%s, %s, %s)',
                  (action, performed_by, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/admin/profile')
@login_required
def admin_profile():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    # Add print statement to check user data
    print(f"Fetched user for admin edit profile: {user}")

    return render_template('admin_profile.html', user=user)

@app.route('/admin/edit_profile')
@login_required
def admin_edit_profile():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    # Add print statement to check user data
    print(f"Fetched user for admin edit profile: {user}")

    return render_template('admin_edit_profile.html', user=user)

@app.route('/admin/update_profile', methods=['POST'])
@login_required
def admin_update_profile():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    gender = request.form['gender']
    nationality = request.form['nationality']
    date_of_birth = request.form['date_of_birth']
    pan_card = request.form['pan_card']
    aadhar_card = request.form['aadhar_card']
    address = request.form['address']
    income = request.form['income']
    emergency_contact = request.form['emergency_contact']
    email = request.form['email']
    phone = request.form['phone']
    city = request.form['city']
    name = first_name + ' ' + last_name

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Users 
            SET name=%s, email=%s, phone=%s, city=%s, first_name=%s, last_name=%s, 
                gender=%s, nationality=%s, date_of_birth=%s, pan_card=%s, 
                aadhar_card=%s, address=%s, income=%s, emergency_contact=%s 
            WHERE user_id=%s
        ''', (name, email, phone, city, first_name, last_name, gender, nationality, 
              date_of_birth, pan_card, aadhar_card, address, income, emergency_contact, 
              session['user_id']))
        conn.commit()
        flash('Profile updated successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Error updating profile: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_profile'))

@app.route('/admin')
@login_required
def admin_index():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_index.html', users=users)

# Admin: View all users
@app.route('/admin/users')
@login_required
def admin_users():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users)

# Admin: Manage stocks
@app.route('/admin/stocks')
@login_required
def admin_stocks():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get stocks with their latest price changes
        cursor.execute('''
            SELECT s.*, 
                   COALESCE((SELECT price_change FROM Stock_Price_History 
                    WHERE stock_id = s.stock_id 
                    ORDER BY recorded_at DESC LIMIT 1), 0) as price_change,
                   COALESCE((SELECT price_change_percent FROM Stock_Price_History 
                    WHERE stock_id = s.stock_id 
                    ORDER BY recorded_at DESC LIMIT 1), 0) as price_change_percent
            FROM Stocks s
            ORDER BY s.symbol
        ''')
        stocks = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Update prices before displaying
        update_stock_prices()
        
        return render_template('admin_stocks.html', stocks=stocks)
    except Exception as e:
        print(f"Error in admin_stocks: {str(e)}")
        flash('Error loading stocks. Please try again.', 'danger')
        return redirect(url_for('admin_index'))

# Admin: View all transactions
@app.route('/admin/transactions')
@login_required
def admin_transactions():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''SELECT t.*, u.name as user_name, s.symbol, b.name as broker_name FROM Transactions t JOIN Users u ON t.user_id = u.user_id JOIN Stocks s ON t.stock_id = s.stock_id LEFT JOIN Brokers b ON t.broker_id = b.broker_id''')
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_transactions.html', transactions=transactions)

# Admin: View all portfolios
@app.route('/admin/portfolios')
@login_required
def admin_portfolios():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''SELECT p.*, u.name as user_name, s.symbol, s.company_name, s.current_price, (s.current_price * p.quantity) AS total_value FROM Portfolio_Holdings p JOIN Users u ON p.user_id = u.user_id JOIN Stocks s ON p.stock_id = s.stock_id''')
    holdings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_portfolios.html', holdings=holdings)

# Admin: View all watchlists
@app.route('/admin/watchlist')
@login_required
def admin_watchlist():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''SELECT w.*, u.name as user_name, s.symbol, s.company_name, s.current_price FROM Watchlist w JOIN Users u ON w.user_id = u.user_id JOIN Stocks s ON w.stock_id = s.stock_id''')
    watchlist = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_watchlist.html', watchlist=watchlist)

@app.route('/admin/edit_stock/<int:stock_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_stock(stock_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        symbol = request.form['symbol']
        company_name = request.form['company_name']
        sector = request.form['sector']
        current_price = request.form['current_price']
        cursor.execute('UPDATE Stocks SET symbol=%s, company_name=%s, sector=%s, current_price=%s WHERE stock_id=%s',
                       (symbol, company_name, sector, current_price, stock_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Stock updated successfully!', 'success')
        return redirect(url_for('admin_stocks'))
    else:
        cursor.execute('SELECT * FROM Stocks WHERE stock_id = %s', (stock_id,))
        stock = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('admin_edit_stock.html', stock=stock)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        nationality = request.form['nationality']
        date_of_birth = request.form['date_of_birth']
        pan_card = request.form['pan_card']
        aadhar_card = request.form['aadhar_card']
        address = request.form['address']
        income = request.form['income']
        emergency_contact = request.form['emergency_contact']
        email = request.form['email']
        phone = request.form['phone']
        city = request.form['city']
        name = first_name + ' ' + last_name
        cursor.execute('''
            UPDATE Users SET name=%s, email=%s, phone=%s, city=%s, first_name=%s, last_name=%s, gender=%s, nationality=%s, date_of_birth=%s, pan_card=%s, aadhar_card=%s, address=%s, income=%s, emergency_contact=%s WHERE user_id=%s
        ''', (name, email, phone, city, first_name, last_name, gender, nationality, date_of_birth, pan_card, aadhar_card, address, income, emergency_contact, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    else:
        cursor.execute('SELECT * FROM Users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('admin_edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Users WHERE user_id = %s AND is_admin = 0', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def admin_delete_transaction(transaction_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Transactions WHERE transaction_id = %s', (transaction_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('admin_transactions'))

@app.route('/admin/delete_portfolio/<int:holding_id>', methods=['POST'])
@login_required
def admin_delete_portfolio(holding_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Portfolio_Holdings WHERE holding_id = %s', (holding_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Portfolio holding deleted successfully!', 'success')
    return redirect(url_for('admin_portfolios'))

@app.route('/admin/add_stock', methods=['GET', 'POST'])
@login_required
def admin_add_stock():
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        symbol = request.form['symbol']
        company_name = request.form['company_name']
        sector = request.form['sector']
        current_price = request.form['current_price']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Stocks (symbol, company_name, sector, current_price) VALUES (%s, %s, %s, %s)',
                       (symbol, company_name, sector, current_price))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Stock added successfully!', 'success')
        return redirect(url_for('admin_stocks'))
    return render_template('admin_add_stock.html')

@app.route('/admin/delete_stock/<int:stock_id>', methods=['POST'])
@login_required
def admin_delete_stock(stock_id):
    if not session.get('is_admin', 0):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Stocks WHERE stock_id = %s', (stock_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Stock deleted successfully!', 'success')
    return redirect(url_for('admin_stocks'))

def update_stock_prices():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all stocks
        cursor.execute('SELECT stock_id, symbol, current_price FROM Stocks')
        stocks = cursor.fetchall()
        
        updated_count = 0
        error_count = 0
        error_messages = []
        
        for stock in stocks:
            try:
                # Clean and format the symbol
                symbol = stock['symbol'].strip().upper()
                old_price = float(stock['current_price'])
                
                # Get stock data from yfinance
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    error_messages.append(f"No info available for {symbol}")
                    error_count += 1
                    continue
                
                # Get historical data
                hist = ticker.history(period='2d')
                if hist.empty:
                    error_messages.append(f"No historical data for {symbol}")
                    error_count += 1
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[-2])
                
                if current_price <= 0 or previous_price <= 0:
                    error_messages.append(f"Invalid price data for {symbol}")
                    error_count += 1
                    continue
                
                price_change = current_price - previous_price
                price_change_percent = (price_change / previous_price) * 100
                
                # Update stock price
                cursor.execute('''
                    UPDATE Stocks 
                    SET current_price = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE stock_id = %s
                ''', (current_price, stock['stock_id']))
                
                # Record price history
                cursor.execute('''
                    INSERT INTO Stock_Price_History 
                    (stock_id, price, price_change, price_change_percent)
                    VALUES (%s, %s, %s, %s)
                ''', (stock['stock_id'], current_price, price_change, price_change_percent))
                
                updated_count += 1
                
            except Exception as e:
                error_messages.append(f"Error updating {stock['symbol']}: {str(e)}")
                error_count += 1
                continue
        
        conn.commit()
        
        if error_count > 0:
            return jsonify({
                'success': True,
                'message': f'Updated {updated_count} stocks with {error_count} errors.',
                'errors': error_messages[:5]  # Return first 5 errors to avoid overwhelming response
            })
        else:
            return jsonify({
                'success': True,
                'message': f'Successfully updated {updated_count} stocks.'
            })
            
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating stock prices: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def calculate_portfolio_value(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all holdings for the user with current prices
    cursor.execute('''
        SELECT ph.*, s.current_price, s.symbol, s.company_name,
               (ph.quantity * s.current_price) as current_value,
               (ph.quantity * s.current_price) - (ph.quantity * ph.purchase_price) as profit_loss
        FROM Portfolio_Holdings ph
        JOIN Stocks s ON ph.stock_id = s.stock_id
        WHERE ph.user_id = %s
    ''', (user_id,))
    
    holdings = cursor.fetchall()
    total_value = sum(holding['current_value'] for holding in holdings)
    total_profit_loss = sum(holding['profit_loss'] for holding in holdings)
    
    cursor.close()
    conn.close()
    
    return {
        'holdings': holdings,
        'total_value': total_value,
        'total_profit_loss': total_profit_loss
    }

# Modify the scheduler to handle errors gracefully
def start_scheduler():
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=update_stock_prices, trigger="interval", minutes=5, id='update_prices')
        scheduler.start()
        print("Price update scheduler started successfully")
    except Exception as e:
        print(f"Error starting scheduler: {str(e)}")

# Start the scheduler when the application starts
start_scheduler()

def fetch_and_insert_stocks():
    api_key = '682f3ec2d515b7.27991093'
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    response = requests.get(f'https://financialmodelingprep.com/api/v3/stock/list?apikey={api_key}')
    if response.status_code == 200:
        stocks = response.json()
        for stock in stocks:
            cursor.execute('INSERT INTO Stocks (symbol, company_name, sector, current_price) VALUES (%s, %s, %s, %s)',
                           (stock['symbol'], stock['name'], stock['sector'], stock['price']))
    conn.commit()
    cursor.close()
    conn.close()

# Call fetch_and_insert_stocks() to populate the database with stocks
fetch_and_insert_stocks()

@app.route('/refresh_prices', methods=['POST'])
@login_required
def refresh_prices():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all stocks
        cursor.execute('SELECT stock_id, symbol, current_price FROM Stocks')
        stocks = cursor.fetchall()
        
        updated_count = 0
        error_count = 0
        error_messages = []
        
        for stock in stocks:
            try:
                # Clean and format the symbol
                symbol = stock['symbol'].strip().upper()
                old_price = float(stock['current_price'])
                
                # Get stock data from yfinance
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    error_messages.append(f"No info available for {symbol}")
                    error_count += 1
                    continue
                
                # Get historical data
                hist = ticker.history(period='2d')
                if hist.empty:
                    error_messages.append(f"No historical data for {symbol}")
                    error_count += 1
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[-2])
                
                if current_price <= 0 or previous_price <= 0:
                    error_messages.append(f"Invalid price data for {symbol}")
                    error_count += 1
                    continue
                
                price_change = current_price - previous_price
                price_change_percent = (price_change / previous_price) * 100
                
                # Update stock price
                cursor.execute('''
                    UPDATE Stocks 
                    SET current_price = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE stock_id = %s
                ''', (current_price, stock['stock_id']))
                
                # Record price history
                cursor.execute('''
                    INSERT INTO Stock_Price_History 
                    (stock_id, price, price_change, price_change_percent)
                    VALUES (%s, %s, %s, %s)
                ''', (stock['stock_id'], current_price, price_change, price_change_percent))
                
                updated_count += 1
                
            except Exception as e:
                error_messages.append(f"Error updating {stock['symbol']}: {str(e)}")
                error_count += 1
                continue
        
        conn.commit()
        
        if error_count > 0:
            return jsonify({
                'success': True,
                'message': f'Updated {updated_count} stocks with {error_count} errors.',
                'errors': error_messages[:5]  # Return first 5 errors to avoid overwhelming response
            })
        else:
            return jsonify({
                'success': True,
                'message': f'Successfully updated {updated_count} stocks.'
            })
            
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating stock prices: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/admin/stock_history/<symbol>')
@login_required
def admin_stock_history(symbol):
    conn = None
    cursor = None
    try:
        # Clean and format the symbol
        symbol = symbol.strip().upper()
        
        # Get stock ID
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get stock ID with case-insensitive search and handle special cases
        cursor.execute("SELECT stock_id FROM Stocks WHERE UPPER(TRIM(symbol)) = %s", (symbol,))
        result = cursor.fetchone()
        
        if not result:
            # Try to get stock data directly from yfinance
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if not info:
                    return jsonify({'error': f'Stock not found: {symbol}'}), 404
                
                # Get historical data
                hist = ticker.history(period='10d')
                if hist.empty:
                    return jsonify({'error': f'No historical data available for {symbol}'}), 404
                
                history = []
                for index, row in hist.iterrows():
                    history.append({
                        'price': float(row['Close']),
                        'price_change': float(row['Close'] - row['Open']),
                        'price_change_percent': float((row['Close'] - row['Open']) / row['Open'] * 100),
                        'date': index.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                return jsonify({'history': history})
                
            except Exception as e:
                return jsonify({'error': f'Error fetching data for {symbol}: {str(e)}'}), 404
            
        stock_id = result['stock_id']
        
        # Get price history
        cursor.execute("""
            SELECT price, price_change, price_change_percent, recorded_at
            FROM Stock_Price_History
            WHERE stock_id = %s
            ORDER BY recorded_at DESC
            LIMIT 10
        """, (stock_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'price': float(row['price']),
                'price_change': float(row['price_change']),
                'price_change_percent': float(row['price_change_percent']),
                'date': row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
            })
            
        if not history:
            # If no history in database, try to get from yfinance
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='10d')
                if not hist.empty:
                    for index, row in hist.iterrows():
                        history.append({
                            'price': float(row['Close']),
                            'price_change': float(row['Close'] - row['Open']),
                            'price_change_percent': float((row['Close'] - row['Open']) / row['Open'] * 100),
                            'date': index.strftime('%Y-%m-%d %H:%M:%S')
                        })
            except Exception as e:
                pass  # If yfinance fails, just return empty history
            
        return jsonify({'history': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/stock_history/<symbol>')
def user_stock_history(symbol):
    conn = None
    cursor = None
    try:
        # Clean and format the symbol
        symbol = symbol.strip().upper()
        
        # Get stock ID
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get stock ID with case-insensitive search and handle special cases
        cursor.execute("SELECT stock_id FROM Stocks WHERE UPPER(TRIM(symbol)) = %s", (symbol,))
        result = cursor.fetchone()
        
        if not result:
            # Try to get stock data directly from yfinance
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if not info:
                    return jsonify({'error': f'Stock not found: {symbol}'}), 404
                
                # Get historical data
                hist = ticker.history(period='10d')
                if hist.empty:
                    return jsonify({'error': f'No historical data available for {symbol}'}), 404
                
                history = []
                for index, row in hist.iterrows():
                    history.append({
                        'price': float(row['Close']),
                        'price_change': float(row['Close'] - row['Open']),
                        'price_change_percent': float((row['Close'] - row['Open']) / row['Open'] * 100),
                        'date': index.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                return jsonify({'history': history})
                
            except Exception as e:
                return jsonify({'error': f'Error fetching data for {symbol}: {str(e)}'}), 404
            
        stock_id = result['stock_id']
        
        # Get price history
        cursor.execute("""
            SELECT price, price_change, price_change_percent, recorded_at
            FROM Stock_Price_History
            WHERE stock_id = %s
            ORDER BY recorded_at DESC
            LIMIT 10
        """, (stock_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'price': float(row['price']),
                'price_change': float(row['price_change']),
                'price_change_percent': float(row['price_change_percent']),
                'date': row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
            })
            
        if not history:
            # If no history in database, try to get from yfinance
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='10d')
                if not hist.empty:
                    for index, row in hist.iterrows():
                        history.append({
                            'price': float(row['Close']),
                            'price_change': float(row['Close'] - row['Open']),
                            'price_change_percent': float((row['Close'] - row['Open']) / row['Open'] * 100),
                            'date': index.strftime('%Y-%m-%d %H:%M:%S')
                        })
            except Exception as e:
                pass  # If yfinance fails, just return empty history
            
        return jsonify({'history': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
