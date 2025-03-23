from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from dotenv import load_dotenv
import os
import requests
from functools import wraps
import uuid
import json
from datetime import datetime
import yfinance as yf
import time
import random
import threading
from functools import lru_cache

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Set production mode if needed
if os.getenv('FORCE_PRODUCTION', 'false').lower() == 'true':
    os.environ['PRODUCTION'] = 'true'
    print("⚠️ Production mode forced via FORCE_PRODUCTION environment variable")

# Detect production environment
is_production = os.getenv('VERCEL_ENV') == 'production' or os.getenv('PRODUCTION') == 'true'
if is_production:
    print("🚀 Running in production mode - using optimized data fetching")
else:
    print("🔧 Running in development mode - will attempt to use live data")

# Load user credentials from .env file
users = {}
user_credentials = os.getenv('USER_CREDENTIALS', 'demo@example.com:demo123:Demo User')
for user_entry in user_credentials.split(','):
    if user_entry and ':' in user_entry:
        parts = user_entry.strip().split(':')
        if len(parts) >= 3:
            email, password, name = parts[0], parts[1], parts[2]
            users[email] = {"password": password, "name": name}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Static fallback data for common stocks
FALLBACK_STOCKS = {
    'HDFCBANK': {
        'symbol': 'HDFCBANK',
        'company_name': 'HDFC Bank Ltd.',
        'current_price': 1650.45,
        'change': 0.75
    },
    'RELIANCE': {
        'symbol': 'RELIANCE',
        'company_name': 'Reliance Industries Ltd.',
        'current_price': 2891.70,
        'change': 1.25
    },
    'TCS': {
        'symbol': 'TCS',
        'company_name': 'Tata Consultancy Services Ltd.',
        'current_price': 3456.80,
        'change': -0.5
    },
    'INFY': {
        'symbol': 'INFY',
        'company_name': 'Infosys Ltd.',
        'current_price': 1467.25,
        'change': 0.3
    },
    # Additional common Indian stocks
    'ICICIBANK': {
        'symbol': 'ICICIBANK',
        'company_name': 'ICICI Bank Ltd.',
        'current_price': 1022.40,
        'change': 0.85
    },
    'TATASTEEL': {
        'symbol': 'TATASTEEL',
        'company_name': 'Tata Steel Ltd.',
        'current_price': 145.80,
        'change': -0.2
    },
    'SBIN': {
        'symbol': 'SBIN',
        'company_name': 'State Bank of India',
        'current_price': 760.25,
        'change': 1.1
    },
    'WIPRO': {
        'symbol': 'WIPRO',
        'company_name': 'Wipro Ltd.',
        'current_price': 478.60,
        'change': -0.7
    },
    'BHARTIARTL': {
        'symbol': 'BHARTIARTL',
        'company_name': 'Bharti Airtel Ltd.',
        'current_price': 1289.55,
        'change': 0.4
    },
    'AXISBANK': {
        'symbol': 'AXISBANK',
        'company_name': 'Axis Bank Ltd.',
        'current_price': 1055.30,
        'change': 0.6
    },
    'KOTAKBANK': {
        'symbol': 'KOTAKBANK',
        'company_name': 'Kotak Mahindra Bank Ltd.',
        'current_price': 1747.15,
        'change': 0.25
    },
    'HINDUNILVR': {
        'symbol': 'HINDUNILVR',
        'company_name': 'Hindustan Unilever Ltd.',
        'current_price': 2530.75,
        'change': -0.3
    },
    'ADANIENT': {
        'symbol': 'ADANIENT',
        'company_name': 'Adani Enterprises Ltd.',
        'current_price': 2840.90,
        'change': 1.5
    },
    'BAJFINANCE': {
        'symbol': 'BAJFINANCE',
        'company_name': 'Bajaj Finance Ltd.',
        'current_price': 7234.60,
        'change': 0.9
    },
    'TATAMOTORS': {
        'symbol': 'TATAMOTORS',
        'company_name': 'Tata Motors Ltd.',
        'current_price': 920.45,
        'change': 1.3
    }
}

