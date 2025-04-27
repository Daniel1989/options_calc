import math
import os
from datetime import datetime # Import datetime
import json
import dotenv

from scipy.stats import norm
from flask import Flask, request, render_template, flash, redirect, url_for, abort, jsonify # Import jsonify
from models import db, OptionData, Strategy, StrategyLeg, populate_initial_data # Import new models
from strategy_defs import STRATEGY_DETAILS # I
# app.py (or a new utils.py)
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError # Import specific errors
import traceback
# --- Initialize OpenAI Client ---
# Best practice: Initialize once if possible. 

dotenv.load_dotenv()
# Ensure OPENAI_API_KEY is set as an environment variable
try:
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL')) # Set a timeout (e.g., 20 seconds)
except Exception as e:
    print(f"Warning: Failed to initialize OpenAI client (is API key set?): {e}")
    openai_client = None

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
    
def identify_strategy_with_llm(legs):
    """
    Uses an LLM (GPT) to identify strategy details as a fallback.

    Args:
        legs (list): A list of StrategyLeg objects.

    Returns:
        dict: A dictionary with strategy details, or a default error dictionary.
    """
    if openai_client is None:
        print("LLM identification skipped: OpenAI client not available.")
        return {
            "name_en": "LLM Disabled",
            "name_cn": "LLM未启用",
            "description": "无法连接到语言模型服务。",
            "example": "N/A",
            "scenarios": "N/A"
        }

    if not legs:
        return STRATEGY_DETAILS.get("Empty Strategy") # Use existing details

    # 1. Format Legs for Prompt
    prompt_legs = []
    for leg in legs:
        direction = leg.direction.upper()
        qty = int(leg.quantity) # Assume integer quantity for display
        if leg.leg_type == 'underlying':
            prompt_legs.append(f"  - {direction} {qty * 100} Underlying Shares") # Assuming qty is units of 100
        elif leg.option:
            option_type = leg.option.option_type.capitalize()
            strike = leg.option.strike_price
            prompt_legs.append(f"  - {direction} {qty} {option_type} K={strike}")
        else:
             prompt_legs.append(f"  - Invalid/Unknown Leg Data")

    legs_string = "\n".join(prompt_legs)

    # 2. Craft Prompt
    prompt = f"""You are an expert options trading strategist analyzing strategy components.
Your task is to identify the most common, standard name for the strategy defined by the legs below and provide details in Chinese.

Strategy Legs:
{legs_string}

Based ONLY on these legs, identify the most common standard name for this strategy. If no standard name fits well, classify it as "自定义策略" (Custom Strategy) or "混合策略" (Mixed Strategy) as appropriate.

Provide your answer ONLY in the following JSON format, with no other text, comments, or introductions:
{{
  "name_cn": "策略中文名",
  "description": "策略的详细中文描述。",
  "example": "一个典型的中文策略示例，描述结构而非精确数字。",
  "scenarios": "该策略适用的市场情景和预期（中文）。"
}}"""

    # 3. Call LLM API
    try:
        print(f"Calling OpenAI API for strategy identification...") # Log the attempt
        response = openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME"), # Or "gpt-4" for potentially better results (more expensive)
            messages=[
                {"role": "system", "content": "You are an expert options trading strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Lower temperature for more deterministic results
            max_tokens=300, # Limit response length
            response_format={"type": "json_object"} # Request JSON output if model supports it
        )
        
        content = response.choices[0].message.content
        print(f"OpenAI Response Content: {content}") # Log the raw response

        # 4. Parse Response
        try:
            details = json.loads(content)
            # Basic validation of parsed structure
            if all(k in details for k in ["name_cn", "description", "example", "scenarios"]):
                details["name_en"] = "LLM Identified" # Mark as LLM identified
                return details
            else:
                print("Warning: LLM response missing expected keys.")
                raise ValueError("Missing keys in LLM response")
        except (json.JSONDecodeError, ValueError) as json_e:
            print(f"Error parsing LLM JSON response: {json_e}\nRaw content: {content}")
            # Fallback if JSON parsing fails
            return {
                "name_en": "LLM Parse Error",
                "name_cn": "LLM解析错误",
                "description": f"无法解析语言模型返回的响应: {content}",
                "example": "N/A",
                "scenarios": "N/A"
            }

    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_e:
         print(f"OpenAI API Error: {api_e}")
         return {
            "name_en": "LLM API Error",
            "name_cn": "LLM接口错误",
            "description": f"调用语言模型服务时出错: {api_e}",
            "example": "N/A",
            "scenarios": "N/A"
         }
    except Exception as e:
        print(f"An unexpected error occurred during LLM call: {e}")
        return {
            "name_en": "LLM Unknown Error",
            "name_cn": "LLM未知错误",
            "description": f"处理语言模型调用时发生未知错误: {e}",
            "example": "N/A",
            "scenarios": "N/A"
        }
    
def identify_strategy_type(legs, use_llm_fallback=True): # Add flag
    """
    Attempts to identify the common name of a strategy based on its legs.
    Uses rule-based approach first, then optionally falls back to LLM.

    Args:
        legs (list): A list of StrategyLeg objects associated with one strategy.
        use_llm_fallback (bool): Whether to call the LLM if rule-based fails.

    Returns:
        dict: A dictionary containing strategy details.
    """
    strategy_name = "Unknown Strategy" # Default rule-based outcome

    # --- Rule-Based Identification Logic ---
    if not legs:
        strategy_name = "Empty Strategy"
    else:
        # --- Data Preparation (DEFINITIONS WERE MISSING HERE) ---
        underlying_legs = [leg for leg in legs if leg.leg_type == 'underlying']
        option_legs = [leg for leg in legs if leg.option is not None] # Ensure option data exists
        
        # Sort option legs primarily by type (call then put), then by strike
        option_legs.sort(key=lambda leg: (leg.option.option_type, leg.option.strike_price))

        # <<< ADD THESE DEFINITIONS BACK >>>
        calls = [leg for leg in option_legs if leg.option.option_type == 'call']
        puts = [leg for leg in option_legs if leg.option.option_type == 'put']

        long_calls = [leg for leg in calls if leg.direction == 'long']
        short_calls = [leg for leg in calls if leg.direction == 'short']
        long_puts = [leg for leg in puts if leg.direction == 'long']
        short_puts = [leg for leg in puts if leg.direction == 'short']
        long_underlying = [leg for leg in underlying_legs if leg.direction == 'long']
        short_underlying = [leg for leg in underlying_legs if leg.direction == 'short'] # Less common
        # <<< END OF ADDED DEFINITIONS >>>

        num_legs = len(legs)
        num_option_legs = len(option_legs)
        num_underlying_legs = len(underlying_legs)

        # --- Identification Rules (Now variables are defined) ---
        # == Single Leg Strategies ==
        if num_legs == 1:
            leg = legs[0]
            if leg.leg_type == 'underlying':
                strategy_name = f"{leg.direction.capitalize()} Underlying"
            elif leg.option:
                strategy_name = f"{leg.direction.capitalize()} {leg.option.option_type.capitalize()}"

        # == Two Leg Strategies ==
        elif num_legs == 2:
             if num_option_legs == 2 and num_underlying_legs == 0:
                 leg1, leg2 = option_legs[0], option_legs[1]
                 same_qty = leg1.quantity == leg2.quantity

                 # Straddle/Strangle (Now 'calls' and 'puts' are defined)
                 if len(calls) == 1 and len(puts) == 1 and same_qty:
                     call_leg, put_leg = calls[0], puts[0]
                     if call_leg.direction == 'long' and put_leg.direction == 'long':
                         strategy_name = "Long Straddle" if call_leg.option.strike_price == put_leg.option.strike_price else "Long Strangle"
                     elif call_leg.direction == 'short' and put_leg.direction == 'short':
                         strategy_name = "Short Straddle" if call_leg.option.strike_price == put_leg.option.strike_price else "Short Strangle"

                 # Spreads (Now 'long_calls', 'short_calls', etc. are defined)
                 elif len(calls) == 2 and same_qty and len(long_calls) == 1:
                     long_c, short_c = long_calls[0], short_calls[0]
                     strategy_name = "Bull Call Spread" if long_c.option.strike_price < short_c.option.strike_price else "Bear Call Spread"
                 elif len(puts) == 2 and same_qty and len(long_puts) == 1:
                     long_p, short_p = long_puts[0], short_puts[0]
                     strategy_name = "Bear Put Spread" if long_p.option.strike_price > short_p.option.strike_price else "Bull Put Spread"
                 # Add basic Ratio Spread label if needed (using len(calls)/len(puts) and not same_qty)
                 elif not same_qty:
                     if len(calls) == 2: strategy_name = "Call Ratio Spread"
                     elif len(puts) == 2: strategy_name = "Put Ratio Spread"


             elif num_underlying_legs == 1 and num_option_legs == 1:
                  u_leg, o_leg = underlying_legs[0], option_legs[0]
                  if u_leg.direction == 'long' and len(long_underlying) == 1: # Ensure it's the long underlying leg
                       if o_leg.option.option_type == 'call' and o_leg.direction == 'short':
                           strategy_name = "Covered Call"
                       elif o_leg.option.option_type == 'put' and o_leg.direction == 'long':
                           strategy_name = "Protective Put"

        # == Three Leg Strategies ==
        elif num_legs == 3 and num_option_legs == 3 and num_underlying_legs == 0:
            if len(calls) == 3: # Basic Butterfly Check (uses long_calls, short_calls)
                legs_by_strike = sorted(calls, key=lambda l: l.option.strike_price)
                if (len(long_calls) == 2 and len(short_calls) == 1 and
                    legs_by_strike[0].direction == 'long' and legs_by_strike[1].direction == 'short' and legs_by_strike[2].direction == 'long' and
                    legs_by_strike[0].quantity * 2 == legs_by_strike[1].quantity and legs_by_strike[2].quantity * 2 == legs_by_strike[1].quantity):
                     strategy_name = "Long Call Butterfly"
            # Add checks for Put Butterfly etc. if needed

        # == Four Leg Strategies ==
        elif num_legs == 4 and num_option_legs == 4 and num_underlying_legs == 0:
             if len(long_puts) == 1 and len(short_puts) == 1 and len(short_calls) == 1 and len(long_calls) == 1: # Iron Condor check
                 quantities = {leg.quantity for leg in option_legs}
                 if len(quantities) == 1: # Check for same quantities
                     lp_k = long_puts[0].option.strike_price
                     sp_k = short_puts[0].option.strike_price
                     sc_k = short_calls[0].option.strike_price
                     lc_k = long_calls[0].option.strike_price
                     if lp_k < sp_k < sc_k < lc_k:
                         strategy_name = "Iron Condor"

        # --- Fallback Labels (if strategy_name is still "Unknown Strategy") ---
        if strategy_name == "Unknown Strategy":
             if num_underlying_legs > 0 and num_option_legs > 0:
                 strategy_name = "Mixed Underlying/Option Strategy"
             elif num_option_legs > 1:
                 strategy_name = "Custom Option Spread"
             elif num_underlying_legs > 1:
                 strategy_name = "Custom Underlying Strategy"


    # --- Get Details or Use LLM Fallback (same as before) ---
    details = STRATEGY_DETAILS.get(strategy_name)
    should_fallback = (strategy_name in ["Unknown Strategy", "Custom Option Spread", "Custom Underlying Strategy", "Mixed Underlying/Option Strategy"] or details is None)

    if use_llm_fallback and should_fallback:
        # ... (LLM fallback logic remains the same) ...
        print(f"Rule-based identification resulted in '{strategy_name}'. Attempting LLM fallback...")
        llm_details = identify_strategy_with_llm(legs)
        if "name_cn" in llm_details and not llm_details["name_cn"].startswith("LLM"):
             print(f"Using LLM result: {llm_details.get('name_cn')}")
             llm_details['name_en'] = "LLM Identified: " + llm_details.get('name_cn', 'Unknown')
             return llm_details
        else:
             print("LLM fallback failed or returned error, using rule-based default.")
             # Return original rule-based default/unknown details
             fallback_details = STRATEGY_DETAILS.get(strategy_name, STRATEGY_DETAILS["Unknown Strategy"])
             fallback_details['name_en'] = strategy_name # Ensure English name is set
             return fallback_details
    else:
        # Return the details found via rules
        result_details = STRATEGY_DETAILS.get(strategy_name, STRATEGY_DETAILS["Unknown Strategy"])
        result_details['name_en'] = strategy_name # Ensure English name is set
        return result_details
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



@app.route('/strategies')
def list_strategies():
    """Fetches strategies, calculates Greeks, and displays them."""
    try:
        strategies = Strategy.query.order_by(Strategy.created_at.desc()).all()
        strategies_data = []

        for strategy in strategies:
            net_delta = 0.0
            net_gamma = 0.0
            net_theta = 0.0
            net_vega = 0.0
            net_rho = 0.0
            legs_details = []
            net_theoretical_value = 0.0 # <<< Initialize Net Theoretical Value
            calculation_possible = True # Flag to track if all data was available

            if not strategy.legs: # Handle strategies with no legs (shouldn't happen with current save logic, but good check)
                calculation_possible = False
            for item in strategy.legs:
                if item.leg_type != 'underlying':
                    option_data = db.session.get(OptionData, item.option_data_id)
                    item.option = option_data
                else:
                    item.option = None
            
            strategy_info = identify_strategy_type(strategy.legs, use_llm_fallback=True)
            for leg in strategy.legs:
                # Determine multiplier based on direction
                multiplier = 1 if leg.direction == 'long' else -1
                # --- Handle based on leg_type ---
                if leg.leg_type == 'underlying':
                    # Assuming leg.quantity for underlying means "units of 100 shares"
                    qty_shares = leg.quantity # Total shares
                    
                    # Delta of 1 per share
                    leg_delta = qty_shares * multiplier 
                    leg_gamma = 0.0
                    leg_theta = 0.0
                    leg_vega = 0.0
                    leg_rho = 0.0 # Ignoring financing cost rho for simplicity here

                    legs_details.append(f"{int(qty_shares)} x {leg.direction.upper()} Underlying Shares")
                    
                    # Add contributions
                    net_delta += leg_delta
                    # Others are 0

                elif leg.option:
                    option_data = db.session.get(OptionData, leg.option_data_id)
                    if option_data is None:
                        legs_details.append(f"{int(leg.quantity)} x {leg.direction.upper()} [Option ID {leg.option_data_id} NOT FOUND]")
                        calculation_possible = False
                        continue # Skip greek calculation for this leg

                    legs_details.append(f"{int(leg.quantity)} x {leg.direction.upper()} {option_data.option_type.capitalize()} K={option_data.strike_price}")
               # Check if theoretical value exists for calculation
                    o_theoretical = option_data.theoretical_value # <<< Get theoretical value
                    if o_theoretical is None:
                        calculation_possible = False # Can't calculate net theoretical if one leg is missing it
                    else:
                         # Add contribution to net theoretical value
                         net_theoretical_value += leg.quantity * multiplier * o_theoretical # <<< Calculate contribution
                    # Get Greeks, default to 0 if None
                    o_delta = option_data.delta if option_data.delta is not None else 0.0
                    o_gamma = option_data.gamma if option_data.gamma is not None else 0.0
                    o_theta = option_data.theta if option_data.theta is not None else 0.0
                    o_vega = option_data.vega if option_data.vega is not None else 0.0
                    o_rho = option_data.rho if option_data.rho is not None else 0.0
                    
                    # Calculate contributions (multiplier for direction, quantity for contracts)
                    leg_multiplier = leg.quantity * multiplier # Contracts * direction multiplier

                    net_delta += leg_multiplier * o_delta
                    net_gamma += leg_multiplier * o_gamma
                    # Theta sign flip for short options
                    net_theta += leg.quantity * (-o_theta if leg.direction == 'short' else o_theta) 
                    net_vega += leg_multiplier * o_vega
                    net_rho += leg_multiplier * o_rho
                
                else:
                     # Should not happen if data is saved correctly
                     legs_details.append(f"Unknown leg type for leg ID {leg.id}")
                     calculation_possible = False


            strategies_data.append({
                'id': strategy.id,
                'created_at': strategy.created_at,
                'legs_details': legs_details,
                'net_theoretical_value': net_theoretical_value if calculation_possible else None, # <<< Add to dict
                'calculation_possible': calculation_possible, # Pass flag to template
                'net_delta': net_delta if calculation_possible else None,
                'net_gamma': net_gamma if calculation_possible else None,
                'net_theta': net_theta if calculation_possible else None,
                'net_vega': net_vega if calculation_possible else None,
                'net_rho': net_rho if calculation_possible else None,
                'strategy_info': strategy_info, # <<< PASS THE WHOLE DICTIONARY
            })

        return render_template('list_strategies.html', strategies_data=strategies_data)

    except Exception as e:
        print(f"Error fetching or processing strategies: {e}")
        print(traceback.format_exc())
        # Render template with an error message (optional)
        flash(f"Error loading strategies: {e}", "danger")
        return render_template('list_strategies.html', strategies_data=[], error=str(e))


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