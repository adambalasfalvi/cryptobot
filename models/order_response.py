class OrderResponse():
    """
    A class to represent the response from an order placed on the Binance platform.

    Attributes:
        client_order_id (str): The unique identifier for the client order.
        symbol (str): The trading pair symbol.
        status (str): The current status of the order.
        average_price (float): The average price at which the order was filled.
        stop_price (float): The stop price for the order.
        original_quantity (float): The original quantity of the order.
        type (str): The type of the order (e.g., market, limit).
        side (str): The side of the order (buy or sell).
    """

    def __init__(
            self, 
            client_order_id: str,  
            symbol: str, 
            status: str,
            average_price: float, 
            stop_price: float, 
            original_quantity: float, 
            type: str, 
            side: str) -> None:
        """
        Initializes the OrderResponse object with given parameters.

        Args:
            client_order_id (str): The unique identifier for the client order.
            symbol (str): The trading pair symbol.
            status (str): The current status of the order.
            average_price (float): The average price at which the order was filled.
            stop_price (float): The stop price for the order.
            original_quantity (float): The original quantity of the order.
            type (str): The type of the order (e.g., market, limit).
            side (str): The side of the order (buy or sell).
        """
        self.client_order_id = client_order_id
        self.symbol = symbol
        self.status = status
        self.average_price = average_price
        self.stop_price = stop_price
        self.original_quantity = original_quantity
        self.type = type
        self.side = side

    @property
    def is_updated(self) -> bool:
        """
        Checks if all attributes of the order response are set.

        Returns:
            bool: True if all attributes are set, False otherwise.
        """
        return all(value is not None for value in self.__dict__.values())
    
    def __str__(self) -> str:
        """
        Provides a string representation of the order response.

        Returns:
            str: A string that represents the order response.
        """
        return (
            f"client_order_id: {self.client_order_id}, "
            f"symbol: {self.symbol}, "
            f"average_price: {self.average_price}, "
            f"stop_price: {self.stop_price}, "
            f"original_quantity: {self.original_quantity}, "
            f"type: {self.type}, "
            f"side: {self.side}"
        )
