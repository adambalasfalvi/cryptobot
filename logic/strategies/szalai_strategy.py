import os
import sys
import logging
import logging.handlers
import time
import threading
from datetime import datetime
from datetime import timedelta
from logging import Logger
from concurrent.futures import ThreadPoolExecutor
from models.order_response import OrderResponse
from models.side import Side
from models.kline_data import KlineData
from models.interval import Interval
from models.symbol import Symbol
from logic.managers.binance_client_manager import BinanceClientManager
from logic.managers.binance_websocket_manager import BinanceWebsocketManager
from configs import szalai_strategy_config
from threading import Event

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
        data objects and order responses. It also sets up initial signals for trading decisions.
        """
        self.logger = self.__init_logger() 
        self.client_manager = BinanceClientManager(logger=self.logger)
        self.websocket_manager = BinanceWebsocketManager(logger=self.logger)
        self.side : Side
        self.risk_usd = szalai_strategy_config.RISK_USD
        self.interval = next(interval for interval in Interval if interval.value == szalai_strategy_config.BAR_INTERVAL) 
        self.kline_data_list: list[KlineData] = [KlineData.from_symbol(symbol) for symbol in szalai_strategy_config.TRADE_SYMBOLS]
        self.symbol_info_list: list[Symbol] = []
        self.order_list: list[OrderResponse] = []
        self.current_symbol: str = str()
        self.start_account_balance: float
        self.signal_interval_trigger: bool = False
        self.signal_set_up_orders: bool = True
        self.signal_check_orders: bool = True
        self.signal_check_profit: bool = False
        self.stop_event = Event()

    def start_strategy(self) -> None:
        """
        Starts the Szalai trading strategy.

        This method initializes and runs the trading strategy by:
        - Logging the start of the strategy.
        - Getting precision informations for symbols.
        - Closing any open positions and orders.
        - Fetching the initial account balance.
        - Configuring leverage for each trading symbol.
        - Starting the interval trigger thread
        - Setting up WebSocket connections for real-time updates on market and user data.
        - Entering a continuous loop where the strategy evaluates signals to manage orders and positions.

        The loop will run indefinitely, executing trading logic based on real-time data and internal signals.
        """       
        # Log the start of the strategy execution
        self.logger.info("Starting Szalai strategy.")

        # Get precision informations for symbols
        self.__get_precision_information_for_symbols()

        # Close any existing open positions and orders for all symbols to ensure a clean state
        self.__close_open_positions_and_orders_for_all_symbols()

        # Fetch and store the initial account balance to monitor profit or loss later
        self.start_account_balance = self.client_manager.futures_get_account_balance(szalai_strategy_config.ACCOUNT_CURRENCY)
        self.logger.info(f"Start account balance is {self.start_account_balance} {szalai_strategy_config.ACCOUNT_CURRENCY}.")

        # Use a ThreadPoolExecutor to concurrently set the leverage for each trading symbol
        with ThreadPoolExecutor(max_workers=len(szalai_strategy_config.TRADE_SYMBOLS)) as executor:
            for symbol in szalai_strategy_config.TRADE_SYMBOLS:
                # Submit a task to change the leverage for each symbol to the configured value
                executor.submit(self.client_manager.futures_change_leverage, symbol, szalai_strategy_config.LEVERAGE)
        
        # Start the interval trigger thread
        thread = threading.Thread(target=self.__set_interval_trigger)
        thread.start()

        # Start the WebSocket manager to receive real-time updates for market data and user data
        self.websocket_manager.start_websocket()

        # Set up the WebSocket for futures kline (candlestick) data and provide a handler for updates
        self.websocket_manager.setup_futures_kline_multiplex_websocket(
            szalai_strategy_config.TRADE_SYMBOLS,      # Symbols to monitor
            self.interval.value,       # Interval for kline data (e.g., 1 minute)
            self.__update_kline_data_handler           # Handler method to process kline data updates
        )

        # Set up the WebSocket for user data to receive order updates and provide a handler for updates
        self.websocket_manager.setup_user_data_websocket(
            self.__update_order_data_handler           # Handler method to process order data updates
        )

        # Main strategy loop to continuously check and act upon various conditions until the stop event is set
        while not self.stop_event.is_set():
            # If the signal to check profit is set, evaluate whether the profit target has been reached
            if self.signal_check_profit:
                self.signal_check_profit = False
                self.__is_profit_reached()

                if not self.stop_event.is_set(): 
                    self.__check_side()  # Adjust the trading side if necessary

            # If the signal to check orders is set, verify the status of open orders and handle them
            if not self.signal_check_profit and self.signal_check_orders:
                self.signal_check_orders = False
                self.__check_signal_to_order() 

            # If the signal to set up new orders and interval trigger is set, set up new orders
            if (
                not self.signal_check_profit
                and self.signal_set_up_orders
                and (self.current_symbol or self.signal_interval_trigger)
                and all(kline_data.is_not_empty for kline_data in self.kline_data_list)
            ):
                self.signal_set_up_orders = False
                self.signal_interval_trigger = False
                self.__set_up_orders()

    def stop_strategy(self) -> None:
        """
        Stops the Szalai trading strategy.

        This method logs the stop event, stops the WebSocket connections, and closes all open positions
        and orders to halt trading activities.
        """
        self.logger.info("Stopping Szalai strategy.")
        # Set the stop event to signal the run_strategy loop to exit
        self.stop_event.set()
        # Stop the WebSocket manager to cease receiving data
        self.websocket_manager.stop_websocket()
        # Close all open positions and orders for all symbols
        self.__close_open_positions_and_orders_for_all_symbols()
    
    def __calculate_first_side(self, symbol: str) -> None:
        """
        Calculates what will be the side to begin with if a new symbol has been chosen.

        This method converts the set interval to minutes, multiplies it with 3, and then uses it to get historical kline data.
        From this data the starting side is get calculated: If the last two kline data shows decline, the starting side will be long, otherwise it will be short.
        """
        time_delta_in_minutes = int(((self.interval.timedelta * 3).total_seconds() / 60)) % 60
        self.logger.debug(f"The calculated time_delta_in_minutes is {time_delta_in_minutes} minutes.")
        kline_datas = self.client_manager.futures_get_symbol_historical_klines_until_now(symbol, self.interval, time_delta_in_minutes, 2)

        if kline_datas and len(kline_datas) >= 2:
            # increase
            if float(kline_datas[-1][4]) - float(kline_datas[-2][4]) > 0:
                self.side = Side.SHORT
            # decline
            else:
                self.side = Side.LONG
        else:
            self.side = Side.LONG
    
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
        self.logger.debug(f"Next trigger is set to {next_trigger}.")
        return next_trigger
    
    def __set_interval_trigger(self) -> None:
        """
        Set the interval trigger at the configured interval.
        """
        while not self.stop_event.is_set():
            server_time = self.client_manager.futures_get_server_time()
            trigger_time = self.__calculate_trigger_time(server_time)
            time_to_sleep = (trigger_time - server_time).total_seconds()
            self.logger.debug(f"Time to sleep: {time_to_sleep} seconds.")

            sleep_interval = 0.1 # seconds
            elapsed_time = 0

            while not self.stop_event.is_set() and elapsed_time < time_to_sleep:
                time.sleep(sleep_interval)
                elapsed_time += sleep_interval

            if self.stop_event.is_set():
                break
    
            self.signal_interval_trigger = True
            self.logger.info(f"The configured {self.interval.value} interval has been triggered.")

    def __check_signal_to_order(self) -> None:
        """
        Checks whether there are signals to place new orders.

        This method examines the current order list to determine if there are any discrepancies or
        conditions that warrant setting up new orders. It ensures that the number of active orders
        is as expected and closes positions for symbols if necessary.
        """
        self.logger.debug("Checking orders.")
        if not self.order_list:
            # If there are no orders, set the flag to prepare new orders
            self.logger.debug("Order list is empty.")
            self.signal_set_up_orders = True
        else:
            # Filter active orders of certain types and statuses
            active_orders = [order for order in self.order_list if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "NEW"]
            self.logger.debug(f"Active orders: {', '.join(str(order) for order in active_orders)}")

            # If there are no active orders, set up new orders
            if not active_orders:
                self.signal_set_up_orders = True
            # If the count of active orders is not as expected, set up new orders
            elif len(active_orders) != 2:              
                self.signal_set_up_orders = True
                current_symbol = next(order for order in self.order_list if order.status == "NEW").symbol
                self.logger.debug("Active orders count is not equal to 2.")
                self.__close_open_positions_and_orders_for_symbol(current_symbol)

    def __is_profit_reached(self) -> bool:
        """
        Checks if the desired profit has been reached.

        This method compares the current account balance with the initial balance to determine if
        the maximum allowable change has been exceeded. If so, it stops the strategy.
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
            # Remove current symbol
            self.current_symbol = str()
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
        elif max_negative_balance_change > account_balance_change:
            self.logger.info(f"Max negative account balance change of {szalai_strategy_config.MAX_NEGATIVE_ACCOUNT_BALANCE_CHANGE} has been reached.")
            self.logger.info(f"A new symbol is to be searched.")
            # Remove current symbol
            self.current_symbol = str()
            # Reinitialize the starting balance
            self.start_account_balance = current_account_balance
        else:
            self.logger.info(f"Trading continues with {self.current_symbol} symbol.")

    def __check_side(self) -> None:
        """
        Checks the trading side based on recent order activity.

        This method updates the trading side (LONG or SHORT) based on the type and status of the
        most recently filled order. It ensures that the trading side aligns with the latest filled orders.
        """
        self.logger.debug(f"Checking side, current side: {self.side.name}.")
        # Sort the order list by update time
        sorted_order_list = sorted(self.order_list, key=lambda x: x.update_time, reverse=True)
        # Find the last filled order
        last_filled_order = next(order for order in sorted_order_list if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "FILLED")
        self.logger.debug(f"Last filled order: {last_filled_order}.")
        # Toggle the trading side if the last filled order is STOP_MARKET
        if last_filled_order.type == "STOP_MARKET":
            self.side = Side.LONG if self.side == Side.SHORT else Side.SHORT
            self.logger.info(f"Side has been changed to {self.side.name}.")

    def __set_up_orders(self) -> None:
        """
        Sets up the order creating. If the signal_change_pair flag is true, it will search for the most volatile symbol. 
        """
        # New symbol      
        if not self.current_symbol:
            with ThreadPoolExecutor() as executor:
                # Sync OS time
                executor.submit(os.system, "w32tm /resync >nul 2>&1")
                self.logger.debug(f"System time has been resynced.")

                # Get the most volatile symbol to trade on
                future_most_volatile_symbol = executor.submit(self.__get_most_volatile_symbol)
                trading_symbol = future_most_volatile_symbol.result()

            # Check if the volatility change exceeds the minimum threshold
            if trading_symbol.change >= szalai_strategy_config.MIN_CHANGE:
                # Save the symbol into the current_trading variable
                self.current_symbol = trading_symbol.symbol
                self.logger.info(f"The most volatile symbol {trading_symbol.symbol} has a change of {round(trading_symbol.change, 2)}.")
                self.logger.info(f"The current trading symbol is {self.current_symbol}.")

                # Calculate the first trading side
                self.__calculate_first_side(trading_symbol.symbol)
                self.logger.info(f"The calculated first trading side is {self.side}.")

                self.__create_orders(trading_symbol)
            else:
                self.logger.warning(
                    f"The most volatile symbol {trading_symbol.symbol} has a change of {round(trading_symbol.change, 2)}, "
                    f"which does not reach the configured minimum change of {szalai_strategy_config.MIN_CHANGE}."
                )
        # Trading continues on the same symbol
        else:
            # Sync OS time
            os.system("w32tm /resync >nul 2>&1")
            self.logger.debug(f"System time has been resynced.")

            # Get the current symbol's kline data
            trading_symbol = next(kline_data for kline_data in self.kline_data_list if kline_data.symbol == self.current_symbol)        
            self.__create_orders(trading_symbol)
    
    def __create_orders(self, trading_symbol: KlineData) -> None:
        """
        Creates orders based on the specified quantity and trading side.

        This method handles the creation of new orders by:
        - Calculating the trading quantity
        - Concurrently creating a position order, stop loss order, and take profit order
        - Adding these orders to the list and handling any exceptions that may occur
        """
        # Calculate the order quantity
        quantity = self.__calculate_quantity(trading_symbol)
        self.logger.info(f"Setting up orders, quantity: {quantity}, side: {self.side.name}.")

        try:            
            with ThreadPoolExecutor() as executor:              
                # Initialize futures to None
                future_position = None
                future_stop_loss = None
                future_take_profit = None

                # Create the position order
                future_position = executor.submit(self.__create_position_order, trading_symbol.symbol, quantity, self.side)
                position_order = future_position.result()

                # Create the stop loss and take profit orders
                future_stop_loss = executor.submit(self.__create_stop_loss_order, trading_symbol.symbol, position_order.average_price, self.side)
                future_take_profit = executor.submit(self.__create_take_profit_order, trading_symbol.symbol, position_order.average_price, self.side)
                stop_loss_order = future_stop_loss.result()
                take_profit_order = future_take_profit.result()

                # Extend the order list with the newly created orders
                self.order_list.extend([position_order, stop_loss_order, take_profit_order])
        except Exception as e:
            # Log any errors encountered during order setup
            self.logger.error(f"Error while setting up orders, {str(e)}")
            self.logger.debug("Error while setting up orders:", exc_info=True)
            # Cancel any outstanding futures if an error occurs
            if future_position:
                future_position.cancel()
            if future_stop_loss:
                future_stop_loss.cancel()
            if future_take_profit: 
                future_take_profit.cancel()
            # Cancel all orders and positions
            self.__close_open_positions_and_orders_for_symbol(trading_symbol.symbol)

    def __calculate_quantity(self, kline_data: KlineData) -> float:
        """
        Calculates the trading quantity for a symbol.

        This method calculates the necessary trading quantity from the configured USD amount to risk.
        """
        # TODO: ezt lehet meg kéne nézni
        quantity_precision = next(symbol_info.quantity_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == kline_data.symbol)
        quantity = round(szalai_strategy_config.RISK_USD / kline_data.close_price, quantity_precision)
        self.logger.info(
            f"The calculated quantity of symbol {kline_data.symbol} " 
            f"from {szalai_strategy_config.RISK_USD} USD is {quantity}."
        )
        return quantity
    
    def __close_open_positions_and_orders_for_symbol(self, symbol: str) -> None:
        """
        Closes all open positions and orders for a specified symbol.

        This method cancels all open orders and closes any positions by creating a market
        order for the remaining position amount.
        """
        self.logger.info(f"Closing all open positions and orders for {symbol}.")
        with ThreadPoolExecutor() as executor:
            # Cancel all open orders for the symbol
            executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol)

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
            for symbol in szalai_strategy_config.TRADE_SYMBOLS:
                executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol)
            
            # Get position information and close any positions for all symbols concurrently
            for position_info_result in executor.map(self.client_manager.futures_get_position_information, szalai_strategy_config.TRADE_SYMBOLS):
                position_symbol = next(x["symbol"] for x in position_info_result)
                position_amount = float(next(x["positionAmt"] for x in position_info_result))

                # If the position amount is positive, sell it
                if position_amount > 0:
                    sell_market_order = self.client_manager.futures_create_sell_market_order(position_symbol, position_amount)
                    self.order_list.append(sell_market_order)

                # If the position amount is negative, buy it
                if position_amount < 0:
                    buy_market_order = self.client_manager.futures_create_buy_market_order(position_symbol, abs(position_amount))
                    self.order_list.append(buy_market_order)

    def __update_kline_data_handler(self, message: str) -> None:
        """
        Updates the kline (candlestick) data based on the incoming WebSocket message.

        This method processes the kline data message, updates the relevant KlineData object,
        and logs the update.
        """

        kline_event_time = (datetime.fromtimestamp(message["data"]["E"]/1000))
        kline_start_time = (datetime.fromtimestamp(message["data"]["k"]["t"]/1000))
        kline_close_time = (datetime.fromtimestamp(message["data"]["k"]["T"]/1000))
        
        self.logger.debug(f"Kline data update, kline_event_time: {kline_event_time}, kline_start_time: {kline_start_time}, kline_close_time: {kline_close_time}, message: {message}.")
        kline_data = next((x for x in self.kline_data_list if x.symbol == message["data"]["s"]), None)
        if kline_data is not None:
            kline_data.interval = message["data"]["k"]["i"]
            kline_data.open_price = float(message["data"]["k"]["o"])
            kline_data.close_price = float(message["data"]["k"]["c"])
            kline_data.high_price = float(message["data"]["k"]["h"])
            kline_data.low_price = float(message["data"]["k"]["l"])
            kline_data.is_closed = bool(message["data"]["k"]["x"])
            
            self.signal_check_orders = True

    def __update_order_data_handler(self, message: str) -> None:
        """
        Updates the order data based on the incoming WebSocket message.

        This method processes order trade updates, adjusts the status of existing orders, and
        sets flags for checking profit and orders as necessary.
        """
        self.logger.debug(f"Trade update, message: {message}.")
        event_type = message.get("e")
        client_order_id = message.get("o", {}).get("c", None)

        if event_type == "ORDER_TRADE_UPDATE" and any(order.client_order_id == client_order_id for order in self.order_list):
            status = message.get("o").get("X")
            order = next(order for order in self.order_list if order.client_order_id == client_order_id)
            order.status = status
            self.logger.debug(f"Order has been updated, {order}.")

            if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "FILLED":
                self.logger.info(f"{order.type} order has been filled, {order}.")
                self.signal_check_profit = True
                self.logger.debug("Signal to check profit has been set to True.")

            self.signal_check_orders = True
            self.logger.debug("Signal to check orders has been set to True.")

    def __create_position_order(self, symbol: str, quantity: float, side: Side) -> OrderResponse:
        """
        Creates a position order for the specified symbol, quantity, and trading side.

        This method generates a market order to either buy or sell based on the side.
        """
        self.logger.info(f"Creating position order, symbol: {symbol}, quantity: {quantity}, side: {side.name}.")
        if side == Side.LONG:
            return self.client_manager.futures_create_buy_market_order(symbol, quantity)
        else:
            return self.client_manager.futures_create_sell_market_order(symbol, quantity)

    def __create_take_profit_order(self, symbol: str, position_price: float, side: Side) -> OrderResponse:
        """
        Creates a take profit order for the specified symbol, price, and trading side.

        This method calculates the take profit price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        tp_price = round(self.__calculate_take_profit_price(position_price, side), price_precision)
        self.logger.info(f"Creating take profit order, symbol: {symbol}, price: {tp_price}, side: {side.name}.")
        if self.side == Side.LONG:
            return self.client_manager.futures_create_sell_take_profit_market_order(symbol, tp_price)
        else:
            return self.client_manager.futures_create_buy_take_profit_market_order(symbol, tp_price)

    def __create_stop_loss_order(self, symbol: str, position_price: float, side: Side) -> OrderResponse:
        """
        Creates a stop loss order for the specified symbol, price, and trading side.

        This method calculates the stop loss price based on the current price and trading side,
        then creates the appropriate order.
        """
        price_precision = next(symbol_info.price_precision for symbol_info in self.symbol_info_list if symbol_info.symbol == symbol)
        sl_price = round(self.__calculate_stop_loss_price(position_price, side), price_precision)
        self.logger.info(f"Creating stop loss order, symbol: {symbol}, position price: {sl_price}, side: {side.name}.")
        if self.side == Side.LONG:
            return self.client_manager.futures_create_sell_stop_market_order(symbol, sl_price)
        else:
            return self.client_manager.futures_create_buy_stop_market_order(symbol, sl_price)

    def __get_most_volatile_symbol(self) -> KlineData:
        """
        Retrieves the most volatile symbol from the kline data list.

        This method determines the most volatile symbol based on the highest price change
        and returns the corresponding KlineData object.
        """
        most_volatile_symbol = max(self.kline_data_list, key=lambda x: x.change)
        self.logger.info(f"Most volatile symbol is {most_volatile_symbol.symbol}.")
        return most_volatile_symbol

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
