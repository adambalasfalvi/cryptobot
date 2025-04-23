from datetime import datetime, timedelta
from typing import Optional

class KlineData:
    """
    Represents candlestick (k-line) data for a specific trading symbol.

    Attributes:
        symbol (str): The trading symbol (e.g., 'BTCUSDT').
        interval (str): The interval of the k-line data (e.g., 1m, 1h).
        open_price (float): The opening price of the k-line.
        close_price (float): The closing price of the k-line.
        high_price (float): The highest price of the k-line.
        low_price (float): The lowest price of the k-line.
        open_time (datetime): The opening time of the k-line.
        close_time (datetime): The closing time of the k-line.
    """
    
    def __init__(self, symbol: str, 
                 interval: str, 
                 open_price: float, 
                 close_price: float, 
                 high_price: float, 
                 low_price: float, 
                 open_time: datetime, 
                 close_time: datetime) -> None:
        """
        Initializes a new instance of the KlineData class.

        Args:
            symbol (str): The trading symbol.
            interval (str): The interval of the k-line data.
            open_price (float): The opening price of the k-line.
            close_price (float): The closing price of the k-line.
            high_price (float): The highest price of the k-line.
            low_price (float): The lowest price of the k-line.
            open_time (datetime): The opening time of the k-line.
            close_time (datetime): The closing time of the k-line.
        """
        self.symbol = symbol
        self.interval = interval
        self.open_price = open_price
        self.close_price = close_price
        self.high_price = high_price
        self.low_price = low_price
        self.open_time = open_time
        self.close_time = close_time

    @classmethod
    def from_symbol(cls, symbol: str):
        """
        Creates an instance of KlineData with only the symbol specified.
        """
        return cls(symbol, str(), 0.0, 0.0, 0.0, 0.0, datetime.min, datetime.min)

    @property
    def change(self) -> float:
        """
        Calculates the relative price change of the k-line.
    
        Returns:
            float: The relative price change as a decimal (e.g., 0.05 for 5% increase).
            0.0: If open_price or close_price is None or open_price is 0.0.
        """
        if self.open_price is None or self.close_price is None:
            return 0.0
            
        if self.open_price == 0.0:
            return 0.0
    
        return (self.close_price - self.open_price) / self.open_price
    
    @property
    def percentage_change(self) -> float:
        """
        Returns the price change as a percentage.

        Returns:
            float: The price change as a percentage.
        """
        return self.change * 100

    @property
    def is_updated(self) -> bool:
        """
        Checks if all attributes of the k-line data are updated and the k-line is closed.

        Returns:
            bool: True if all attributes are not None and the k-line is closed, False otherwise.
        """
        return all(value is not None for value in self.__dict__.values())
    
    @property 
    def is_not_empty(self) -> bool:
        """
        Checks if all attributes of the k-line data are not empty.

        Returns:
            bool: True if all attributes are not None, False otherwise.
        """
        return all(value is not None for value in self.__dict__.values())

    def __str__(self) -> str:
        """
        Returns a string representation of the KlineData instance.

        Returns:
            str: A string representation of the KlineData.
        """
        return (
            f"symbol: {self.symbol}, "
            f"interval: {self.interval}, "
            f"open_price: {self.open_price}, "
            f"close_price: {self.close_price}, "
            f"high_price: {self.high_price}, "
            f"low_price: {self.low_price}, "
            f"open_time: {self.open_time}, "
            f"close_time: {self.close_time}"
        )