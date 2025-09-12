import queue
import sys
import logging
import time
import threading
import asyncio
from turtle import up
from typing import Optional
import aiohttp
import traceback
import numpy
from datetime import datetime
from logging import Logger
from logging.handlers import QueueHandler, QueueListener
from concurrent.futures import ThreadPoolExecutor
from models.order_error_code import OrderErrorCode
from models.order_response import OrderResponse
from models.side import Side
from models.kline_data import KlineData
from models.interval import Interval
from models.symbol import Symbol
from models.state import State
from logic.managers.binance_client_manager import BinanceClientManager
from logic.managers.binance_websocket_manager import BinanceWebsocketManager
from configs import szalai_strategy_config
from threading import Event
from threading import Lock
from logic.managers.session_manager import SessionManager

class SzalaiStrategy:
    """
    Implements the Szalai trading strategy using the Binance API for futures trading.

    This class manages the trading strategy including:
    - Initializing and setting up the trading environment
    - Managing real-time data and WebSocket connections
    - Handling order execution and position management
    - Monitoring profit and making adjustments to trading positions
    """

    def __init__(self) -> None:
        """
        Initializes the SzalaiStrategy instance.

        This constructor sets up the logger, initializes the client and WebSocket managers,
        determines the initial trading side (LONG or SHORT), and prepares the list of kline
        data objects and order responses.
        """
        self.logger = self._init_logger() 
        self.client_manager = BinanceClientManager(logger=self.logger)
        self.websocket_manager = BinanceWebsocketManager(logger=self.logger)
        self.side : Side
        self.state: State = State.INIT
        self.state_lock : Lock = Lock()
        self.currency = szalai_strategy_config.ACCOUNT_CURRENCY
        self.risk_usd = szalai_strategy_config.RISK_USD
        self.interval = next(interval for interval in Interval if interval.value == szalai_strategy_config.BAR_INTERVAL) 
        self.kline_data_list: list[KlineData] = [KlineData.from_symbol(symbol) for symbol in szalai_strategy_config.TRADE_SYMBOLS]
        self.symbol_info_list: list[Symbol] = []
        self.order_list: list[OrderResponse] = []
        self.start_account_balance: float
        self.signal_interval_trigger: bool = False
        self.stop_event = Event()   
        self.trading_symbol: str = str()
        self.trading_symbol_kline_data: KlineData
        self.trading_symbol_quantity: float
        self.trading_symbol_position_order: OrderResponse
        self.trading_symbol_take_profit_order: OrderResponse
        self.trading_symbol_stop_loss_order : OrderResponse
        self.interval_trigger_thread: threading.Thread
        self.session_manager = SessionManager(logger=self.logger)
        self.queue_listener: Optional[QueueListener]

    async def start_strategy(self) -> None:
        # Initialize the strategy
        await self._init_strategy()

        # Run the strategy
        await self._run_strategy()

    async def stop_strategy(self) -> None:
        """
        Stops the Szalai trading strategy.

        This method logs the stop event, stops the WebSocket connections, and closes all open positions
        and orders to halt trading activities.
        """
        self.logger.info("Stopping Szalai strategy...")

        # Set state to STOPPED
        with self.state_lock:
            self.state = State.STOPPED

        # Set the stop event to signal
        self.stop_event.set()

        # Stop the WebSocket manager to cease receiving data
        self.websocket_manager.stop_websocket()

        # Close all open positions and cancel all orders for all symbols
        async with aiohttp.ClientSession() as session:
            await self._close_open_positions_and_cancel_orders_for_all_symbols(
                session=session
            )

        # Wait 2 seconds for the interval trigger thread to complete
        self.interval_trigger_thread.join(timeout=2.0)

        # Not needed anymore, because the  _run_strategy() loop already got cancelled
        # Close the session
        # await self.session_manager.close_session()

        self.logger.info("Szalai strategy has stopped.")

        # Stop the queue listener if it exists
        if self.queue_listener:
            self.queue_listener.stop()
    
    async def _init_strategy(self) -> None:
        # Log the start of the strategy execution
        self.logger.info("Starting Szalai strategy.")

        # Initialize session
        self.session_manager.create_session()

        # Check if all symbols exist in Binance
        if not self._check_if_all_symbol_exists_in_binance():
            raise ValueError("Not all symbols exist in Binance. Please check the symbols in the config.")

        # Fetch and store the initial account balance
        self.start_account_balance = self.client_manager.futures_get_account_balance(self.currency)
        if self.start_account_balance == -1:
            raise ValueError(f"Currency {self.currency} not found in account balances. Please check the account balance in the config.")
        self.logger.info(f"Start account balance is {round(self.start_account_balance, szalai_strategy_config.LOGGING_PRECISION)} {self.currency}.")

        # Set the leverage for each trading symbol
        with ThreadPoolExecutor() as executor:
            for symbol in szalai_strategy_config.TRADE_SYMBOLS:
                # Submit a task to change the leverage for each symbol to the configured value
                executor.submit(self.client_manager.futures_change_leverage, symbol, szalai_strategy_config.LEVERAGE)
        
        # Start the interval trigger thread
        self.interval_trigger_thread = threading.Thread(
            target=self._set_interval_trigger,
            name="IntervalTriggerThread")
        self.interval_trigger_thread.start()

        # Start the WebSocket manager to receive real-time updates for market data and user data
        # self.websocket_manager.start_websocket()

        # Set up the WebSocket for user data to receive order updates and provide a handler for updates
        # self.websocket_manager.setup_user_data_websocket(
        #     self._update_order_data_handler           # Handler method to process order data updates
        # )

    async def _run_strategy(self) -> None:
        # Main strategy loop to continuously check and act upon various conditions until the stop event is set
        while not self.stop_event.is_set():
            with self.state_lock:
                match self.state:
                    case State.INIT:
                        self._get_precision_information_for_symbols()
                        await self._close_open_positions_and_cancel_orders_for_all_symbols(self.session_manager.get_session())
                        self.logger.info("Updating state to NO_TRADE.")
                        self.state = State.NO_TRADE
                    case State.NO_TRADE:
                        # Wait for the interval trigger to set the state to COLLECTING_DATA
                        pass
                    case State.COLLECTING_DATA:
                        await self._update_kline_data_for_all_symbol()
                        self._get_most_volatile_symbol()
                        if self._check_change_rate():
                            await self._calculate_first_side()
                            self.logger.info("Updating state to TAKING_POSITION_AND_ORDERS.")
                            self.state = State.TAKING_POSITION_AND_ORDERS
                        else:
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                    case State.TAKING_POSITION_AND_ORDERS:               
                        self._calculate_quantity()
                        order_error_code = await self._set_up_orders()
                        if order_error_code == OrderErrorCode.SUCCESS:
                            self.logger.info("Updating state to TRADE.")
                            self.state = State.TRADE
                        elif order_error_code == OrderErrorCode.POSITION_ORDER_FAILED:
                            await self._close_open_position_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to ERROR_AT_TAKING_POSITION_AND_ORDERS.")
                            self.state = State.ERROR_AT_TAKING_POSITION_AND_ORDERS
                        elif order_error_code == OrderErrorCode.TAKE_PROFIT_ORDER_FAILED:
                            await self._close_open_position_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to ERROR_AT_TAKING_POSITION_AND_ORDERS.")
                            self.state = State.ERROR_AT_TAKING_POSITION_AND_ORDERS
                        elif order_error_code == OrderErrorCode.STOP_LOSS_ORDER_FAILED:
                            await self._close_open_position_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to ERROR_AT_TAKING_POSITION_AND_ORDERS.")
                            self.state = State.ERROR_AT_TAKING_POSITION_AND_ORDERS
                        elif order_error_code == OrderErrorCode.BOTH_ORDERS_FAILED:
                            await self._close_open_position_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to ERROR_AT_TAKING_POSITION_AND_ORDERS.")
                            self.state = State.ERROR_AT_TAKING_POSITION_AND_ORDERS
                        elif order_error_code == OrderErrorCode.UNKNOWN_ERROR:
                            self.logger.info("Updating state to ERROR_AT_TAKING_POSITION_AND_ORDERS.")
                            self.state = State.ERROR_AT_TAKING_POSITION_AND_ORDERS
                    case State.ERROR_AT_TAKING_POSITION_AND_ORDERS:
                        check_orders = await self._check_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                        check_position = await self._check_position_for_symbol(self.trading_symbol, self.session_manager.get_session())
                        if check_orders or check_position:
                            await self._close_open_position_and_cancel_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                        else:
                            self.logger.info("Updating state to TAKING_POSITION_AND_ORDERS.")
                            self.state = State.TAKING_POSITION_AND_ORDERS
                    case State.TRADE:
                        # Waiting for one of the orders to be filled
                        pass
                    case State.TAKE_PROFIT_ORDER_FILLED:
                        if self._is_balance_change_limit_reached():
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                        else:
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to TAKING_POSITION_AND_ORDERS.")
                            self.state = State.TAKING_POSITION_AND_ORDERS
                    case State.STOP_MARKET_ORDER_FILLED:
                        if self._is_balance_change_limit_reached():
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                        else:
                            # Reverse the side for the next trade
                            self._reverse_side()
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to TAKING_POSITION_AND_ORDERS.")
                            self.state = State.TAKING_POSITION_AND_ORDERS
                    case State.CONNECTION_LOST:
                        # Waiting until connection is restored
                        pass
                    case State.CONNECTION_RESTORED:
                        open_orders = await self._what_orders_are_open(self.trading_symbol, self.session_manager.get_session())
                        if len(open_orders) == 0:
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                        elif len(open_orders) != 2:
                            await self._cancel_open_orders_for_symbol(self.trading_symbol, self.session_manager.get_session())
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                        else:
                            self.logger.info("Updating state to TRADE.")
                            self.state = State.TRADE
                    case State.STOPPED:
                        pass
    
    def _check_if_all_symbol_exists_in_binance(self) -> bool:
        """
        Check if all symbols in szalai_strategy_config.TRADE_SYMBOLS exist in Binance.

        Returns:
            bool: True if all symbols exist, False otherwise.
        """
        exchange_info = self.client_manager.futures_get_exchange_info()
        all_symbols = [symbol_info["symbol"] for symbol_info in exchange_info["symbols"]]
        not_found_symbols = [symbol for symbol in szalai_strategy_config.TRADE_SYMBOLS if symbol not in all_symbols]
        if len(not_found_symbols) == 0:
            self.logger.info("All symbols in config exist in Binance.")
            return True
        else:
            self.logger.error(f"Symbols not found in Binance: {not_found_symbols}.")
            return False
        
    def _reverse_side(self) -> None: 
        """
        Reverse the trading side (LONG or SHORT) for the next trade.
        """
        if self.side == Side.LONG:
            self.side = Side.SHORT
        else:
            self.side = Side.LONG
        self.logger.info(f"Reversed trading side to {self.side}.")
    
    async def _calculate_first_side(self) -> None:
        """
        Calculates what will be the side to begin with if a new symbol has been chosen.

        This method retrieves the historical kline data for the trading symbol and determines the starting side.
        If the price has increased (close price is higher than open price), the starting side will be SHORT.
        If the price has declined (close price is lower than open price), the starting side will be LONG.
        If the REVERSE_FIRST_ORDER_SIDE config is set to True, the side will be reversed.
        """   
        symbol_kline_data = next(kline_data for kline_data in self.kline_data_list if kline_data.symbol == self.trading_symbol)

        # If price has increased
        if symbol_kline_data.open_price - symbol_kline_data.close_price < 0:
            self.side = Side.SHORT
        # If declined
        else:
            self.side = Side.LONG

        if szalai_strategy_config.REVERSE_FIRST_ORDER_SIDE:
            self.logger.info("The REVERSE_FIRST_ORDER_SIDE config is set to True. The side will be reversed.")
            self.side = Side.LONG if self.side == Side.SHORT else Side.SHORT
    
        self.logger.info(f"The calculated first trading side is {self.side}.")
    
    def _get_precision_information_for_symbols(self) -> None:
        """Get precision information for all symbols concurrently."""
        with ThreadPoolExecutor(
            max_workers=len(szalai_strategy_config.TRADE_SYMBOLS)
        ) as executor:
            for symbol_precision_info in executor.map(self.client_manager.futures_get_symbol_precision_info, szalai_strategy_config.TRADE_SYMBOLS):   
                self.symbol_info_list.append(
                    Symbol(
                        symbol_precision_info["symbol"],
                        symbol_precision_info["pricePrecision"],
                        symbol_precision_info["quantityPrecision"],
                        symbol_precision_info["baseAssetPrecision"],
                        symbol_precision_info["quotePrecision"]
                    )
                )
    
    def _set_interval_trigger(self) -> None:
        """
        Set the interval trigger at the configured interval.
        """
        while not self.stop_event.is_set():
            try:
                # Sync OS time
                self._sync_os_time()

                # Ping the server
                self.client_manager.futures_ping_server()

                # If the ping was successful, set the state to CONNECTION_RESTORED if the current state is CONNECTION_LOST
                with self.state_lock:
                    if self.state == State.CONNECTION_LOST:
                        self.logger.info("Connection restored. Updating state to CONNECTION_RESTORED.")
                        self.state = State.CONNECTION_RESTORED
                
                # Get the server time from Binance
                server_time = self.client_manager.futures_get_server_time()

                # Calculate the next trigger time
                trigger_time = self._calculate_trigger_time(server_time)
                time_to_sleep = (trigger_time - server_time).total_seconds()

                if szalai_strategy_config.LOG_DEBUG_DATA:
                    self.logger.debug(f"Time to sleep: {time_to_sleep} seconds.")

                # Sleep until the next trigger time
                if time_to_sleep > 0:
                    self._precise_sleep_until(trigger_time)

                if self.stop_event.is_set():
                    break
        
                # Only set the state to COLLECTING_DATA if the current state is NO_TRADE
                with self.state_lock:
                    if self.state == State.NO_TRADE:
                        self.logger.info("Updating state to COLLECTING_DATA.")
                        self.state = State.COLLECTING_DATA

                self.logger.info(f"The configured {self.interval.value} interval has been triggered.")
            
            except Exception as e:
                if szalai_strategy_config.LOG_DEBUG_DATA:
                    self.logger.debug(f"Error during interval trigger: {type(e).__name__}: {e}\n{traceback.format_exc()}")

                self.logger.error(f"Connection has failed during interval trigger, retrying in {szalai_strategy_config.RETRY_INTERVAL} seconds.")
                with self.state_lock:
                    if self.state != State.CONNECTION_LOST:
                        self.logger.info("Updating state to CONNECTION_LOST.")
                        self.state = State.CONNECTION_LOST
                time.sleep(szalai_strategy_config.RETRY_INTERVAL)

    def _calculate_trigger_time(self, server_time: datetime) -> datetime:
        """
        Calculate the next trigger time based on the current interval and server time.
        
        Args:
            server_time (datetime): The current server time
            
        Returns:
            datetime: The next trigger time with the configured offset applied
        """
        offset_ms = szalai_strategy_config.TRIGGER_TIME_OFFSET
        next_trigger = self.interval.get_trigger_time(server_time, offset_ms)
        self.logger.info(f"Next trigger is set to {next_trigger}.")
        return next_trigger
    
    def _precise_sleep_until(self, target_time: datetime) -> None:
        """Sleep with higher precision until target time."""
        while True:
            current_time = datetime.now()
            time_diff = (target_time - current_time).total_seconds()
            
            if time_diff <= 0:
                break
                
            # Use shorter sleeps for the last 100ms for better precision
            if time_diff > 0.1:
                time.sleep(time_diff - 0.05)  # Sleep most of the time, leave 50ms buffer
            else:
                time.sleep(0.001)  # 1ms precision sleep for final adjustment

    def _sync_os_time(self) -> None:
        """
        Synchronizes the OS time on Windows platforms.
        
        This method attempts to synchronize the system clock on Windows using the w32tm utility.
        It logs the result of the synchronization attempt.
        """
        if sys.platform == "win32":

            if szalai_strategy_config.LOG_DEBUG_DATA:
                self.logger.debug("Synchronizing OS time on Windows.")

            try:
                import subprocess
                result = subprocess.run(
                    ['w32tm', '/resync', '/force'], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else f"Unknown error (code {result.returncode})"
                    self.logger.warning(f"Time synchronization failed: {error_msg}")
                else:
                    self.logger.info("OS time synchronization completed successfully.")
                    
            except Exception as e:
                self.logger.warning(f"Error during OS time sync: {e}")

    async def _check_open_orders_for_symbol(self, symbol: str, session: aiohttp.ClientSession) -> bool:
        """
        Check if there are open orders for a symbol.

        This method retrieves the open orders for the current trading symbol
        and returns a boolean indicating whether any open orders exist.

        Returns:
            bool: True if open orders exist, False otherwise.
        """

        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Checking open orders for symbol {symbol}.")

        open_orders = await self.client_manager.async_futures_get_current_all_open_orders(symbol, session)

        self.logger.info(f"There is {len(open_orders)} open order(s) for symbol {symbol}.")

        return bool(open_orders)

    async def _check_position_for_symbol(self, symbol: str, session: aiohttp.ClientSession) -> bool:
        """
        Check if there is a position for a symbol.

        This method retrieves the position information for the current trading symbol
        and returns a boolean indicating whether a position exists.

        Returns:
            bool: True if a position exists, False otherwise.
        """

        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Checking position for symbol {symbol}.")

        position_info = await self.client_manager.async_futures_get_position_information(symbol, session)

        # Filter out zero amount positions
        filtered_position_info = [pos for pos in position_info if float(pos["positionAmt"]) != 0.0]

        if filtered_position_info:
            self.logger.info(f"There is a position for symbol {symbol}.")
        else:
            self.logger.info(f"There is no position for symbol {symbol}.")

        return bool(filtered_position_info)

    async def _what_orders_are_open(self, symbol: str, session: aiohttp.ClientSession) -> list[OrderResponse]:
        """
        Get all open orders for a symbol.

        This method retrieves all open futures orders for the current trading symbol
        and returns a list of open orders.

        Returns:
            list[OrderResponse]: A list of open orders for the trading symbol.
        """

        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Checking what orders are open for symbol {symbol}.")

        # Check if the trading_symbol_take_profit_order and trading_symbol_stop_loss_order attributes exist
        if hasattr(self, 'trading_symbol_take_profit_order') and hasattr(self, 'trading_symbol_stop_loss_order'):
            # Get the orders from the strategy
            saved_symbol_orders = [self.trading_symbol_take_profit_order, self.trading_symbol_stop_loss_order]
            # Get all open orders for the symbol from exchange
            exchange_symbol_orders = await self.client_manager.async_futures_get_current_all_open_orders(symbol, session)
            # Filter the saved orders to include only those that are still open
            open_orders = [order for order in saved_symbol_orders if order.client_order_id in [order["clientOrderId"] for order in exchange_symbol_orders]]

            if szalai_strategy_config.LOG_DEBUG_DATA:
                self.logger.debug(f"Symbol {symbol} has the following open order(s): {open_orders}.")

            return open_orders
        
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"No open orders found for symbol {symbol}.")

        return []

    def _is_balance_change_limit_reached(self) -> bool:
        """
        Checks if the account balance change limit has been reached.

        This method compares the current account balance with the initial balance to determine if
        the maximum allowable positive or negative change has been exceeded. If so, it reinitializes
        the starting balance and returns True to indicate that the limit has been reached.
        """
        # Log the starting balance
        self.logger.info(f"Start account balance: {round(self.start_account_balance, szalai_strategy_config.LOGGING_PRECISION)}.")

        # Get the current account balance
        current_account_balance = self.client_manager.futures_get_account_balance(szalai_strategy_config.ACCOUNT_CURRENCY)
        self.logger.info(f"Current account balance: {round(current_account_balance, szalai_strategy_config.LOGGING_PRECISION)}.")

        # Calculate the percentage change in account balance
        balance_change_percentage = ((current_account_balance - self.start_account_balance) / self.start_account_balance) * 100
        self.logger.info(f"Account balance change: {round(balance_change_percentage, szalai_strategy_config.LOGGING_PRECISION)}%.")

        # Define the upper and lower balance change limits
        upper_balance_change_limit = szalai_strategy_config.MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE.percent_value
        lower_balance_change_limit = szalai_strategy_config.MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE.percent_value

        # Check if the balance change exceeds the allowed limits
        if balance_change_percentage >= upper_balance_change_limit:
            self.logger.info(f"Max positive account balance change of {szalai_strategy_config.MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE} has been reached by {self.trading_symbol} symbol.")
            self.logger.info(f"A new symbol is to be searched.")
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
            return True
        elif balance_change_percentage <= lower_balance_change_limit:
            self.logger.info(f"Max negative account balance change of {szalai_strategy_config.MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE} has been reached by {self.trading_symbol} symbol.")
            self.logger.info(f"A new symbol is to be searched.")
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
            return True
        else:
            self.logger.info(f"Trading continues with {self.trading_symbol} symbol.")
            return False

    def _check_change_rate(self) -> bool:
        # Check if the volatility change exceeds the minimum threshold
        if abs(self.trading_symbol_kline_data.percentage_change) >= szalai_strategy_config.MIN_CHANGE.percent_value:
            self.logger.info(f"The symbol {self.trading_symbol} has reached the preset minimal change of {szalai_strategy_config.MIN_CHANGE.percent_value}%.")
            return True
        else:
            self.logger.info(f"The symbol {self.trading_symbol} does not reach the preset minimal change of {szalai_strategy_config.MIN_CHANGE.percent_value}%.")
            return False

    async def _update_kline_data_for_all_symbol(self) -> None:
        """
        Gets the current kline data for all symbols listed in szalai_strategy_config concurrently.
        """
        # Calculate end time as current time rounded to the nearest minute
        end_time = datetime.now()
        end_time = end_time.replace(microsecond=0, second=0)
        
        # Calculate start time based on the interval's timedelta
        # This uses the timedelta property from the Interval enum, which correctly represents
        # the time difference for each interval type
        start_time = end_time - self.interval.timedelta
        
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Fetching kline data with start time: {start_time}, end time: {end_time}")

        # Get the optimized session from session manager
        session = self.session_manager.get_session()

        tasks = [
            self.client_manager.async_futures_get_kline_data(
                kline_data.symbol, self.interval.__str__(), 1, session, start_time, end_time
            ) 
            for kline_data in self.kline_data_list
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Pair each kline data with its corresponding result
        for kline_data, current_kline_data in zip(self.kline_data_list, results):
            # Check if its an Exception
            if isinstance(current_kline_data, Exception):
                self.logger.error(f"Error fetching kline data for {kline_data.symbol}: {current_kline_data}")
                continue              

            if current_kline_data and isinstance(current_kline_data, list) and len(current_kline_data) > 0:
                try:
                    kline_data.interval = self.interval.__str__()
                    kline_data.open_price = float(current_kline_data[0][1])
                    kline_data.high_price = float(current_kline_data[0][2])
                    kline_data.low_price = float(current_kline_data[0][3])
                    kline_data.close_price = float(current_kline_data[0][4])
                    kline_data.open_time = datetime.fromtimestamp(int(current_kline_data[0][0]) / 1000)
                    kline_data.close_time = datetime.fromtimestamp(int(current_kline_data[0][6]) / 1000)

                    # Log the kline data if kline data logging is enabled
                    if szalai_strategy_config.LOG_KLINE_DATA:
                        self.logger.kline_data( # type: ignore
                            f"Symbol: {kline_data.symbol}, "
                            f"Interval: {kline_data.interval}, "
                            f"Open Time: {kline_data.open_time}, "
                            f"Close Time: {kline_data.close_time}, "
                            f"Open: {round(kline_data.open_price, szalai_strategy_config.LOGGING_PRECISION)}, "
                            f"High: {round(kline_data.high_price, szalai_strategy_config.LOGGING_PRECISION)}, "
                            f"Low: {round(kline_data.low_price, szalai_strategy_config.LOGGING_PRECISION)}, "
                            f"Close: {round(kline_data.close_price, szalai_strategy_config.LOGGING_PRECISION)}, "
                            f"Change: {round(kline_data.change, szalai_strategy_config.LOGGING_PRECISION)}, "
                            f"Percentage Change: {round(kline_data.percentage_change, szalai_strategy_config.LOGGING_PRECISION)}%, "
                            f"Raw Data: {current_kline_data}"
                        )

                except (IndexError, ValueError, TypeError) as e:
                    self.logger.error(f"Error processing kline data for {kline_data.symbol}: {e}")
                    continue

    async def _set_up_orders(self) -> OrderErrorCode:
        """
        Sets up the initial orders for the trading symbol.

        This method creates a market order to buy or sell the trading symbol based on the trading side.
        It also sets up the stop loss and take profit orders for the position.

        Returns:
            OrderErrorCode: Indicates success or the specific failure point
        """
        self.logger.info(f"Setting up orders for symbol {self.trading_symbol}.")
        # TODO: check if there is enough balance to place the order

        # Get the optimized session from session manager
        session = self.session_manager.get_session()

        try:          
            try:
                self.trading_symbol_position_order = await self._create_position_order(self.trading_symbol, self.trading_symbol_quantity, self.side, session)
                self.order_list.extend([self.trading_symbol_position_order])
            except Exception as e:
                self.logger.error(f"Error creating position order: {e}")
                return OrderErrorCode.POSITION_ORDER_FAILED

            order_results = await asyncio.gather(
                self._create_take_profit_order(self.trading_symbol, self.trading_symbol_position_order.average_price, self.side, session),
                self._create_stop_loss_order(self.trading_symbol, self.trading_symbol_position_order.average_price, self.side, session),
                return_exceptions=True
            )

            # Check if orders were created successfully
            if isinstance(order_results[0], Exception) and isinstance(order_results[1], Exception):
                self.logger.error("Both take profit and stop loss orders failed.")
                self.logger.error(f"Take profit order creation errror: {order_results[0]}")
                self.logger.error(f"Stop loss order creation error: {order_results[1]}")
                return OrderErrorCode.BOTH_ORDERS_FAILED
            
            if isinstance(order_results[0], Exception):
                self.logger.error(f"Take profit order creation failed: {order_results[0]}")
                return OrderErrorCode.TAKE_PROFIT_ORDER_FAILED
            
            if isinstance(order_results[1], Exception):
                self.logger.error(f"Stop loss order creation failed: {order_results[1]}")
                return OrderErrorCode.STOP_LOSS_ORDER_FAILED

            # Process the take profit and stop loss order results
            for i, result in enumerate(order_results):             
                # Store the take profit order result
                if i == 0 and result and isinstance(result, OrderResponse):                    
                    self.trading_symbol_take_profit_order = result
                    self.order_list.append(self.trading_symbol_take_profit_order)
                # Store the stop loss order result
                elif i == 1 and result and isinstance(result, OrderResponse):
                    self.trading_symbol_stop_loss_order = result
                    self.order_list.append(self.trading_symbol_stop_loss_order)

            return OrderErrorCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Error setting up orders for symbol {self.trading_symbol}: {e}")
            return OrderErrorCode.UNKNOWN_ERROR

    def _calculate_quantity(self) -> None:
        """
        Calculates the trading quantity for a symbol.

        This method calculates the necessary trading quantity from the configured USD amount to risk.
        """
        symbol_info_dict = {symbol_info.symbol: symbol_info for symbol_info in self.symbol_info_list}
        quantity_precision = symbol_info_dict[self.trading_symbol_kline_data.symbol].quantity_precision

        try:
            self.trading_symbol_quantity = round(szalai_strategy_config.RISK_USD / self.trading_symbol_kline_data.close_price, quantity_precision)
            self.logger.info(
            f"The calculated quantity of symbol {self.trading_symbol_kline_data.symbol} " 
            f"from {szalai_strategy_config.RISK_USD} USD is {self.trading_symbol_quantity}."
        )
        except ZeroDivisionError:
            self.logger.error(f"Error calculating quantity for symbol {self.trading_symbol_kline_data.symbol}: Division by zero.")
            self.trading_symbol_quantity = 0.0

    async def _close_open_position_for_symbol(self, symbol: str, session: aiohttp.ClientSession) -> None:
        """
        Closes open position for a specified symbol.

        This method creates a market order to close any open position for the given symbol.
        """
        self.logger.info(f"Closing all open positions for {symbol}.")

        position_info = await self.client_manager.async_futures_get_position_information(symbol, session)

        if position_info:
            position_amount = float(next((x["positionAmt"] for x in position_info), 0))

            if position_amount > 0:
                sell_market_order = await self.client_manager.async_futures_create_sell_market_order(symbol, position_amount, session)
                self.order_list.append(sell_market_order)

            if position_amount < 0:
                buy_market_order = await self.client_manager.async_futures_create_buy_market_order(symbol, abs(position_amount), session)
                self.order_list.append(buy_market_order)

    async def _cancel_open_orders_for_symbol(self, symbol: str, session: aiohttp.ClientSession) -> None:
        """
        Cancel open orders for a specified symbol.

        This method cancels all open orders for the given symbol.
        """
        self.logger.info(f"Cancel all open orders for {symbol}.")

        await self.client_manager.async_futures_cancel_all_open_orders(symbol, session)

    async def _cancel_open_order_for_symbol(self, symbol: str, order_id: str, session: aiohttp.ClientSession) -> None:
        """
        Cancel an open order for a specified symbol.

        This method cancels an open order for the given symbol.
        """
        self.logger.info(f"Cancel order {order_id} for {symbol}.")

        await self.client_manager.async_futures_cancel_order(symbol, order_id, session)

    async def _close_open_position_and_cancel_orders_for_symbol(self, symbol: str, session: aiohttp.ClientSession) -> None:
        """
        Closes all open positions and orders for a specified symbol.

        This method cancels all open orders and closes any positions by creating a market
        order for the remaining position amount.
        """
        self.logger.info(f"Closing all open positions and orders for {symbol}.")
        
        try:
            # Execute both tasks concurrently
            await asyncio.gather(
                self._cancel_open_orders_for_symbol(symbol, session),
                self._close_open_position_for_symbol(symbol, session),
            )

        except Exception as e:
            self.logger.error(f"Error closing position and orders for symbol {symbol}: {e}")
            raise 

    async def _close_open_positions_and_cancel_orders_for_all_symbols(self, session: aiohttp.ClientSession) -> None:
        """
        Closes open positions and cancels all orders for all symbols listed in the configuration.

        This method iterates through each trading symbol and:
        - Cancels all open orders
        - Closes any remaining positions by creating market orders
        """
        self.logger.info("Closing open positions and cancel orders for all symbols.")
        
        try:
            # Create a list of tasks for closing positions and canceling orders
            tasks = []

            # Create a task for each symbol
            for symbol in szalai_strategy_config.TRADE_SYMBOLS:
                tasks.append(self._close_open_position_and_cancel_orders_for_symbol(symbol, session))

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

        except Exception as e:
            self.logger.error(f"Error closing positions and orders for all symbols: {e}")
            raise

    def _update_order_data_handler(self, message: dict) -> None:
        """
        Updates the order data based on the incoming WebSocket message.

        This method processes order trade updates, adjusts the status of existing orders, and
        sets flags for checking profit and orders as necessary.
        """
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Trade update, message: {message}.")

        event_type = message.get("e")
        client_order_id = message.get("o", {}).get("c", None)

        if event_type == "ORDER_TRADE_UPDATE" and any(order.client_order_id == client_order_id for order in self.order_list):
            status = message.get("o", {}).get("X", None)
            update_time = message.get("o", {}).get("T", None)

            order = next(order for order in self.order_list if order.client_order_id == client_order_id)
            order.status = status
            order.update_time = update_time

            if szalai_strategy_config.LOG_DEBUG_DATA:
                self.logger.debug(f"Order has been updated, {order}.")
            
            with self.state_lock:
                if order.type == "TAKE_PROFIT_MARKET" and order.status == "FILLED":
                    self.logger.info(f"{order.type} order has been filled.")
                    self.logger.info(f"Updating state to TAKE_PROFIT_ORDER_FILLED.")
                    self.state = State.TAKE_PROFIT_ORDER_FILLED
                    return

                if order.type == "STOP_MARKET" and order.status == "FILLED":
                    self.logger.info(f"{order.type} order has been filled.")
                    self.logger.info(f"Updating state to STOP_MARKET_ORDER_FILLED.")
                    self.state = State.STOP_MARKET_ORDER_FILLED
                    return

                if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "CANCELED":
                    if szalai_strategy_config.LOG_DEBUG_DATA:
                        self.logger.debug(f"{order.type} order has been canceled.")

    async def _create_position_order(self, symbol: str, quantity: float, side: Side, session: aiohttp.ClientSession) -> OrderResponse:
        """
        Creates a position order for the specified symbol, quantity, and trading side.

        This method generates a market order to either buy or sell based on the side.
        """
        self.logger.info(f"Creating position order, symbol: {symbol}, quantity: {quantity}, side: {side.name}.")
        if side == Side.LONG:
            return await self.client_manager.async_futures_create_buy_market_order(symbol, quantity, session)
        else:
            return await self.client_manager.async_futures_create_sell_market_order(symbol, quantity, session)

    async def _create_take_profit_order(self, symbol: str, position_price: float, side: Side, session: aiohttp.ClientSession) -> OrderResponse:
        """
        Creates a take profit order for the specified symbol, price, and trading side.

        This method calculates the take profit price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        tp_price = round(self._calculate_take_profit_price(position_price, side), price_precision)
        self.logger.info(f"Creating take profit order, symbol: {symbol}, price: {numpy.format_float_positional(tp_price)}, side: {side.name}.")
        if self.side == Side.LONG:
            return await self.client_manager.async_futures_create_sell_take_profit_market_order(symbol, tp_price, session)
        else:
            return await self.client_manager.async_futures_create_buy_take_profit_market_order(symbol, tp_price, session)

    async def _create_stop_loss_order(self, symbol: str, position_price: float, side: Side, session: aiohttp.ClientSession) -> OrderResponse:
        """
        Creates a stop loss order for the specified symbol, price, and trading side.

        This method calculates the stop loss price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        sl_price = round(self._calculate_stop_loss_price(position_price, side), price_precision)
        self.logger.info(f"Creating stop loss order, symbol: {symbol}, price: {numpy.format_float_positional(sl_price)}, side: {side.name}.")
        if self.side == Side.LONG:
            return await self.client_manager.async_futures_create_sell_stop_market_order(symbol, sl_price, session)
        else:
            return await self.client_manager.async_futures_create_buy_stop_market_order(symbol, sl_price, session)

    def _get_most_volatile_symbol(self) -> None:
        """ 
        Retrieves the most volatile symbol from the kline data list.

        This method determines the most volatile symbol based on the highest price change.
        """
        self.trading_symbol_kline_data = max(self.kline_data_list, key=lambda x: abs(x.change))
        self.trading_symbol = self.trading_symbol_kline_data.symbol
        self.logger.info(f"Most volatile symbol is {self.trading_symbol_kline_data.symbol}, change is {round(self.trading_symbol_kline_data.percentage_change, szalai_strategy_config.LOGGING_PRECISION)}%.")

    def _calculate_take_profit_price(self, price: float, side: Side) -> float:
        """
        Calculates the take profit price based on the current price and trading side.

        This method adjusts the price according to the take profit multiplier configured in
        the strategy configuration.
        """
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Calculating take profit price, price: {numpy.format_float_positional(price)}, side: {side.name}.")

        if side == Side.LONG:
            tp_price = price + (price * szalai_strategy_config.TAKE_PROFIT_MULTIPLIER.decimal_value)
        else:
            tp_price = price - (price * szalai_strategy_config.TAKE_PROFIT_MULTIPLIER.decimal_value)

        if szalai_strategy_config.LOG_DEBUG_DATA:    
            self.logger.debug(f"Take profit price is {numpy.format_float_positional(tp_price)}.")

        return tp_price

    def _calculate_stop_loss_price(self, price: float, side: Side) -> float:
        """
        Calculates the stop loss price based on the current price and trading side.

        This method adjusts the price according to the stop loss multiplier configured in
        the strategy configuration.
        """
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Calculating stop loss price, price: {numpy.format_float_positional(price)}, side: {side.name}.")
        
        if side == Side.LONG:
            sl_price = price - (price * szalai_strategy_config.STOP_LOSS_MULTIPLIER.decimal_value)
        else:
            sl_price = price + (price * szalai_strategy_config.STOP_LOSS_MULTIPLIER.decimal_value)

        if szalai_strategy_config.LOG_DEBUG_DATA:    
            self.logger.debug(f"Stop loss price is {numpy.format_float_positional(sl_price)}.")

        return sl_price

    def _init_logger(self) -> Logger:
        """
        Initializes the logger for the Szalai strategy.

        This method sets up the logger with different handlers for console output and file
        logging. It includes separate files for informational and debug logging.
        """

        # Define custom log level for kline data
        KLINE_DATA = 15  # Between DEBUG (10) and INFO (20)
        logging.addLevelName(KLINE_DATA, "KLINE_DATA")
        
        # Create a method for the custom level
        def kline_data(self, message, *args, **kwargs):
            """Log kline data events at custom level between DEBUG and INFO"""
            if self.isEnabledFor(KLINE_DATA):
                self._log(KLINE_DATA, message, args, **kwargs)
        
        # Add the method to the Logger class
        setattr(logging.Logger, 'kline_data', kline_data)

        # Create a queue for log messages (this makes logging non-blocking)
        log_queue = queue.Queue(maxsize=10000)

        # Create the main logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Create a queue handler to handle log messages asynchronously
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)

        # Create actual handlers (these will run in background thread)
        handlers = []

        # Console handler for info level logs
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("[%(asctime)s, %(threadName)s, %(levelname)s] %(message)s"))
        handlers.append(console_handler)

        # File handler for info level logs
        file_info_name = f"szalai_strategy_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        file_info_handler = logging.FileHandler(filename=file_info_name)
        file_info_handler.setFormatter(logging.Formatter("[%(asctime)s, %(threadName)s, %(levelname)s] %(message)s"))
        file_info_handler.setLevel(logging.INFO)
        handlers.append(file_info_handler)

        # File handler for debug level logs
        if szalai_strategy_config.LOG_DEBUG_DATA:
            file_debug_name = f"szalai_strategy_debug_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
            file_debug_handler = logging.FileHandler(filename=file_debug_name)
            file_debug_handler.setFormatter(logging.Formatter("[%(asctime)s, %(threadName)s, %(funcName)s, %(levelname)s] %(message)s"))
            file_debug_handler.setLevel(logging.DEBUG)
            handlers.append(file_debug_handler)

        # File handler for kline data logs
        if szalai_strategy_config.LOG_KLINE_DATA:
            file_kline_data_name = f"szalai_strategy_kline_data_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
            file_kline_data_handler = logging.FileHandler(filename=file_kline_data_name)
            file_kline_data_handler.setFormatter(logging.Formatter("[%(asctime)s, %(threadName)s, %(funcName)s, %(levelname)s] %(message)s"))
            file_kline_data_handler.setLevel(KLINE_DATA)

            # Add a filter to only include KLINE_DATA level messages
            class KlineDataFilter(logging.Filter):
                def filter(self, record):
                    return record.levelno == KLINE_DATA  # Only log messages exactly at KLINE_DATA level

            file_kline_data_handler.addFilter(KlineDataFilter())
            handlers.append(file_kline_data_handler)

        # Start the queue listener in a background thread
        self.queue_listener = QueueListener(
            log_queue, 
            *handlers,
            respect_handler_level=True
          )
        self.queue_listener.start()  

        return logger
