from enum import IntEnum
from tkinter import BOTH

class OrderErrorCode(IntEnum):
    """
    Error codes for order operations.
    
    These codes indicate the success or failure point of order operations:
    - SUCCESS: All orders created successfully
    - POSITION_ORDER_FAILED: Failed to create the initial position order
    - TAKE_PROFIT_ORDER_FAILED: Failed to create the take profit order
    - STOP_LOSS_ORDER_FAILED: Failed to create the stop loss order
    - BOTH_ORDERS_FAILED: Both the take profit and stop loss orders failed
    - UNKNOWN_ERROR: An unexpected error occurred
    """
    SUCCESS = 0
    POSITION_ORDER_FAILED = 1
    TAKE_PROFIT_ORDER_FAILED = 2
    STOP_LOSS_ORDER_FAILED = 3
    BOTH_ORDERS_FAILED = 4
    UNKNOWN_ERROR = 99