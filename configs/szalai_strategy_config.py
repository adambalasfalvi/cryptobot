# List of trading symbols to be used in the strategy
TRADE_SYMBOLS = ["ETHUSDT", "BTCUSDT"]

# Currency of the account being used for trading
ACCOUNT_CURRENCY = "USDT"

# Interval of the candlestick (kline) data, here set to 1 minute
BAR_INTERVAL = "1m"

# Minimum percentage change in price to consider for volatility calculations
MIN_CHANGE = 0.1

# Maximum allowable change in account balance before stopping the strategy (e.g., 1%)
MAX_ACCOUNT_BALANCE_CHANGE = 0.01

# Amount of USD to risk per trade
RISK_USD = 10 

# Quantity of the asset to trade (e.g., 0.1 ETH or BTC)
TRADE_QUANTITY = 0.1 

# Leverage to be used in futures trading
LEVERAGE = 1

# Starting position for the strategy, can be either "LONG" or "SHORT"
START_POSITION = "LONG"  # Options: "LONG" or "SHORT"

# Multiplier for calculating stop loss price, e.g., 0.1% below entry price for long positions
STOP_LOSS_MULTIPLIER = 0.001

# Multiplier for calculating take profit price, e.g., 0.1% above entry price for long positions
TAKE_PROFIT_MULTIPLIER = 0.001
