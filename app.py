import math
import os
from datetime import datetime # Import datetime

from scipy.stats import norm
from flask import Flask, request, render_template, flash, redirect, url_for, abort, jsonify # Import jsonify
from models import db, OptionData, Strategy, StrategyLeg, populate_initial_data # Import new models

app = Flask(__name__)

# Configuration
# Use instance folder for the database file
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app.config['SECRET_KEY'] = 'your secret key here - change me!' # Important for flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "options.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable tracking modifications

# Initialize extensions
db.init_app(app) # Bind db to the app

# -------------------------------------
# Command to initialize DB
# -------------------------------------
# Run this once from the terminal: flask init-db
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context(): # Ensure we are within application context
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database tables created.")
        populate_initial_data() # Populate after creating tables
    print('Initialized the database.')

# -------------------------------------
# Black-Scholes Calculation Function (Keep as before)
# -------------------------------------
def black_scholes_merton(S, K, T_days, r_pct, sigma_pct, option_type='call', q_pct=0):
    """Calculates the Black-Scholes-Merton option price."""
    try:
        if T_days <= 0 or sigma_pct <= 0:
            raise ValueError("Days to expiry and volatility must be positive.")
        T = T_days / 365.0
        r = r_pct / 100.0
        sigma = sigma_pct / 100.0
        q = q_pct / 100.0
        
        sigma_sqrt_T = sigma * math.sqrt(T)
        if sigma_sqrt_T == 0:
             raise ValueError("Volatility or Time to Expiry results in zero denominator component.")
             
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / sigma_sqrt_T
        d2 = d1 - sigma_sqrt_T

        if option_type == 'call':
            price = (S * math.exp(-q * T) * norm.cdf(d1)) - (K * math.exp(-r * T) * norm.cdf(d2))
        elif option_type == 'put':
            price = (K * math.exp(-r * T) * norm.cdf(-d2)) - (S * math.exp(-q * T) * norm.cdf(-d1))
        else:
            raise ValueError("Invalid option type. Use 'call' or 'put'.")
        return price
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as e:
        print(f"Error in calculation: {e}")
        raise ValueError(f"Calculation Error: {e}")

