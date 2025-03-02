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
        ORDER_CANCELED (6): Order canceled state.
    """
    INIT = 0
    NO_TRADE = 1
    COLLECTING_DATA = 2
    TAKING_POSITION = 3
    TRADE = 4
    ORDER_FILLED = 5
    ORDER_CANCELED = 6