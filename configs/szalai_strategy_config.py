# List of trading symbols to be used in the strategy
TRADE_SYMBOLS = [
    "AMBUSDT","FXSUSDT","AAVEUSDT","XEMUSDT","SKLUSDT",
    "BAKEUSDT","OMUSDT","SFPUSDT","ORBSUSDT","TWTUSDT",
    "IOTXUSDT","SAGAUSDT","CRVUSDT","CHRUSDT","ACEUSDT",
    "FLOWUSDT","RVNUSDT","XVSUSDT","BTCDOMUSDT","XMRUSDT",
    "LOOMUSDT","BONDUSDT","UNIUSDT","JUPUSDT","COMPUSDT",
    "ZENUSDT","RONINUSDT","EGLDUSDT","BNBUSDT","BELUSDT",
    "ASTRUSDT","ICXUSDT","HBARUSDT","APTUSDT","ENJUSDT",
    "GALAUSDT","LSKUSDT","XLMUSDT","TIAUSDT",
    "SUSHIUSDT","ONGUSDT","BALUSDT","QNTUSDT","JOEUSDT",
    "DEFIUSDT","AVAXUSDT","POWRUSDT","KNCUSDT","ATOMUSDT",
    "LEVERUSDT","CAKEUSDT","YFIUSDT","DENTUSDT","NOTUSDT",
    "GMXUSDT","CELRUSDT","CELOUSDT","MASKUSDT","DYDXUSDT",
    "1000BONKUSDT","1000LUNCUSDT","IMXUSDT","IOSTUSDT",
    "OXTUSDT","PEOPLEUSDT","LUNA2USDT","XTZUSDT",
    "LRCUSDT","ZILUSDT","NTRNUSDT","POLYXUSDT","HOTUSDT",
    "AXSUSDT","STEEMUSDT","LPTUSDT","TUSDT","SUIUSDT","STXUSDT",
    "GASUSDT","MKRUSDT","NKNUSDT","HOOKUSDT","FLMUSDT",
    "DOTUSDT","STORJUSDT","DASHUSDT","PERPUSDT","STGUSDT",
    "MOVRUSDT","FETUSDT","COMBOUSDT","OMGUSDT","EOSUSDT","INJUSDT",
    "PHBUSDT","LTCUSDT","GLMUSDT","QTUMUSDT","BNXUSDT","ARKUSDT",
    "NEOUSDT","ALICEUSDT","VETUSDT","LQTYUSDT"
]

# Currency of the account being used for trading
ACCOUNT_CURRENCY = "USDT"

# Interval of the candlestick (kline) data, here set to 1 minute
BAR_INTERVAL = "1m"

# Minimum percentage change in price to consider for volatility calculations
MIN_CHANGE = 0.0

# Maximum allowable positive change in account balance before stopping the strategy (e.g., 1% = 0.01)
MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE = 0.001

# Maximum allowable negative change in account balance before stopping the strategy (e.g., 1% = 0.01)
MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE = 0.001

# Amount of USD to risk per trade
RISK_USD = 120 

# Leverage to be used in futures trading
LEVERAGE = 1

# Starting position for the strategy, can be either "LONG" or "SHORT"
START_POSITION = "LONG"  # Options: "LONG" or "SHORT"

# Multiplier for calculating stop loss price, e.g., 0.1% below entry price for long positions
STOP_LOSS_MULTIPLIER = 0.01

# Multiplier for calculating take profit price, e.g., 0.1% above entry price for long positions
TAKE_PROFIT_MULTIPLIER = 0.01