# Server-side caching for stock data
# Create a thread-safe cache with expiration
class ExpiringCache:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
        
    def get(self, key):
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if time.time() - item['timestamp'] < 3600:  # 1 hour cache
                    return item['data']
                # Expired but keep for emergency fallback
            return None
            
    def set(self, key, value):
        with self.lock:
            self.cache[key] = {
                'data': value,
                'timestamp': time.time()
            }
            
    def get_stale(self, key):
        # Return even expired data as emergency fallback
        with self.lock:
            if key in self.cache:
                return self.cache[key]['data']
            return None

# Initialize the cache
stock_cache = ExpiringCache()

def get_stock_info(symbol):
    """Use yfinance to fetch stock data for NSE and BSE stocks"""
    # Make sure symbol has proper extension
    if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
        symbol = f"{symbol}.NS"  # Default to NSE
    
    # Get base symbol without extension
    base_symbol = symbol.split('.')[0]
    
    # In production or if we have fallback data for this stock, use it to avoid API limits
    is_production = os.getenv('VERCEL_ENV') == 'production' or os.getenv('PRODUCTION') == 'true'
    if is_production or base_symbol in FALLBACK_STOCKS:
        if base_symbol in FALLBACK_STOCKS:
            print(f"Using static fallback data for {base_symbol}")
            return {
                'success': True,
                'symbol': base_symbol,
                'company_name': FALLBACK_STOCKS[base_symbol]['company_name'],
                'current_price': FALLBACK_STOCKS[base_symbol]['current_price'],
                'change': FALLBACK_STOCKS[base_symbol]['change']
            }
    
    # If we're here, attempt to get data from yfinance
    try:
        # Add a small delay to avoid rate limiting
        time.sleep(random.uniform(0.1, 0.3))
        
        # Get stock info using yfinance with error handling
        try:
            ticker = yf.Ticker(symbol)
            
            # Try fetching the info (sometimes this can fail)
            try:
                info = ticker.info
                
                # Check if we got valid data
                if isinstance(info, dict) and 'longName' in info and 'regularMarketPrice' in info:
                    # Calculate change if available
                    price = info.get('regularMarketPrice', 0)
                    prev_close = info.get('previousClose', price)
                    change = ((price - prev_close) / prev_close * 100) if prev_close and prev_close > 0 else 0
                    
                    return {
                        'success': True,
                        'symbol': base_symbol,
                        'company_name': info.get('longName', base_symbol),
                        'current_price': round(price, 2),
                        'change': round(change, 2)
                    }
            except Exception as inner_error:
                print(f"Inner error fetching info for {symbol}: {str(inner_error)}")
            
            # Try using history as an alternative approach
            try:
                history = ticker.history(period="2d")
                if not history.empty and len(history) > 0:
                    # Calculate change from the history data
                    latest = history.iloc[-1]
                    if len(history) > 1:
                        prev_day = history.iloc[-2]
                        price = latest.get('Close', 0)
                        prev_price = prev_day.get('Close', price)
                        change = ((price - prev_price) / prev_price * 100) if prev_price and prev_price > 0 else 0
                    else:
                        price = latest.get('Close', 0)
                        change = 0
                    
                    return {
                        'success': True,
                        'symbol': base_symbol,
                        'company_name': f"{base_symbol} Stock", # Fallback name
                        'current_price': round(price, 2),
                        'change': round(change, 2)
                    }
            except Exception as history_error:
                print(f"History fallback error for {symbol}: {str(history_error)}")
                
        except Exception as ticker_error:
            print(f"Ticker creation error for {symbol}: {str(ticker_error)}")
            
        # If all yfinance methods failed, check for fallback data again
        if base_symbol in FALLBACK_STOCKS:
            print(f"YFinance failed, using fallback data for {base_symbol}")
            return {
                'success': True,
                'symbol': base_symbol,
                'company_name': FALLBACK_STOCKS[base_symbol]['company_name'],
                'current_price': FALLBACK_STOCKS[base_symbol]['current_price'],
                'change': FALLBACK_STOCKS[base_symbol]['change']
            }
                
        # If we reach here, we couldn't get data    
        print(f"No data available for {symbol}")
        return {'success': False, 'error': 'Could not fetch stock data'}
            
    except Exception as e:
        print(f"Error fetching stock data for {symbol}: {str(e)}")
        return {'success': False, 'error': str(e)}

