from datetime import datetime
from logging import Logger
from binance import Client
from binance import enums
from configs import binance_config
from models.order_response import OrderResponse

class BinanceClientManager():
    """This class manages Binance client operations including creating orders, 
    changing leverage, and retrieving account information."""

    def __init__(self, logger: Logger) -> None:
        """Initializes the BinanceClientManager with a logger and a Binance client.

        Args:
            logger (Logger): Logger instance for logging messages.
        """
        self.logger = logger
        self.client = Client(binance_config.API_KEY, binance_config.API_SECRET, testnet=binance_config.TESTNET)

    def futures_get_symbol_precision_info(self, symbol: str) -> None:
        """Gets symbol precision information.

        Args:
            symbol (str): Trading symbol.
        """
        response = self.client.futures_exchange_info()

        try:
            symbol_information = next(symbol_info for symbol_info in response["symbols"] if symbol_info["symbol"] == symbol)
            self.logger.debug(
                f"Symbol information, symbol: {symbol}, "
                f"pricePrecision: {symbol_information["pricePrecision"]}, "
                f"quantityPrecision: {symbol_information["quantityPrecision"]} "
                f"baseAssetPrecision: {symbol_information["baseAssetPrecision"]}, "
                f"quotePrecision: {symbol_information["quotePrecision"]}."
            )
            return {
                "symbol": symbol,
                "pricePrecision": symbol_information["pricePrecision"],
                "quantityPrecision": symbol_information["quantityPrecision"],
                "baseAssetPrecision": symbol_information["baseAssetPrecision"],
                "quotePrecision": symbol_information["quotePrecision"]
            }
        except StopIteration as e:
            self.logger.error(f"Error while getting symbol precision information, {str(e)}")
            self.logger.debug("Error while getting symbol precision information:", exc_info=True)
    
    def futures_get_server_time(self) -> datetime:
        """Gets the current time from the Binance server.

        Returns:
            datetime: The current Binance server time.
        """
        response = self.client.futures_time()
        server_time = datetime.fromtimestamp(response["serverTime"]/1000)
        self.logger.debug(f"Server time is {server_time}.")
        return server_time
    
    def futures_create_buy_market_order(self, symbol: str, quantity: float) -> OrderResponse:
        """Creates a futures buy market order.

        Args:
            symbol (str): Trading symbol.
            quantity (float): Quantity to buy.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating buy market order, symbol: {symbol}, quantity: {quantity}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_BUY, 
            type=enums.FUTURE_ORDER_TYPE_MARKET, 
            quantity=quantity, 
            newOrderRespType=enums.ORDER_RESP_TYPE_RESULT, 
            reduceOnly="false")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response
        
    def futures_create_sell_market_order(self, symbol: str, quantity: float) -> OrderResponse:
        """Creates a futures sell market order.

        Args:
            symbol (str): Trading symbol.
            quantity (float): Quantity to sell.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating sell market order, symbol: {symbol}, quantity: {quantity}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_SELL, 
            type=enums.FUTURE_ORDER_TYPE_MARKET, 
            quantity=quantity, 
            newOrderRespType=enums.ORDER_RESP_TYPE_RESULT, 
            reduceOnly="false")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response

    def futures_create_buy_stop_market_order(self, symbol: str, stop_price: float) -> OrderResponse:
        """Creates a futures buy stop market order.

        Args:
            symbol (str): Trading symbol.
            stop_price (float): Stop price for the order.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating buy stop market order, symbol: {symbol}, stop_price: {stop_price}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_BUY, 
            type=enums.FUTURE_ORDER_TYPE_STOP_MARKET, 
            stopPrice=stop_price,
            timeInForce=enums.TIME_IN_FORCE_GTC,
            closePosition="true")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response
        
    def futures_create_sell_stop_market_order(self, symbol: str, stop_price: float) -> OrderResponse:
        """Creates a futures sell stop market order.

        Args:
            symbol (str): Trading symbol.
            stop_price (float): Stop price for the order.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating sell stop market order, symbol: {symbol}, stop_price: {stop_price}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_SELL, 
            type=enums.FUTURE_ORDER_TYPE_STOP_MARKET, 
            stopPrice=stop_price,
            timeInForce=enums.TIME_IN_FORCE_GTC,
            closePosition="true")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response
        
    def futures_create_buy_take_profit_market_order(self, symbol: str, stop_price: float) -> OrderResponse:
        """Creates a futures buy take profit market order.

        Args:
            symbol (str): Trading symbol.
            stop_price (float): Stop price for the order.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating buy take profit market order, symbol: {symbol}, stop_price: {stop_price}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_BUY, 
            type=enums.FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET, 
            stopPrice=stop_price,
            timeInForce=enums.TIME_IN_FORCE_GTC,
            closePosition="true")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response
        
    def futures_create_sell_take_profit_market_order(self, symbol: str, stop_price: float) -> OrderResponse:
        """Creates a futures sell take profit market order.

        Args:
            symbol (str): Trading symbol.
            stop_price (float): Stop price for the order.

        Returns:
            OrderResponse: Response object containing order details.
        """
        self.logger.debug(f"Creating sell take profit market order, symbol: {symbol}, stop_price: {stop_price}.")
        response = self.client.futures_create_order(
            symbol=symbol, 
            side=enums.SIDE_SELL, 
            type=enums.FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET, 
            stopPrice=stop_price,
            timeInForce=enums.TIME_IN_FORCE_GTC,
            closePosition="true")
        
        order_response = OrderResponse(
            response["clientOrderId"], 
            response["symbol"], 
            response["status"], 
            float(response["avgPrice"]), 
            float(response["stopPrice"]),
            float(response["origQty"]),
            response["type"],
            response["side"],
            datetime.fromtimestamp(response["updateTime"]/1000)
        )
        return order_response
    
    def futures_cancel_all_open_orders(self, symbol: str) -> str:
        """Cancels all open futures orders for a given symbol.

        Args:
            symbol (str): Trading symbol.

        Returns:
            str: Response from the cancel order request.
        """
        response = self.client.futures_cancel_all_open_orders(symbol=symbol)
        self.logger.debug(f"All open future orders have been cancelled.")
        return response
        
    def futures_change_leverage(self, symbol: str, leverage: int) -> str:
        """Changes the leverage for a given symbol.

        Args:
            symbol (str): Trading symbol.
            leverage (int): New leverage value.

        Returns:
            str: Response from the change leverage request.
        """
        response = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
        self.logger.debug(f"Leverage has been changed to {leverage} for {symbol}.")
        return response

    def futures_get_account_balance(self, currency: str) -> float:
        """Retrieves the account balance for a specific currency.

        Args:
            currency (str): Currency symbol (e.g., "BTC").

        Returns:
            float: Account balance for the specified currency.
        """
        self.logger.debug(f"Getting {currency} account balance.")
        accounts = self.client.futures_account_balance()
        account = next(filter(lambda x: x["asset"] == currency, accounts), None)
        balance = float(account["balance"])
        self.logger.debug(f"Balance is {balance} {currency}.")
        return balance
    
    def futures_get_position_information(self, symbol: str) -> str:
        """Retrieves the position information for a given symbol.

        Args:
            symbol (str): Trading symbol.

        Returns:
            str: Position information for the specified symbol.
        """
        self.logger.debug(f"Getting asset balance for {symbol}.")
        response = self.client.futures_position_information(symbol=symbol)
        return response
    
    def futures_get_symbol_price_ticker(self, symbol: str) -> float:
        """Retrieves the latest price ticker for a given symbol.

        Args:
            symbol (str): Trading symbol.

        Returns:
            float: Latest price for the specified symbol.
        """
        self.logger.debug(f"Getting latest price for {symbol}.")
        response = self.client.futures_symbol_ticker(symbol=symbol)
        latest_price = float(response["price"])
        self.logger.debug(f"Latest price for {symbol} is {latest_price}.")
        return latest_price