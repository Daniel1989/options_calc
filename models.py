from flask_sqlalchemy import SQLAlchemy
from datetime import datetime # Import datetime

# Initialize SQLAlchemy without binding it to an app yet
# This allows the models module to be imported before the app is created
db = SQLAlchemy() 

class OptionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strike_price = db.Column(db.Float, nullable=False)
    option_type = db.Column(db.String(4), nullable=False)  # 'call' or 'put'
    
    # Data from Image 1 (Allowing Null for flexibility if some data missing)
    market_price = db.Column(db.Float, nullable=True) 
    theoretical_value = db.Column(db.Float, nullable=True)
    delta = db.Column(db.Float, nullable=True)
    gamma = db.Column(db.Float, nullable=True)
    theta = db.Column(db.Float, nullable=True)
    vega = db.Column(db.Float, nullable=True)
    rho = db.Column(db.Float, nullable=True)

    strategy_legs = db.relationship('StrategyLeg', backref='option_data', lazy=True)

    # Represent how the option should be displayed
    def __repr__(self):
        return f"<OptionData {self.option_type.upper()} K={self.strike_price} ID={self.id}>"

# --- New Models ---
class Strategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Add user_id here if you implement user accounts later
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    
    # Relationship to legs
    legs = db.relationship('StrategyLeg', backref='strategy', lazy=True, cascade="all, delete-orphan") # Cascade delete legs if strategy is deleted

    def __repr__(self):
        return f"<Strategy ID={self.id} Created={self.created_at.strftime('%Y-%m-%d %H:%M:%S')}>"

class StrategyLeg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    
    leg_type = db.Column(db.String(10), nullable=False) # 'call', 'put', or 'underlying'
    quantity = db.Column(db.Integer, nullable=False)
    direction = db.Column(db.String(5), nullable=False) # 'long' or 'short'
    
    # Fields specific to options (nullable for underlying)
    option_data_id = db.Column(db.Integer, db.ForeignKey('option_data.id'), nullable=True) 
    strike_price = db.Column(db.Float, nullable=True) # Store strike redundantly or for underlying=null case

    def __repr__(self):
        details = f"Type={self.leg_type} Qty={self.quantity} Dir={self.direction}"
        if self.leg_type != 'underlying':
            details += f" OptionDataID={self.option_data_id} K={self.strike_price}"
        return f"<StrategyLeg ID={self.id} StrategyID={self.strategy_id} {details}>"
    
# Helper function to add initial data
def populate_initial_data():
    # Check if data already exists to avoid duplicates
    if OptionData.query.first() is not None:
        print("Database already contains data. Skipping population.")
        return

    print("Populating initial option data...")
    
    # Transcribe data from Image 1 carefully
    initial_options = [
        # June Calls
        {'strike_price': 90, 'option_type': 'call', 'market_price': 12.30, 'theoretical_value': 11.96, 'delta': 87, 'gamma': 2.0, 'theta': -0.029, 'vega': 0.122, 'rho': 0.178},
        {'strike_price': 95, 'option_type': 'call', 'market_price': 8.55, 'theoretical_value': 8.33, 'delta': 71, 'gamma': 2.8, 'theta': -0.034, 'vega': 0.170, 'rho': 0.155},
        {'strike_price': 100, 'option_type': 'call', 'market_price': 5.55, 'theoretical_value': 5.44, 'delta': 56, 'gamma': 3.2, 'theta': -0.035, 'vega': 0.196, 'rho': 0.124},
        {'strike_price': 105, 'option_type': 'call', 'market_price': 3.15, 'theoretical_value': 3.32, 'delta': 40, 'gamma': 3.1, 'theta': -0.032, 'vega': 0.192, 'rho': 0.091},
        {'strike_price': 110, 'option_type': 'call', 'market_price': 1.80, 'theoretical_value': 1.90, 'delta': 27, 'gamma': 2.6, 'theta': -0.027, 'vega': 0.163, 'rho': 0.062},
        # June Puts
        {'strike_price': 90, 'option_type': 'put', 'market_price': 1.45, 'theoretical_value': 1.12, 'delta': -16, 'gamma': 2.0, 'theta': -0.014, 'vega': 0.122, 'rho': -0.043},
        {'strike_price': 95, 'option_type': 'put', 'market_price': 2.63, 'theoretical_value': 2.42, 'delta': -29, 'gamma': 2.8, 'theta': -0.019, 'vega': 0.170, 'rho': -0.078},
        {'strike_price': 100, 'option_type': 'put', 'market_price': 4.55, 'theoretical_value': 4.45, 'delta': -44, 'gamma': 3.2, 'theta': -0.019, 'vega': 0.196, 'rho': -0.121},
        {'strike_price': 105, 'option_type': 'put', 'market_price': 7.10, 'theoretical_value': 7.26, 'delta': -60, 'gamma': 3.1, 'theta': -0.015, 'vega': 0.195, 'rho': -0.167},
        {'strike_price': 110, 'option_type': 'put', 'market_price': 10.70, 'theoretical_value': 10.77, 'delta': -73, 'gamma': 2.6, 'theta': -0.009, 'vega': 0.163, 'rho': -0.209}, # Corrected Vega for 110 Put from image 2 -> image 1
    ]

    for data in initial_options:
        option = OptionData(**data) # Unpack dictionary keys as arguments
        db.session.add(option)

    try:
        db.session.commit()
        print("Initial data populated successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error populating data: {e}")