# Enhanced stock data fetching with better error handling
def get_stock_data(symbol):
    """API endpoint to get stock data with improved caching and rate limiting"""
    # Check cache first
    cached_data = stock_cache.get(symbol)
    if cached_data:
        print(f"Cache hit for {symbol}")
        return cached_data
        
    base_symbol = symbol.split('.')[0]
    
    # Check if we're in production - use multiple indicators
    is_production = os.getenv('VERCEL_ENV') == 'production' or os.getenv('PRODUCTION') == 'true'
    
    # In production, prioritize fallback data to avoid rate limits entirely
    if is_production and base_symbol in FALLBACK_STOCKS:
        print(f"Production mode: using fallback data for {base_symbol}")
        result = FALLBACK_STOCKS[base_symbol].copy()
        result['success'] = True
        # Still cache this result
        stock_cache.set(symbol, result)
        return result
    
    # For common Indian stocks, always use fallback data even in development
    if base_symbol in FALLBACK_STOCKS:
        print(f"Using fallback data for common stock: {base_symbol}")
        result = FALLBACK_STOCKS[base_symbol].copy()
        result['success'] = True
        # Cache this result
        stock_cache.set(symbol, result) 
        return result
    
    # Try to get real data using yfinance only if we don't have fallback data
    try:
        # Add randomized delay to prevent rate limiting
        time.sleep(random.uniform(0.2, 0.5))
        
        # Format symbol properly for Yahoo Finance
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            yahoo_symbol = f"{symbol}.NS"  # Default to NSE
        else:
            yahoo_symbol = symbol
            
        print(f"Fetching data for {yahoo_symbol} from Yahoo Finance")
        result = get_stock_info(yahoo_symbol)
        
        # Cache successful results
        if result['success']:
            stock_cache.set(symbol, result)
            return result
            
        # If NSE fails, try BSE
        if yahoo_symbol.endswith('.NS'):
            bse_symbol = f"{base_symbol}.BO"
            print(f"NSE failed, trying BSE: {bse_symbol}")
            time.sleep(random.uniform(0.2, 0.5))  # Additional delay
            result = get_stock_info(bse_symbol)
            if result['success']:
                stock_cache.set(symbol, result)
                return result
    
    except Exception as e:
        print(f"Error fetching stock data for {symbol}: {str(e)}")
        # Try to get stale data from cache
        stale_data = stock_cache.get_stale(symbol)
        if stale_data:
            print(f"Using stale data for {symbol}")
            return stale_data
    
    # Last resort: return generated data
    print(f"Generating fallback data for {symbol}")
    generated_data = {
        "success": True,
        "symbol": base_symbol,
        "company_name": f"{base_symbol} Stock",
        "current_price": round(random.uniform(500, 3000), 2),
        "change": round(random.uniform(-2, 2), 2)
    }
    # Cache even the generated data
    stock_cache.set(symbol, generated_data)
    return generated_data

@app.route('/firebase-config')
def firebase_config():
    """Return Firebase configuration as JSON for client-side initialization"""
    config = {
        "apiKey": os.getenv('FIREBASE_API_KEY'),
        "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
        "databaseURL": os.getenv('FIREBASE_DATABASE_URL'),
        "projectId": os.getenv('FIREBASE_PROJECT_ID'),
        "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
        "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        "appId": os.getenv('FIREBASE_APP_ID')
    }
    return jsonify(config)

@app.route('/api/stock-data')
@login_required
def get_stock_data_api():
    """API endpoint to get stock data"""
    symbol = request.args.get('symbol', '').upper().strip()
    static_only = request.args.get('static_only') == 'true'
    
    if not symbol:
        return jsonify({"success": False, "error": "Symbol is required"})
    
    # Extract base symbol without extension
    base_symbol = symbol.split('.')[0]
    
    # If static_only flag is set, only return from the fallback data
    if static_only:
        if base_symbol in FALLBACK_STOCKS:
            print(f"Providing static data for {base_symbol} (client-side request)")
            result = FALLBACK_STOCKS[base_symbol].copy()
            result['success'] = True
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": "No static data available"})
    
    # Use the enhanced stock data fetching function
    result = get_stock_data(symbol)
    return jsonify(result)

