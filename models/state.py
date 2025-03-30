from enum import Enum

class State(Enum):
    """
    Enum representing the various states of the trading bot.

    States:
        INIT (0): Initial state.
        NO_TRADE (1): No trade state.
        COLLECTING_DATA (2): Collecting data state.
        TAKING_POSITION_AND_ORDERS (3): Taking position and orders state.
        TRADE (4): Trade state.
        TAKE_PROFIT_ORDER_FILLED (5): Take profit order filled state.
        STOP_MARKET_ORDER_FILLED (6): Stop market order filled state.
        WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_REACHED (7): Waiting for order cancel when balance change limit is reached.
        WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED (8): Waiting for order cancel when balance change limit is not reached.
        ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_REACHED (9): Order canceled when balance change limit reached state.
        ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED (10): Order canceled when balance change limit not reached state.
        FIRST_ORDER_CANCELED (11): First order canceled state.
        WAITING_FOR_SECOND_ORDER_CANCEL (12): Waiting for second order cancel state.
        SECOND_ORDER_CANCELED (13): Second order canceled state.
        CLEARING_ORDERS (14): Clearing orders state.
        CONNECTION_LOST (15): Lost internet connection state.
        CONNECTION_RESTORED (16): Restored internet connection state.
        STOPPED (17): Stopped state.
    """
    INIT = 0
    NO_TRADE = 1
    COLLECTING_DATA = 2
    TAKING_POSITION_AND_ORDERS = 3
    TRADE = 4
    TAKE_PROFIT_ORDER_FILLED = 5
    STOP_MARKET_ORDER_FILLED = 6
    WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_REACHED = 7
    WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED = 8
    ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_REACHED = 9
    ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED = 10
    FIRST_ORDER_CANCELED = 11
    WAITING_FOR_SECOND_ORDER_CANCEL = 12
    SECOND_ORDER_CANCELED = 13
    CLEARING_ORDERS = 14
    CONNECTION_LOST = 15
    CONNECTION_RESTORED = 16
    STOPPED = 17
