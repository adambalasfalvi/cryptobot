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
        FIRST_ORDER_CANCELED (6): First order canceled state.
        WAITING_FOR_SECOND_ORDER_CANCEL (7): Waiting for second order cancel state.
        SECOND_ORDER_CANCELED (8): Second order canceled state.
        CLEARING_ORDERS (9): Clearing orders state.
        CONNECTION_LOST (10): Lost internet connection state.
        CONNECTION_RESTORED (11): Restored internet connection state.
        STOPPED (12): Stopped state.
    """
    INIT = 0
    NO_TRADE = 1
    COLLECTING_DATA = 2
    TAKING_POSITION = 3
    TRADE = 4
    ORDER_FILLED = 5
    FIRST_ORDER_CANCELED = 6
    WAITING_FOR_SECOND_ORDER_CANCEL = 7
    SECOND_ORDER_CANCELED = 8
    CLEARING_ORDERS = 9
    CONNECTION_LOST = 10
    CONNECTION_RESTORED = 11
    STOPPED = 12