from enum import Enum

class OrderStatus(Enum):
    """
    An enumeration representing different statuses of orders.

    Attributes:
        NEW (int): Represents a new order that has been created.
        FILLED (int): Represents an order that has been fully executed.
        PARTIALLY_FILLED (int): Represents an order that has been partially executed.
        CANCELED (int): Represents an order that has been canceled.
        PENDING_CANCEL (int): Represents an order that is pending cancellation.
        EXPIRED (int): Represents an order that has expired.
        REJECTED (int): Represents an order that has been rejected.
    """

    NEW = 0  # New order status
    FILLED = 1   # Filled order status
    PARTIALLY_FILLED = 2 # Partially filled order status
    CANCELED = 3 # Canceled order status
    PENDING_CANCEL = 4 # Pending cancel order status
    EXPIRED = 5  # Expired order status
    REJECTED = 6  # Rejected order status