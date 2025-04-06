from enum import Enum, auto

class State(Enum):
    """
    Enum representing the various states of the trading bot.

    States:
        INIT: Initial state when the bot first starts.
        NO_TRADE: State when the bot is not actively trading.
        COLLECTING_DATA: State when the bot is collecting market data for analysis.
        TAKING_POSITION_AND_ORDERS: State when the bot is creating position and order entries.
        TRADE: State when the bot has active trades and is monitoring them.
        TAKE_PROFIT_ORDER_FILLED: State when a take profit order has been filled.
        STOP_MARKET_ORDER_FILLED: State when a stop market order has been filled.
        CONNECTION_LOST: State when the internet connection has been lost.
        CONNECTION_RESTORED: State when the internet connection has been restored.
        STOPPED: State when the bot has been stopped and is shutting down.
    """
    INIT = 0
    NO_TRADE = 1
    COLLECTING_DATA = 2
    TAKING_POSITION_AND_ORDERS = 3
    TRADE = 4
    TAKE_PROFIT_ORDER_FILLED = 5
    STOP_MARKET_ORDER_FILLED = 6
    CONNECTION_LOST = 7
    CONNECTION_RESTORED = 8
    STOPPED = 9