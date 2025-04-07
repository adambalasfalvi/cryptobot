from enum import Enum
from datetime import datetime, timedelta
from math import ceil

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

    def get_trigger_time(self, server_time: datetime) -> datetime:
        """
        Calculates the next trigger time for the given interval based on server time.
        
        For smaller intervals (1m, 3m, 5m, 15m, 30m, 1h, 2h), this aligns with the regular
        clock boundaries.
        
        For larger intervals (4h, 6h, 8h, 12h, 1d, 3d, 1w), the counting begins from:
            - 2:00 PM (14:00) during summer time (DST)
            - 1:00 PM (13:00) during winter time (non-DST)
        
        Args:
            server_time (datetime): Current server time to calculate from
            
        Returns:
            datetime: The next trigger time for this interval
        """
        # First check if it's DST (summer time) or not (winter time)
        # This uses the server_time's tzinfo to determine DST status
        # Default to summer time offset if time has no timezone info
        dst_value = server_time.dst() if server_time.tzinfo else None
        is_dst = dst_value is not None and dst_value.total_seconds() > 0 if server_time.tzinfo else True
        base_hour = 2 if is_dst else 1  # 2AM for summer, 1AM for winter
        
        # Short intervals aligned to regular clock boundaries
        if self == Interval.ONE_MINUTE:
            return server_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        elif self == Interval.THREE_MINUTES:
            minute = server_time.minute
            # Get the next 3-minute boundary (0, 3, 6, 9, 12, etc.)
            next_minute = ceil(minute / 3) * 3
            if next_minute == minute and server_time.second > 0:
                next_minute += 3
            if next_minute >= 60:
                return (server_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1, minutes=next_minute-60))
            return server_time.replace(minute=next_minute, second=0, microsecond=0)
        elif self == Interval.FIVE_MINUTES:
            minute = server_time.minute
            # Get the next 5-minute boundary (0, 5, 10, 15, etc.)
            next_minute = ceil(minute / 5) * 5
            if next_minute == minute and server_time.second > 0:
                next_minute += 5
            if next_minute >= 60:
                return (server_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1, minutes=next_minute-60))
            return server_time.replace(minute=next_minute, second=0, microsecond=0)
        elif self == Interval.FIFTEEN_MINUTES:
            minute = server_time.minute
            # Get the next 15-minute boundary (0, 15, 30, 45)
            next_minute = ceil(minute / 15) * 15
            if next_minute == minute and server_time.second > 0:
                next_minute += 15
            if next_minute >= 60:
                return (server_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1, minutes=next_minute-60))
            return server_time.replace(minute=next_minute, second=0, microsecond=0)
        elif self == Interval.THIRTY_MINUTES:
            minute = server_time.minute
            # Get the next 30-minute boundary (0, 30)
            next_minute = ceil(minute / 30) * 30
            if next_minute == minute and server_time.second > 0:
                next_minute += 30
            if next_minute >= 60:
                return (server_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1, minutes=next_minute-60))
            return server_time.replace(minute=next_minute, second=0, microsecond=0)
        elif self == Interval.ONE_HOUR:
            if server_time.minute > 0 or server_time.second > 0:
                return server_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return server_time.replace(minute=0, second=0, microsecond=0)
        elif self == Interval.TWO_HOURS:
            hour = server_time.hour
            next_hour = ceil(hour / 2) * 2
            if next_hour == hour and (server_time.minute > 0 or server_time.second > 0):
                next_hour += 2
            if next_hour >= 24:
                return (server_time.replace(hour=0, minute=0, second=0, microsecond=0) + 
                        timedelta(days=1, hours=next_hour-24))
            return server_time.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        # For 4h, 6h, 8h, 12h, 1d, 3d, 1w intervals, we use the base hour (02:00/01:00)
        current = server_time.replace(minute=0, second=0, microsecond=0)
        
        if self == Interval.FOUR_HOURS:
            # Find next 4-hour interval from base hour (02:00/01:00)
            hours_since_base = (current.hour - base_hour) % 24
            next_interval = 4 * ceil(hours_since_base / 4)
            target_hour = (base_hour + next_interval) % 24
            days_ahead = (base_hour + next_interval) // 24
            if target_hour == current.hour and (server_time.minute > 0 or server_time.second > 0):
                target_hour = (target_hour + 4) % 24
                if target_hour < current.hour:
                    days_ahead += 1
            target = current.replace(hour=target_hour)
            if target <= current:
                target += timedelta(days=days_ahead)
            return target
        
        elif self == Interval.SIX_HOURS:
            # Find next 6-hour interval from base hour (02:00/01:00)
            hours_since_base = (current.hour - base_hour) % 24
            next_interval = 6 * ceil(hours_since_base / 6)
            target_hour = (base_hour + next_interval) % 24
            days_ahead = (base_hour + next_interval) // 24
            if target_hour == current.hour and (server_time.minute > 0 or server_time.second > 0):
                target_hour = (target_hour + 6) % 24
                if target_hour < current.hour:
                    days_ahead += 1
            target = current.replace(hour=target_hour)
            if target <= current:
                target += timedelta(days=days_ahead)
            return target
        
        elif self == Interval.EIGHT_HOURS:
            # Find next 8-hour interval from base hour (02:00/01:00)
            hours_since_base = (current.hour - base_hour) % 24
            next_interval = 8 * ceil(hours_since_base / 8)
            target_hour = (base_hour + next_interval) % 24
            days_ahead = (base_hour + next_interval) // 24
            if target_hour == current.hour and (server_time.minute > 0 or server_time.second > 0):
                target_hour = (target_hour + 8) % 24
                if target_hour < current.hour:
                    days_ahead += 1
            target = current.replace(hour=target_hour)
            if target <= current:
                target += timedelta(days=days_ahead)
            return target
        
        elif self == Interval.TWELVE_HOURS:
            # Find next 12-hour interval from base hour (02:00/01:00)
            hours_since_base = (current.hour - base_hour) % 24
            next_interval = 12 * ceil(hours_since_base / 12)
            target_hour = (base_hour + next_interval) % 24
            days_ahead = (base_hour + next_interval) // 24
            if target_hour == current.hour and (server_time.minute > 0 or server_time.second > 0):
                target_hour = (target_hour + 12) % 24
                if target_hour < current.hour:
                    days_ahead += 1
            target = current.replace(hour=target_hour)
            if target <= current:
                target += timedelta(days=days_ahead)
            return target
        
        elif self == Interval.ONE_DAY:
            # Base time 02:00/01:00 every day
            if current.hour > base_hour or (current.hour == base_hour and (server_time.minute > 0 or server_time.second > 0)):
                return (current.replace(hour=base_hour, minute=0, second=0, microsecond=0) + 
                        timedelta(days=1))
            return current.replace(hour=base_hour, minute=0, second=0, microsecond=0)
        
        elif self == Interval.THREE_DAYS:
            # Get the 2023-01-01 date with the base hour
            start_of_time_calculation = datetime(2023, 1, 1).replace(hour=base_hour, minute=0, second=0, microsecond=0)
            
            # Determine which 3-day period we're in (starting from 2023 Jan 1st)
            days_elapsed = (current - start_of_time_calculation.replace(tzinfo=current.tzinfo)).days
            period = days_elapsed // 3
            
            # Calculate the start of the current 3-day period
            period_start = start_of_time_calculation.replace(tzinfo=current.tzinfo) + timedelta(days=period*3)
            period_start = period_start.replace(hour=base_hour, minute=0, second=0, microsecond=0)
            
            # If we're past the base hour in the last day of the period, move to the next period
            if (current - period_start).days >= 2 or (
                    (current - period_start).days == 2 and 
                    (current.hour > base_hour or 
                        (current.hour == base_hour and (server_time.minute > 0 or server_time.second > 0)))):
                return period_start + timedelta(days=3)
            
            # Otherwise, return the base hour on the 3rd day of the current period
            return period_start + timedelta(days=2)
        
        elif self == Interval.ONE_WEEK:
            # Base time 02:00/01:00 on weekly boundaries (assuming Monday is start of week)
            today = current.weekday()  # 0 is Monday, 6 is Sunday
            days_to_next_monday = 7 - today if today > 0 else (0 if current.hour < base_hour else 7)
            
            next_week = current.replace(hour=base_hour, minute=0, second=0, microsecond=0) + timedelta(days=days_to_next_monday)
            
            if current.hour > base_hour or (current.hour == base_hour and (server_time.minute > 0 or server_time.second > 0)):
                if today == 0:  # If it's Monday after base hour
                    return next_week
            return next_week
        
        # Default case if interval is not recognized is one minute
        return server_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
    
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