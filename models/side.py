from enum import Enum

class Side(Enum):
    """
    Enumeration for trade positions.

    This enum represents the possible trading positions in a trading strategy.

    Attributes:
        LONG (int): Represents a long (buy) position.
        SHORT (int): Represents a short (sell) position.
    """
    LONG = 0
    SHORT = 1

    def __str__(self) -> str:
        """
        Returns a string representation of the Side enum member.

        Returns:
            str: A string representation of the Side enum member.
        """
        if self == Side.LONG:
            return "LONG"
        elif self == Side.SHORT:
            return "SHORT"
