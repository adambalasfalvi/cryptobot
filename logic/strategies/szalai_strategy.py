import os
import sys
import logging
import logging.handlers
import time
import threading
import asyncio
import aiohttp
import queue
from datetime import datetime
from datetime import timedelta
from logging import Logger
from concurrent.futures import ThreadPoolExecutor
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
from requests.exceptions import ReadTimeout

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
        self.logger = self.__init_logger() 
        self.client_manager = BinanceClientManager(logger=self.logger)
        self.websocket_manager = BinanceWebsocketManager(logger=self.logger)
        self.side : Side
        self.state: State = State.INIT
        self.state_lock : Lock = Lock()
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


    def start_strategy(self) -> None:
        # Initialize the strategy
        self.__init_strategy()

        # Run the strategy
        asyncio.run(self.__run_strategy())

    def stop_strategy(self) -> None:
        """
        Stops the Szalai trading strategy.

        This method logs the stop event, stops the WebSocket connections, and closes all open positions
        and orders to halt trading activities.
        """
        self.logger.info("Stopping Szalai strategy...")
        with self.state_lock:
            self.state = State.STOPPED
        # Set the stop event to signal the run_strategy loop to exit
        self.stop_event.set()
        # Stop the WebSocket manager to cease receiving data
        self.websocket_manager.stop_websocket()
        # Close all open positions and orders for all symbols
        self.__close_open_positions_and_orders_for_all_symbols()
        # Wait for the interval trigger thread to complete
        self.interval_trigger_thread.join()
        self.logger.info("Szalai strategy has stopped.")
    
    def __init_strategy(self) -> None:
        # Log the start of the strategy execution
        self.logger.info("Starting Szalai strategy.")

        # Fetch and store the initial account balance
        self.start_account_balance = self.client_manager.futures_get_account_balance(szalai_strategy_config.ACCOUNT_CURRENCY)
        self.logger.info(f"Start account balance is {self.start_account_balance} {szalai_strategy_config.ACCOUNT_CURRENCY}.")

        # Set the leverage for each trading symbol
        with ThreadPoolExecutor(max_workers=len(szalai_strategy_config.TRADE_SYMBOLS)) as executor:
            for symbol in szalai_strategy_config.TRADE_SYMBOLS:
                # Submit a task to change the leverage for each symbol to the configured value
                executor.submit(self.client_manager.futures_change_leverage, symbol, szalai_strategy_config.LEVERAGE)
        
        # Start the interval trigger thread
        self.interval_trigger_thread = threading.Thread(target=self.__set_interval_trigger)
        self.interval_trigger_thread.start()

        # Start the WebSocket manager to receive real-time updates for market data and user data
        self.websocket_manager.start_websocket()

        # Set up the WebSocket for user data to receive order updates and provide a handler for updates
        self.websocket_manager.setup_user_data_websocket(
            self.__update_order_data_handler           # Handler method to process order data updates
        )

    async def __run_strategy(self) -> None:
        # Main strategy loop to continuously check and act upon various conditions until the stop event is set
        while not self.stop_event.is_set():
            with self.state_lock:
                match self.state:
                    case State.INIT:
                        self.__get_precision_information_for_symbols()
                        self.__close_open_positions_and_orders_for_all_symbols()
                        self.logger.info("Updating state to NO_TRADE.")
                        self.state = State.NO_TRADE
                    case State.NO_TRADE:
                        # Wait for the interval trigger to set the state to COLLECTING_DATA
                        pass
                    case State.COLLECTING_DATA:
                        await self.__update_kline_data_for_all_symbol()
                        self.__get_most_volatile_symbol()
                        if self.__check_change_rate():
                            await self.__calculate_first_side()
                            self.logger.info("Updating state to TAKING_POSITION.")
                            self.state = State.TAKING_POSITION
                        else:
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                    case State.TAKING_POSITION:               
                        self.__calculate_quantity()
                        if await self.__set_up_orders():
                            self.logger.info("Updating state to TRADE.")
                            self.state = State.TRADE
                        else:
                            self.__close_open_positions_and_orders_for_symbol(self.trading_symbol)
                    case State.TRADE:
                        # Waiting for the order to be filled
                        pass
                    case State.ORDER_FILLED:
                        if self.__is_balance_change_limit_reached():
                            self.__close_open_positions_and_orders_for_symbol(self.trading_symbol)
                            self.logger.info("Updating state to NO_TRADE.")
                            self.state = State.NO_TRADE
                        else:
                            self.__close_open_positions_and_orders_for_symbol(self.trading_symbol)
                            self.logger.info("Updating state to TAKING_POSITION.")
                            self.state = State.TAKING_POSITION
                    case State.FIRST_ORDER_CANCELED:
                        self.__close_open_positions_and_orders_for_symbol(self.trading_symbol)
                        self.logger.info("Updating state to WAITING_FOR_SECOND_ORDER_CANCEL.")
                        self.state = State.WAITING_FOR_SECOND_ORDER_CANCEL
                    case State.WAITING_FOR_SECOND_ORDER_CANCEL:
                        # Wait for the second order to be canceled in __update_order_data_handler
                        pass
                    case State.SECOND_ORDER_CANCELED:
                        self.logger.info("Updating state to TAKING_POSITION.")
                        self.state = State.TAKING_POSITION
                    case State.CONNECTION_LOST:
                        # Waiting until connection is restored
                        pass
                    case State.CONNECTION_RESTORED:
                        if self.__how_many_orders_are_open(self.trading_symbol) != 2:
                            self.__close_open_positions_and_orders_for_symbol(self.trading_symbol)
                            self.logger.info("Updating state to TAKING_POSITION.")
                            self.state = State.TAKING_POSITION
                        else:
                            self.logger.info("Updating state to TRADE.")
                            self.state = State.TRADE
                    case State.STOPPED:
                        pass
    
    async def __calculate_first_side(self) -> None:
        """
        Calculates what will be the side to begin with if a new symbol has been chosen.

        This method retrieves the historical kline data for the trading symbol and determines the starting side.
        If the price has increased (close price is higher than open price), the starting side will be SHORT.
        If the price has declined (close price is lower than open price), the starting side will be LONG.
        """   
        symbol_kline_data = next(kline_data for kline_data in self.kline_data_list if kline_data.symbol == self.trading_symbol)

        # If price has increased
        if symbol_kline_data.open_price - symbol_kline_data.close_price < 0:
            self.side = Side.SHORT
        # If declined
        else:
            self.side = Side.LONG
        
        self.logger.info(f"The calculated first trading side is {self.side}.")
    
    def __get_precision_information_for_symbols(self) -> None:
        """Get precision information for all symbols concurrently."""
        with ThreadPoolExecutor(max_workers=len(szalai_strategy_config.TRADE_SYMBOLS)) as executor:
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

    def __calculate_trigger_time(self, server_time: datetime) -> None:
        """Calculate the next trigger time based on the interval."""
        if self.interval == Interval.ONE_MINUTE:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.THREE_MINUTES:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.FIVE_MINUTES:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.FIFTEEN_MINUTES:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.THIRTY_MINUTES:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.ONE_HOUR:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.TWO_HOURS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.FOUR_HOURS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.SIX_HOURS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.EIGHT_HOURS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.TWELVE_HOURS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.ONE_DAY:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.THREE_DAYS:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.ONE_WEEK:
            next_trigger = server_time + self.interval.timedelta
        elif self.interval == Interval.ONE_MONTH:
            next_trigger = server_time.replace(day=1) + self.interval.timedelta
            next_trigger = next_trigger.replace(day=1)

        next_trigger = next_trigger.replace(second=0, microsecond=0)
        self.logger.info(f"Next trigger is set to {next_trigger}.")
        return next_trigger
    
    def __set_interval_trigger(self) -> None:
        """
        Set the interval trigger at the configured interval.
        """
        while not self.stop_event.is_set():
            try:
                server_time = self.client_manager.futures_get_server_time()

                # Only set the state to CONNECTION_RESTORED if the current state is CONNECTION_LOST
                with self.state_lock:
                    if self.state == State.CONNECTION_LOST:
                        self.logger.info("Connection restored. Updating state to CONNECTION_RESTORED.")
                        self.state = State.CONNECTION_RESTORED

                trigger_time = self.__calculate_trigger_time(server_time)
                time_to_sleep = (trigger_time - server_time).total_seconds()
                self.logger.debug(f"Time to sleep: {time_to_sleep} seconds.")

                # Sleep until the next trigger time
                if time_to_sleep > 0:
                    time.sleep(time_to_sleep)

                if self.stop_event.is_set():
                    break
        
                # Only set the state to COLLECTING_DATA if the current state is NO_TRADE
                with self.state_lock:
                    if self.state == State.NO_TRADE:
                        self.logger.info("Updating state to COLLECTING_DATA.")
                        self.state = State.COLLECTING_DATA

                self.logger.info(f"The configured {self.interval.value} interval has been triggered.")
            
            except Exception as e:
                self.logger.error(f"Internet connection has been lost, retry in {szalai_strategy_config.RETRY_INTERVAL} seconds.")
                with self.state_lock:
                    if self.state != State.CONNECTION_LOST:
                        self.logger.info("Updating state to CONNECTION_LOST.")
                        self.state = State.CONNECTION_LOST
                time.sleep(szalai_strategy_config.RETRY_INTERVAL)

    def __how_many_orders_are_open(self, symbol: str) -> int:
        """
        Get the number of open orders for a symbol.

        This method retrieves all open futures orders for the current trading symbol
        and returns the number of open orders.

        Returns:
            int: The number of open orders for the trading symbol.
        """
        self.logger.debug(f"Checking how many open orders are for symbol {symbol}.")
        symbol_orders = self.client_manager.futures_get_current_all_open_orders(symbol)
        self.logger.debug(f"Symbol {symbol} has {len(symbol_orders)} open order(s).")
        return len(symbol_orders)


    def __is_balance_change_limit_reached(self) -> bool:
        """
        Checks if the account balance change limit has been reached.

        This method compares the current account balance with the initial balance to determine if
        the maximum allowable positive or negative change has been exceeded. If so, it reinitializes
        the starting balance and returns True to indicate that the limit has been reached.
        """
        # Get the current account balance
        current_account_balance = self.client_manager.futures_get_account_balance(szalai_strategy_config.ACCOUNT_CURRENCY)
        self.logger.info(f"Current account balance is {current_account_balance}.")
        # Calculate the change in account balance
        account_balance_change = current_account_balance / self.start_account_balance
        self.logger.info(f"Account balance change is {account_balance_change}.")
        # Calculate the max positive and max negative balance changes
        max_positive_balance_change = 1 + szalai_strategy_config.MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE
        max_negative_balance_change = 1 - szalai_strategy_config.MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE      
        # Check if the change exceeds the maximum allowed
        if account_balance_change > max_positive_balance_change:
            self.logger.info(f"Max positive account balance change of {szalai_strategy_config.MAX_POSITIVE_ACCOUNT_BALANCE_CHANGE} has been reached.")
            self.logger.info(f"A new symbol is to be searched.")
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
            return True
        elif max_negative_balance_change > account_balance_change:
            self.logger.info(f"Max negative account balance change of {szalai_strategy_config.MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE} has been reached.")
            self.logger.info(f"A new symbol is to be searched.")
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
            return True
        else:
            self.logger.info(f"Trading continues with {self.trading_symbol} symbol.")
            return False

    def __check_change_rate(self) -> bool:
        # Check if the volatility change exceeds the minimum threshold
        if self.trading_symbol_kline_data.change >= szalai_strategy_config.MIN_CHANGE:
            self.logger.info(f"The symbol {self.trading_symbol} has reached the preset minimal change of {szalai_strategy_config.MIN_CHANGE}.")
            return True
        else:
            self.logger.info(f"The symbol {self.trading_symbol} does not reach the preset minimal change of {szalai_strategy_config.MIN_CHANGE}.")
            return False

    async def __update_kline_data_for_all_symbol(self) -> None:
        """
        Gets the current kline data for all symbols listed in szalai_strategy_config concurrently.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.client_manager.async_futures_get_kline_data(
                    kline_data.symbol, self.interval.__str__(), 1, session
                ) 
                for kline_data in self.kline_data_list
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Pair each kline data with its corresponding result
            for kline_data, current_kline_data in zip(self.kline_data_list, results):
                # Check if its an Exception
                if isinstance(current_kline_data, Exception):
                    self.logger.error(f"Error fetching kline data for {kline_data.symbol}: {current_kline_data}")

                if current_kline_data:
                    kline_data.interval = self.interval.__str__()
                    kline_data.open_price = float(current_kline_data[0][1])
                    kline_data.high_price = float(current_kline_data[0][2])
                    kline_data.low_price = float(current_kline_data[0][3])
                    kline_data.close_price = float(current_kline_data[0][4])
                    kline_data.open_time = datetime.fromtimestamp(current_kline_data[0][0] / 1000)
                    kline_data.close_time = datetime.fromtimestamp(current_kline_data[0][6] / 1000)

    async def __set_up_orders(self) -> bool:
        """
        Sets up the initial orders for the trading symbol.

        This method creates a market order to buy or sell the trading symbol based on the trading side.
        It also sets up the stop loss and take profit orders for the position.
        """
        self.logger.info(f"Setting up orders for symbol {self.trading_symbol}.")
        try:
            async with aiohttp.ClientSession() as session:
                await self.__create_position_order(self.trading_symbol, self.trading_symbol_quantity, self.side, session)

                await asyncio.gather(
                    self.__create_stop_loss_order(self.trading_symbol, self.trading_symbol_position_order.average_price, self.side, session),
                    self.__create_take_profit_order(self.trading_symbol, self.trading_symbol_position_order.average_price, self.side, session)
                )
            return True
        except Exception as e:
            self.logger.error(f"Error setting up orders for symbol {self.trading_symbol}: {e}")
            return False

    def __calculate_quantity(self) -> None:
        """
        Calculates the trading quantity for a symbol.

        This method calculates the necessary trading quantity from the configured USD amount to risk.
        """
        symbol_info_dict = {symbol_info.symbol: symbol_info for symbol_info in self.symbol_info_list}
        quantity_precision = symbol_info_dict[self.trading_symbol_kline_data.symbol].quantity_precision
        self.trading_symbol_quantity = round(szalai_strategy_config.RISK_USD / self.trading_symbol_kline_data.close_price, quantity_precision)
        self.logger.info(
            f"The calculated quantity of symbol {self.trading_symbol_kline_data.symbol} " 
            f"from {szalai_strategy_config.RISK_USD} USD is {self.trading_symbol_quantity}."
        )
    
    def __close_open_positions_and_orders_for_symbol(self, symbol: str) -> None:
        """
        Closes all open positions and orders for a specified symbol.

        This method cancels all open orders and closes any positions by creating a market
        order for the remaining position amount.
        """
        self.logger.info(f"Closing all open positions and orders for {symbol}.")
        with ThreadPoolExecutor() as executor:
            # Cancel all open orders for the symbol
            cancel_future = executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol)

            # Get position information and close any open positions
            position_info_future = executor.submit(self.client_manager.futures_get_position_information, symbol)
            position_info_result = position_info_future.result()
            position_amount = float(next((x["positionAmt"] for x in position_info_result)))

            # If the position amount is positive, sell it
            if position_amount > 0:
                sell_market_order = self.client_manager.futures_create_sell_market_order(symbol, position_amount)
                self.order_list.append(sell_market_order)

            # If the position amount is negative, buy it
            if position_amount < 0:
                buy_market_order = self.client_manager.futures_create_buy_market_order(symbol, abs(position_amount))
                self.order_list.append(buy_market_order)

            # Wait for the cancel future to complete
            cancel_future.result()

    def __close_open_positions_and_orders_for_all_symbols(self) -> None:
        """
        Closes all open positions and orders for all symbols.

        This method iterates through each trading symbol and:
        - Cancels all open orders
        - Closes any remaining positions by creating market orders
        """
        self.logger.info("Closing all open positions and orders for all symbols.")
        with ThreadPoolExecutor(max_workers=len(szalai_strategy_config.TRADE_SYMBOLS) * 2) as executor:

            # Cancel all open orders for all symbols concurrently
            cancel_futures = {symbol: executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol) for symbol in szalai_strategy_config.TRADE_SYMBOLS}
            
            # Get position information and close any positions for all symbols concurrently
            position_info_futures = {symbol: executor.submit(self.client_manager.futures_get_position_information, symbol) for symbol in szalai_strategy_config.TRADE_SYMBOLS}
            
            # Get position information and close any positions for all symbols concurrently
            for symbol, future in position_info_futures.items():
                position_info_result = future.result()
                position_amount = float(next(x["positionAmt"] for x in position_info_result))

                # If the position amount is positive, sell it
                if position_amount > 0:
                    sell_market_order = self.client_manager.futures_create_sell_market_order(symbol, position_amount)
                    self.order_list.append(sell_market_order)

                # If the position amount is negative, buy it
                if position_amount < 0:
                    buy_market_order = self.client_manager.futures_create_buy_market_order(symbol, abs(position_amount))
                    self.order_list.append(buy_market_order)
            
            # Wait for all cancel futures to complete
            for symbol, future in cancel_futures.items():
                future.result()

    def __update_order_data_handler(self, message: str) -> None:
        """
        Updates the order data based on the incoming WebSocket message.

        This method processes order trade updates, adjusts the status of existing orders, and
        sets flags for checking profit and orders as necessary.
        """
        self.logger.debug(f"Trade update, message: {message}.")
        event_type = message.get("e")
        client_order_id = message.get("o", {}).get("c", None)

        with self.state_lock:
            if event_type == "ORDER_TRADE_UPDATE" and any(order.client_order_id == client_order_id for order in self.order_list):
                status = message.get("o").get("X")
                order = next(order for order in self.order_list if order.client_order_id == client_order_id)
                order.status = status
                self.logger.debug(f"Order has been updated, {order}.")

                if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "CANCELED":
                    self.logger.info(f"{order.type} order has been canceled, {order}.")
                    self.logger.info(f"Updating state to ORDER_CANCELED.")

                    if self.state == State.STOPPED:
                        return

                    if self.state == State.WAITING_FOR_SECOND_ORDER_CANCEL:
                        self.logger.info("Updating state to SECOND_ORDER_CANCELED.")
                        self.state = State.SECOND_ORDER_CANCELED
                    else:
                        self.logger.info("Updating state to FIRST_ORDER_CANCELED.")
                        self.state = State.FIRST_ORDER_CANCELED

                if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "FILLED":
                    self.logger.info(f"{order.type} order has been filled, {order}.")
                    self.logger.info(f"Updating state to ORDER_FILLED.")
                    self.state = State.ORDER_FILLED

    async def __create_position_order(self, symbol: str, quantity: float, side: Side, session: aiohttp.ClientSession) -> None:
        """
        Creates a position order for the specified symbol, quantity, and trading side.

        This method generates a market order to either buy or sell based on the side.
        """
        self.logger.info(f"Creating position order, symbol: {symbol}, quantity: {quantity}, side: {side.name}.")
        if side == Side.LONG:
            self.trading_symbol_position_order = await self.client_manager.async_futures_create_buy_market_order(symbol, quantity, session)
        else:
            self.trading_symbol_position_order = await self.client_manager.async_futures_create_sell_market_order(symbol, quantity, session)

        self.order_list.extend([self.trading_symbol_position_order])

    async def __create_take_profit_order(self, symbol: str, position_price: float, side: Side, session: aiohttp.ClientSession) -> None:
        """
        Creates a take profit order for the specified symbol, price, and trading side.

        This method calculates the take profit price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        tp_price = round(self.__calculate_take_profit_price(position_price, side), price_precision)
        self.logger.info(f"Creating take profit order, symbol: {symbol}, price: {tp_price}, side: {side.name}.")
        if self.side == Side.LONG:
            self.trading_symbol_take_profit_order = await self.client_manager.async_futures_create_sell_take_profit_market_order(symbol, tp_price, session)
        else:
            self.trading_symbol_take_profit_order = await self.client_manager.async_futures_create_buy_take_profit_market_order(symbol, tp_price, session)

        self.order_list.extend([self.trading_symbol_take_profit_order])

    async def __create_stop_loss_order(self, symbol: str, position_price: float, side: Side, session: aiohttp.ClientSession) -> None:
        """
        Creates a stop loss order for the specified symbol, price, and trading side.

        This method calculates the stop loss price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        sl_price = round(self.__calculate_stop_loss_price(position_price, side), price_precision)
        self.logger.info(f"Creating stop loss order, symbol: {symbol}, position price: {sl_price}, side: {side.name}.")
        if self.side == Side.LONG:
            self.trading_symbol_stop_loss_order = await self.client_manager.async_futures_create_sell_stop_market_order(symbol, sl_price, session)
        else:
            self.trading_symbol_stop_loss_order = await self.client_manager.async_futures_create_buy_stop_market_order(symbol, sl_price, session)

        self.order_list.extend([self.trading_symbol_stop_loss_order])

    def __get_most_volatile_symbol(self) -> None:
        """
        Retrieves the most volatile symbol from the kline data list.

        This method determines the most volatile symbol based on the highest price change.
        """
        self.trading_symbol_kline_data = max(self.kline_data_list, key=lambda x: x.change)
        self.trading_symbol = self.trading_symbol_kline_data.symbol
        self.logger.info(f"Most volatile symbol is {self.trading_symbol_kline_data.symbol}, change is {round(self.trading_symbol_kline_data.change, 2)}.")

    def __calculate_take_profit_price(self, price: float, side: Side) -> float:
        """
        Calculates the take profit price based on the current price and trading side.

        This method adjusts the price according to the take profit multiplier configured in
        the strategy configuration.
        """
        self.logger.debug(f"Calculating take profit price, price: {price}, side: {side.name}.")
        if side == Side.LONG:
            tp_price = price * (1 + szalai_strategy_config.TAKE_PROFIT_MULTIPLIER)
        else:
            tp_price = price * (1 - szalai_strategy_config.TAKE_PROFIT_MULTIPLIER)
        self.logger.info(f"Take profit price is {tp_price}.")
        return tp_price

    def __calculate_stop_loss_price(self, price: float, side: Side) -> float:
        """
        Calculates the stop loss price based on the current price and trading side.

        This method adjusts the price according to the stop loss multiplier configured in
        the strategy configuration.
        """
        self.logger.debug(f"Calculating stop loss price, price: {price}, side: {side.name}.")
        if side == Side.LONG:
            sl_price = price * (1 - szalai_strategy_config.STOP_LOSS_MULTIPLIER)
        else:
            sl_price = price * (1 + szalai_strategy_config.STOP_LOSS_MULTIPLIER)
        self.logger.info(f"Stop loss price is {sl_price}.")
        return sl_price

    def __init_logger(self) -> Logger:
        """
        Initializes the logger for the Szalai strategy.

        This method sets up the logger with different handlers for console output and file
        logging. It includes separate files for informational and debug logging.
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Console handler for info level logs
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("[%(asctime)s, %(levelname)s] %(message)s"))
        logger.addHandler(console_handler)

        # File handler for info level logs
        file_info_name = f"szalai_strategy_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        file_info_handler = logging.FileHandler(filename=file_info_name)
        file_info_handler.setFormatter(logging.Formatter("[%(asctime)s, %(levelname)s] %(message)s"))
        file_info_handler.setLevel(logging.INFO)
        logger.addHandler(file_info_handler)

        # File handler for debug level logs
        file_debug_name = f"szalai_strategy_debug_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        file_debug_handler = logging.FileHandler(filename=file_debug_name)
        file_debug_handler.setFormatter(logging.Formatter("[%(asctime)s, %(threadName)s, %(funcName)s, %(levelname)s] %(message)s"))
        file_debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_debug_handler)

        return logger