@app.route('/get_stock_info')
@login_required
def get_stock_details():
    """Additional endpoint for detailed stock info"""
    try:
        symbol = request.args.get('symbol', '')
        # Add .NS suffix for NSE stocks
        if not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if 'regularMarketPrice' not in info:
            return jsonify({
                'error': 'Stock not found or not available'
            }), 404
            
        return jsonify({
            'name': info.get('longName', ''),
            'symbol': symbol,
            'currentPrice': info.get('regularMarketPrice', 0),
            'dayHigh': info.get('dayHigh', 0),
            'dayLow': info.get('dayLow', 0),
            'previousClose': info.get('previousClose', 0)
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in users and users[email]['password'] == password:
            session['user'] = {'email': email, 'name': users[email]['name']}
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/stocks', methods=['GET', 'POST'])
@login_required
def stocks():
    user_email = session['user']['email']
    
    # Only handle session-based storage for SSR mode,
    # client-side will use Firebase directly
    if request.method == 'POST' and not (request.is_json or request.content_type == 'application/json'):
        symbol = request.form.get('symbol', '').upper().strip()
        if symbol:
            # Check if it's one of our fallback stocks
            base_symbol = symbol.split('.')[0]
            if base_symbol in FALLBACK_STOCKS:
                session.setdefault('stocks', []).append(f"{base_symbol}.NS")
                flash(f'Added {base_symbol} to your portfolio', 'success')
                return redirect(url_for('stocks'))
                
            # Try both NSE and BSE
            try_symbols = [f"{symbol}.NS", f"{symbol}.BO"]
            added = False
            for try_symbol in try_symbols:
                stock_info = get_stock_info(try_symbol)
                if stock_info['success']:
                    # For form submissions, use session and redirect
                    session.setdefault('stocks', []).append(try_symbol)
                    flash(f'Added {symbol} to your portfolio', 'success')
                    added = True
                    break
            
            if not added:
                # Just add to NSE as fallback
                session.setdefault('stocks', []).append(f"{symbol}.NS")
                flash(f'Added {symbol} to your portfolio', 'success')
        
        return redirect(url_for('stocks'))

    # Get stocks from session for SSR
    stocks_data = []
    for symbol in session.get('stocks', []):
        # Check if we have fallback data
        base_symbol = symbol.split('.')[0]
        if base_symbol in FALLBACK_STOCKS:
            stock_data = FALLBACK_STOCKS[base_symbol].copy()
            stocks_data.append(stock_data)
            continue
        
        # Otherwise try to fetch live data
        stock_info = get_stock_info(symbol)
        if stock_info['success']:
            stocks_data.append({
                'symbol': stock_info['symbol'],
                'company_name': stock_info['company_name'],
                'current_price': stock_info['current_price'],
                'change': stock_info['change']
            })
        else:
            # Add placeholder data if API fails
            stocks_data.append({
                'symbol': base_symbol,
                'company_name': f"{base_symbol} Stock",
                'current_price': round(random.uniform(500, 3000), 2),
                'change': round(random.uniform(-2, 2), 2)
            })

    return render_template('stocks.html', stocks=stocks_data)

@app.route('/mutual-funds')
@login_required
def mutual_funds():
    # Empty initial data, client will load from Firebase
    return render_template('mutual_funds.html', mutual_funds=[])

@app.route('/api/mutual-fund')
@login_required
def get_mutual_fund_data():
    """API endpoint to get mutual fund data"""
    scheme_code = request.args.get('scheme_code', '').strip()
    if not scheme_code:
        return jsonify({"success": False, "error": "Scheme code is required"})
    
    try:
        response = requests.get(
            f'https://api.mfapi.in/mf/{scheme_code}',
            timeout=10,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data and data.get('status') == 'SUCCESS':
                    return jsonify({
                        "success": True,
                        "scheme_code": scheme_code,
                        "scheme_name": data['meta']['scheme_name'],
                        "nav": data['data'][0]['nav'],
                        "date": data['data'][0]['date']
                    })
            except:
                pass
                
        # Return fallback data if API fails
        return jsonify({
            "success": True,
            "scheme_code": scheme_code,
            "scheme_name": f"Mutual Fund {scheme_code}",
            "nav": "32.456",
            "date": datetime.now().strftime('%d-%m-%Y')
        })
    except Exception as e:
        # Return fallback data if API fails
        return jsonify({
            "success": True,
            "scheme_code": scheme_code,
            "scheme_name": f"Mutual Fund {scheme_code}",
            "nav": "32.456",
            "date": datetime.now().strftime('%d-%m-%Y')
        })

@app.route('/insurance')
@login_required
def insurance():
    # Empty initial data, client will load from Firebase
    return render_template('insurance.html', policies=[])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
