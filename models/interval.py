from enum import Enum
from datetime import timedelta

class Interval(Enum):
    """
    An enumeration representing different time intervals commonly used in financial and trading contexts.

    Each member of this enum corresponds to a specific time interval, with its value being the string representation
    typically used in APIs or data systems to denote that interval.

    Members:
        ONE_MINUTE (str): Represents a 1-minute interval ("1m").
        THREE_MINUTES (str): Represents a 3-minute interval ("3m").
        FIVE_MINUTES (str): Represents a 5-minute interval ("5m").
        FIFTEEN_MINUTES (str): Represents a 15-minute interval ("15m").
        THIRTY_MINUTES (str): Represents a 30-minute interval ("30m").
        ONE_HOUR (str): Represents a 1-hour interval ("1h").
        TWO_HOURS (str): Represents a 2-hour interval ("2h").
        FOUR_HOURS (str): Represents a 4-hour interval ("4h").
        SIX_HOURS (str): Represents a 6-hour interval ("6h").
        EIGHT_HOURS (str): Represents an 8-hour interval ("8h").
        TWELVE_HOURS (str): Represents a 12-hour interval ("12h").
        ONE_DAY (str): Represents a 1-day interval ("1d").
        THREE_DAYS (str): Represents a 3-day interval ("3d").
        ONE_WEEK (str): Represents a 1-week interval ("1w").
        ONE_MONTH (str): Represents a 1-month interval ("1M").
    """
    
    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    SIX_HOURS = "6h"
    EIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"

    @property
    def timedelta(self) -> timedelta:
        if self == Interval.ONE_MINUTE:
            return timedelta(minutes=1)
        elif self == Interval.THREE_MINUTES:
            return timedelta(minutes=3)
        elif self == Interval.FIVE_MINUTES:
            return timedelta(minutes=5)
        elif self == Interval.FIFTEEN_MINUTES:
            return timedelta(minutes=15)
        elif self == Interval.THIRTY_MINUTES:
            return timedelta(minutes=30)
        elif self == Interval.ONE_HOUR:
            return timedelta(hours=1)
        elif self == Interval.TWO_HOURS:
            return timedelta(hours=2)
        elif self == Interval.FOUR_HOURS:
            return timedelta(hours=4)
        elif self == Interval.SIX_HOURS:
            return timedelta(hours=6)
        elif self == Interval.EIGHT_HOURS:
            return timedelta(hours=8)
        elif self == Interval.TWELVE_HOURS:
            return timedelta(hours=12)
        elif self == Interval.ONE_DAY:
            return timedelta(days=1)
        elif self == Interval.THREE_DAYS:
            return timedelta(days=3)
        elif self == Interval.ONE_WEEK:
            return timedelta(weeks=1)
        elif self == Interval.ONE_MONTH:
            return timedelta(days=30)
        else:
            return timedelta(minutes=1)  # Default case
    
    def __str__(self) -> str:
        """
        Returns a string representation of the Interval enum member.

        Returns:
            str: A string representation of the Interval enum member.
        """
        if self == Interval.ONE_MINUTE:
            return "1m"
        elif self == Interval.THREE_MINUTES:
            return "3m"
        elif self == Interval.FIVE_MINUTES:
            return "5m"
        elif self == Interval.FIFTEEN_MINUTES:
            return "15m"
        elif self == Interval.THIRTY_MINUTES:
            return "30m"
        elif self == Interval.ONE_HOUR:
            return "1h"
        elif self == Interval.TWO_HOURS:
            return "2h"
        elif self == Interval.FOUR_HOURS:
            return "4h"
        elif self == Interval.SIX_HOURS:
            return "6h"
        elif self == Interval.EIGHT_HOURS:
            return "8h"
        elif self == Interval.TWELVE_HOURS:
            return "12h"
        elif self == Interval.ONE_DAY:
            return "1d"
        elif self == Interval.ONE_WEEK:
            return "1w"
        elif self == Interval.ONE_MONTH:
            return "1M"
        elif self == Interval.ONE_MONTH:
            return "1m"
        else:
            return "1m"