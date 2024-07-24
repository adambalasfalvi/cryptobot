from enum import Enum

class OrderType(Enum):
    """
    An enumeration representing different types of orders.

    Attributes:
        MARKET (int): Represents a market order, which is executed immediately at the current market price.
        LIMIT (int): Represents a limit order, which is executed at a specified price or better.
    """
    
    MARKET = 0  # Market order type
    LIMIT = 1   # Limit order type
