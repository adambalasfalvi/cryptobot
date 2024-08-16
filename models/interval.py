from enum import Enum

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