# -------------------------------------
# Flask Routes
# -------------------------------------
@app.route('/')
def index():
    """Renders the main calculator form."""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Handles calculator form submission."""
    result = None
    error = None
    inputs = {}
    try:
        inputs['stock_price'] = float(request.form['stock_price'])
        inputs['strike_price'] = float(request.form['strike_price'])
        inputs['days_to_expiry'] = int(request.form['days_to_expiry'])
        inputs['interest_rate'] = float(request.form['interest_rate'])
        inputs['volatility'] = float(request.form['volatility'])
        inputs['option_type'] = request.form['option_type']
        result = black_scholes_merton(
            S=inputs['stock_price'], K=inputs['strike_price'], T_days=inputs['days_to_expiry'],
            r_pct=inputs['interest_rate'], sigma_pct=inputs['volatility'],
            option_type=inputs['option_type']
        )
    except ValueError as e:
        error = f"Invalid input or calculation error: {e}"
    except Exception as e:
        error = f"An unexpected error occurred: {e}"
        print(f"Unexpected error: {e}")
    return render_template('index.html', result=result, error=error, inputs=inputs)

# --- New Routes for Listing and Editing ---

@app.route('/options')
def list_options():
    """Displays all options from the database."""
    options = OptionData.query.order_by(OptionData.option_type, OptionData.strike_price).all()
    return render_template('list_options.html', options=options)

@app.route('/edit_option/<int:option_id>', methods=['GET', 'POST'])
def edit_option(option_id):
    """Handles editing a specific option."""
    # Fetch the option or return 404 if not found
    option = db.session.get(OptionData, option_id) # Use db.session.get for primary key lookup
    if option is None:
        abort(404) # Not found error

    if request.method == 'POST':
        try:
            # Update fields from form data
            option.market_price = float(request.form['market_price'])
            option.theoretical_value = float(request.form['theoretical_value'])
            option.delta = float(request.form['delta'])
            option.gamma = float(request.form['gamma'])
            option.theta = float(request.form['theta'])
            option.vega = float(request.form['vega'])
            option.rho = float(request.form['rho'])
            
            db.session.commit()
            flash(f'Option {option.option_type.upper()} K={option.strike_price} updated successfully!', 'success')
            return redirect(url_for('list_options'))
        except ValueError:
            db.session.rollback() # Rollback changes if there's an error
            flash('Invalid input. Please ensure all fields are numbers.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            print(f"Error updating option {option_id}: {e}")
            
        # If POST fails (e.g., validation error), re-render form with current data
        return render_template('edit_option.html', option=option)

    # GET request: Show the edit form
    return render_template('edit_option.html', option=option)

@app.route('/api/save_strategy', methods=['POST'])
def save_strategy():
    """API endpoint to receive strategy data from frontend and save to DB."""
    if not request.is_json:
        return jsonify({"success": False, "message": "Request must be JSON"}), 400

    data = request.get_json()
    strategy_legs_data = data.get('strategy') # Expect {'strategy': [legs...]}

    if not strategy_legs_data or not isinstance(strategy_legs_data, list) or len(strategy_legs_data) == 0:
        return jsonify({"success": False, "message": "Missing or invalid 'strategy' data in request body"}), 400

    try:
        # Create the main strategy record
        new_strategy = Strategy() # timestamp is added by default
        db.session.add(new_strategy)
        db.session.flush() # Assigns an ID to new_strategy without committing yet

        # Process each leg
        for leg_data in strategy_legs_data:
            # Basic validation of leg data structure
            leg_type = leg_data.get('type')
            quantity = leg_data.get('quantity')
            direction = leg_data.get('direction')

            if not all([leg_type, quantity, direction]):
                 raise ValueError("Invalid leg data: missing type, quantity, or direction")
            if leg_type not in ['call', 'put', 'underlying']:
                 raise ValueError(f"Invalid leg type: {leg_type}")
            if direction not in ['long', 'short']:
                 raise ValueError(f"Invalid leg direction: {direction}")
            if not isinstance(quantity, int) or quantity <= 0:
                 raise ValueError(f"Invalid quantity: {quantity}")

            # Create StrategyLeg record
            new_leg = StrategyLeg(
                strategy_id = new_strategy.id,
                leg_type = leg_type,
                quantity = quantity,
                direction = direction
            )

            # Add option-specific details if not underlying
            if leg_type != 'underlying':
                option_id = leg_data.get('id')
                strike = leg_data.get('strike')
                if option_id is None or strike is None:
                     raise ValueError(f"Missing 'id' or 'strike' for option leg: {leg_data}")
                
                # Optional: Verify the option_id exists in OptionData
                option_ref = db.session.get(OptionData, option_id)
                if option_ref is None:
                     raise ValueError(f"OptionData with ID {option_id} not found in database.")
                
                new_leg.option_data_id = option_id
                new_leg.strike_price = strike # Store strike for convenience

            db.session.add(new_leg)

        # If all legs processed without error, commit the transaction
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Strategy saved successfully", 
            "strategy_id": new_strategy.id
        }), 201 # 201 Created status code

    except ValueError as ve:
        db.session.rollback() # Rollback transaction on validation error
        print(f"Validation Error saving strategy: {ve}")
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        db.session.rollback() # Rollback transaction on other errors
        print(f"Error saving strategy: {e}") # Log the full error for debugging
        return jsonify({"success": False, "message": "An internal error occurred while saving the strategy."}), 500


# -------------------------------------
# Run the App
# -------------------------------------
if __name__ == '__main__':
    # Optional: Create tables on first run if db doesn't exist
    # For robust setup, use 'flask init-db' command instead.
    # with app.app_context():
    #     db_file = os.path.join(instance_path, "options.db")
    #     if not os.path.exists(db_file):
    #          print("Database file not found, creating...")
    #          db.create_all()
    #          print("Database tables created.")
    #          populate_initial_data() # Also populate if creating
             
    app.run(debug=True)