from models.percentage import Percentage

# List of trading symbols to be used in the strategy
TRADE_SYMBOLS = [ "BTCUSDT" ]
# TRADE_SYMBOLS = [
#     "BTCUSDT", "ETHUSDT", "BCHUSDT", "XRPUSDT", "EOSUSDT", "PEOPLEUSDT"
# ]

# Currency of the account being used for trading
ACCOUNT_CURRENCY = "USDT"

# Interval of the candlestick (kline) data (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w)
BAR_INTERVAL = "1w"

# Minimum percentage change in price to consider for volatility calculations
MIN_CHANGE = Percentage(0.001)

# Maximum allowable positive change in account balance before stopping the strategy in percentage
MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE = Percentage(5)

# Maximum allowable negative change in account balance before stopping the strategy in percentage
MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE = Percentage(-5)

# Amount of USD to risk per trade
RISK_USD = 150

# Leverage to be used in futures trading
LEVERAGE = 1

# Multiplier for calculating stop loss price in percentage
STOP_LOSS_MULTIPLIER = Percentage(1)

# Multiplier for calculating take profit price in percentage
TAKE_PROFIT_MULTIPLIER = Percentage(1)

# Time interval in seconds to wait before retrying the connection
RETRY_INTERVAL = 5

# Logging precision for displaying floating-point numbers
LOGGING_PRECISION = 3