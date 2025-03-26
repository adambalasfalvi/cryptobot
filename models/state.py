from enum import Enum

class State(Enum):
    """
    Enum representing the various states of the trading bot.

    States:
        INIT (0): Initial state.
        NO_TRADE (1): No trade state.
        COLLECTING_DATA (2): Collecting data state.
        TAKING_POSITION (3): Taking position state.
        TRADE (4): Trade state.
        ORDER_FILLED (5): Order filled state.
        WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_REACHED (6): Waiting for order cancel when balance change limit is reached.
        WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED (7): Waiting for order cancel when balance change limit is not reached.
        ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_REACHED (8): Order canceled when balance change limit reached state.
        ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED (9): Order canceled when balance change limit not reached state.
        FIRST_ORDER_CANCELED (10): First order canceled state.
        WAITING_FOR_SECOND_ORDER_CANCEL (11): Waiting for second order cancel state.
        SECOND_ORDER_CANCELED (12): Second order canceled state.
        CLEARING_ORDERS (13): Clearing orders state.
        CONNECTION_LOST (14): Lost internet connection state.
        CONNECTION_RESTORED (15): Restored internet connection state.
        STOPPED (16): Stopped state.
    """
    INIT = 0
    NO_TRADE = 1
    COLLECTING_DATA = 2
    TAKING_POSITION = 3
    TRADE = 4
    ORDER_FILLED = 5
    WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_REACHED = 6
    WAITING_FOR_CANCEL_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED = 7
    ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_REACHED = 8
    ORDER_CANCELED_WHEN_BALANCE_CHANGE_LIMIT_NOT_REACHED = 9
    FIRST_ORDER_CANCELED = 10
    WAITING_FOR_SECOND_ORDER_CANCEL = 11
    SECOND_ORDER_CANCELED = 12
    CLEARING_ORDERS = 13
    CONNECTION_LOST = 14
    CONNECTION_RESTORED = 15
    STOPPED = 16