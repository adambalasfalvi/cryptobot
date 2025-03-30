from models.percentage import Percentage

# List of trading symbols to be used in the strategy
TRADE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BCHUSDT", "XRPUSDT", "EOSUSDT", "PEOPLEUSDT"
]

# Currency of the account being used for trading
ACCOUNT_CURRENCY = "USDT"

# Interval of the candlestick (kline) data, here set to 1 minute
BAR_INTERVAL = "1m"

# Minimum percentage change in price to consider for volatility calculations
MIN_CHANGE = Percentage(0.001)

# Maximum allowable positive change in account balance before stopping the strategy in percentage
MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE = Percentage(1)

# Maximum allowable negative change in account balance before stopping the strategy in percentage
MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE = Percentage(-1)

# Amount of USD to risk per trade
RISK_USD = 120

# Leverage to be used in futures trading
LEVERAGE = 10

# Starting position for the strategy, can be either "LONG" or "SHORT"
# START_POSITION = "SHORT"  # Options: "LONG" or "SHORT"

# Multiplier for calculating stop loss price below entry price for long positions in percentage
STOP_LOSS_MULTIPLIER = Percentage(0.05)

# Multiplier for calculating take profit price above entry price for long positions in percentage
TAKE_PROFIT_MULTIPLIER = Percentage(0.05)

# Time interval in seconds to wait before retrying the connection
RETRY_INTERVAL = 5