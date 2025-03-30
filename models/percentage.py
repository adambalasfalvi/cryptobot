class Percentage:
    """
    A class to handle percentage values and their conversions.
    
    This class stores a percentage value and provides methods to convert 
    between percentage and decimal representations.
    """
    
    def __init__(self, value) -> None:
        """
        Initialize a Percentage object with a given value.
        
        Args:
            value: The percentage value (e.g., 5 for 5%)
        """
        self.percent_value = value

    @property
    def decimal_value(self) -> float:
        """
        Convert the percentage value to its decimal equivalent.
        
        Returns:
            float: The decimal representation of the percentage (e.g., 0.05 for 5%)
        """
        return self.percent_value / 100.0 
    
    def __str__(self) -> str:
        """
        Return the string representation of the percentage value.
        
        Returns:
            str: The percentage value with a '%' symbol (e.g., '5%')
        """
        return f"{self.percent_value}%"
    
    def __repr__(self) -> str:
        """
        Return the official string representation of the Percentage object.
        
        Returns:
            str: A string representation that can be used to recreate the object
        """
        return f"Percentage({self.percent_value})"