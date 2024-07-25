import sys
import logging
import logging.handlers
from datetime import datetime
from logging import Logger
from concurrent.futures import ThreadPoolExecutor
from models.order_response import OrderResponse
from models.side import Side
from models.kline_data import KlineData
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
        self.side = Side.LONG if szalai_strategy_config.START_POSITION == "LONG" else Side.SHORT
        self.trading_quantity = szalai_strategy_config.TRADE_QUANTITY
        self.kline_data_list: list[KlineData] = [KlineData.from_symbol(symbol) for symbol in szalai_strategy_config.TRADE_SYMBOLS]
        self.order_list: list[OrderResponse] = []
        self.start_account_balance: float
        self.signal_to_set_up_orders: bool = True
        self.signal_to_check_orders: bool = True
        self.signal_to_check_profit: bool = False
        self.stop_event = Event()

    def run_strategy(self) -> None:
        """
        Starts the Szalai trading strategy.

        This method initializes and runs the trading strategy by:
        - Logging the start of the strategy.
        - Closing any open positions and orders.
        - Fetching the initial account balance.
        - Configuring leverage for each trading symbol.
        - Setting up WebSocket connections for real-time updates on market and user data.
        - Entering a continuous loop where the strategy evaluates signals to manage orders and positions.

        The loop will run indefinitely, executing trading logic based on real-time data and internal signals.
        """       
        # Log the start of the strategy execution
        self.logger.info("Starting Szalai strategy.")

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

        # Start the WebSocket manager to receive real-time updates for market data and user data
        self.websocket_manager.start_websocket()

        # Set up the WebSocket for futures kline (candlestick) data and provide a handler for updates
        self.websocket_manager.setup_futures_kline_multiplex_websocket(
            szalai_strategy_config.TRADE_SYMBOLS,      # Symbols to monitor
            szalai_strategy_config.BAR_INTERVAL,       # Interval for kline data (e.g., 1 minute)
            self.__update_kline_data_handler           # Handler method to process kline data updates
        )

        # Set up the WebSocket for user data to receive order updates and provide a handler for updates
        self.websocket_manager.setup_user_data_websocket(
            self.__update_order_data_handler           # Handler method to process order data updates
        )

        # Main strategy loop to continuously check and act upon various conditions until the stop event is set
        while not self.stop_event.is_set():
            # If the signal to check profit is set, evaluate whether the profit target has been reached
            if self.signal_to_check_profit:
                self.signal_to_check_profit = False
                self.__is_profit_reached()  # Check if the desired profit level is reached

                if not self.stop_event.is_set(): 
                    self.__check_side()         # Adjust the trading side if necessary

            # If the signal to check orders is set, verify the status of open orders and handle them
            if self.signal_to_check_orders:
                self.signal_to_check_orders = False
                self.__check_signal_to_order()  # Check and handle signals related to existing orders

            # If the signal to set up new orders is set and all kline data is updated, set up new orders
            if self.signal_to_set_up_orders and all(kline_data.is_updated for kline_data in self.kline_data_list):
                self.signal_to_set_up_orders = False
                self.__set_up_orders(self.trading_quantity, self.side)  # Set up new orders based on the current strategy

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
            self.signal_to_set_up_orders = True
        else:
            # Filter active orders of certain types and statuses
            active_orders = [order for order in self.order_list if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "NEW"]
            self.logger.debug(f"Active orders: {', '.join(str(order) for order in active_orders)}")

            # If there are no active orders, set up new orders
            if not active_orders:
                self.signal_to_set_up_orders = True
            # If the count of active orders is not as expected, set up new orders
            elif len(active_orders) != 2:              
                self.signal_to_set_up_orders = True
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
        self.logger.info(f"Account balance change is {account_balance_change - 1}.")
        # Check if the change exceeds the maximum allowed
        if abs(account_balance_change - 1) > szalai_strategy_config.MAX_ACCOUNT_BALANCE_CHANGE:
            self.logger.info(f"Max account balance change of {szalai_strategy_config.MAX_ACCOUNT_BALANCE_CHANGE} has been reached.")
            # Stop the strategy if the change exceeds the limit
            self.stop_strategy()

    def __check_side(self) -> None:
        """
        Checks the trading side based on recent order activity.

        This method updates the trading side (LONG or SHORT) based on the type and status of the
        most recently filled order. It ensures that the trading side aligns with the latest filled orders.
        """
        self.logger.debug(f"Checking side, current side: {self.side.name}.")
        # Find the last filled order
        last_filled_order = next(order for order in self.order_list if (order.type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]) and order.status == "FILLED")
        self.logger.debug(f"Last filled order: {last_filled_order}.")
        # Update the trading side based on the type of the last filled order
        if last_filled_order.type == "STOP_MARKET" and self.side == Side.LONG:
            self.side = Side.SHORT
            self.logger.info(f"Side has been changed to {self.side.name}.")
        elif last_filled_order.type == "TAKE_PROFIT_MARKET" and self.side == Side.SHORT:
            self.side = Side.LONG
            self.logger.info(f"Side has been changed to {self.side.name}.")

    def __set_up_orders(self, quantity: float, side: Side) -> None:
        """
        Sets up new orders based on the specified quantity and trading side.

        This method handles the creation of new orders by:
        - Determining the most volatile symbol
        - Concurrently creating a position order, stop loss order, and take profit order
        - Adding these orders to the list and handling any exceptions that may occur
        """

        # Get the most volatile symbol to trade on
        trading_symbol = self.__get_most_volatile_symbol()

        # Check if the volatility change exceeds the minimum threshold
        if trading_symbol.change > szalai_strategy_config.MIN_CHANGE:
            self.logger.info(f"Most volatile symbol {trading_symbol.symbol} has a change of {trading_symbol.change}.")
            self.logger.info(f"Setting up orders, quantity: {quantity}, side: {side.name}.")
            try:
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Create the position order
                    future_position = executor.submit(self.__create_position_order, trading_symbol.symbol, quantity, side)
                    position_order = future_position.result()

                    # Create the stop loss and take profit orders
                    future_stop_loss = executor.submit(self.__create_stop_loss_order, trading_symbol.symbol, position_order.average_price, side)
                    future_take_profit = executor.submit(self.__create_take_profit_order, trading_symbol.symbol, position_order.average_price, side)
                    stop_loss_order = future_stop_loss.result()
                    take_profit_order = future_take_profit.result()

                    # Extend the order list with the newly created orders
                    self.order_list.extend([position_order, stop_loss_order, take_profit_order])
            except Exception as e:
                # Log any errors encountered during order setup
                self.logger.error(f"Error while setting up orders, {str(e)}")
                self.logger.debug("Error while setting up orders:", exc_info=True)
                # Cancel any outstanding futures if an error occurs
                future_position.cancel()
                future_stop_loss.cancel()
                future_take_profit.cancel()
                # Set the signal to set up orders for new orders
                self.signal_to_set_up_orders = True

        else:
            self.logger.warning(
                f"The most volatile symbol {trading_symbol.symbol} has a change of {trading_symbol.change}, "
                f"which does not reach the configured minimum change of {szalai_strategy_config.MIN_CHANGE}."
            )

    def __close_open_positions_and_orders_for_all_symbols(self) -> None:
        """
        Closes all open positions and orders for all symbols.

        This method iterates through each trading symbol and:
        - Cancels all open orders
        - Closes any remaining positions by creating market sell orders
        """
        self.logger.info("Closing all open positions and orders for all symbols.")
        for symbol in szalai_strategy_config.TRADE_SYMBOLS:
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Cancel all open orders for the symbol
                executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol)

                # Get position information and close any open positions
                position_info_future = executor.submit(self.client_manager.futures_get_position_information, symbol)
                position_info_result = position_info_future.result()
                position_amount = next((x["positionAmt"] for x in position_info_result))

                if float(position_amount) > 0:
                    # Create a market sell order to close the position
                    sell_market_order = self.client_manager.futures_create_sell_market_order(symbol, position_amount)
                    self.order_list.append(sell_market_order)

    def __close_open_positions_and_orders_for_symbol(self, symbol: str) -> None:
        """
        Closes all open positions and orders for a specified symbol.

        This method cancels all open orders and closes any positions by creating a market sell
        order for the remaining position amount.
        """
        self.logger.info(f"Closing all open positions and orders for {symbol}.")
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Cancel all open orders for the symbol
            executor.submit(self.client_manager.futures_cancel_all_open_orders, symbol)

            # Get position information and close any open positions
            position_info_future = executor.submit(self.client_manager.futures_get_position_information, symbol)
            position_info_result = position_info_future.result()
            position_amount = next((x["positionAmt"] for x in position_info_result))

            if float(position_amount) > 0:
                # Create a market sell order to close the position
                sell_market_order = self.client_manager.futures_create_sell_market_order(symbol, position_amount)
                self.order_list.append(sell_market_order)

    def __update_kline_data_handler(self, message: str) -> None:
        """
        Updates the kline (candlestick) data based on the incoming WebSocket message.

        This method processes the kline data message, updates the relevant KlineData object,
        and logs the update. It checks if the kline data is closed and logs the data accordingly.
        """
        self.logger.debug(f"Kline data update, message: {message}.")
        kline_data = next((x for x in self.kline_data_list if x.symbol == message["data"]["s"]), None)
        if kline_data is not None:
            kline_data.interval = message["data"]["k"]["i"]
            kline_data.open_price = float(message["data"]["k"]["o"])
            kline_data.close_price = float(message["data"]["k"]["c"])
            kline_data.high_price = float(message["data"]["k"]["h"])
            kline_data.low_price = float(message["data"]["k"]["l"])
            kline_data.is_closed = bool(message["data"]["k"]["x"])

            if kline_data.is_closed:
                self.logger.info(f"Kline data has been updated, {kline_data}.")
                self.signal_to_check_orders = True
                self.logger.debug("Signal to check orders has been set to True.")
            else:
                self.logger.debug(f"Kline data has been updated, {kline_data}.")


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
                self.signal_to_check_profit = True
                self.logger.debug("Signal to check profit has been set to True.")

            self.signal_to_check_orders = True
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

    def __create_take_profit_order(self, symbol: str, price: float, side: Side) -> OrderResponse:
        """
        Creates a take profit order for the specified symbol, price, and trading side.

        This method calculates the take profit price based on the current price and trading side,
        then creates the appropriate order.
        """
        self.logger.info(f"Creating take profit order, symbol: {symbol}, price: {price}, side: {side.name}.")
        tp_price = self.__calculate_take_profit_price(price, side)
        if self.side == Side.LONG:
            return self.client_manager.futures_create_sell_take_profit_market_order(symbol, tp_price)
        else:
            return self.client_manager.futures_create_buy_take_profit_market_order(symbol, tp_price)

    def __create_stop_loss_order(self, symbol: str, price: float, side: Side) -> OrderResponse:
        """
        Creates a stop loss order for the specified symbol, price, and trading side.

        This method calculates the stop loss price based on the current price and trading side,
        then creates the appropriate order.
        """
        self.logger.info(f"Creating stop loss order, symbol: {symbol}, price: {price}, side: {side.name}.")
        sl_price = self.__calculate_stop_loss_price(price, side)
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
