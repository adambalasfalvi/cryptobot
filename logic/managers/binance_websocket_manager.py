from configs import szalai_strategy_config
from logging import Logger
from binance import ThreadedWebsocketManager
from collections.abc import Callable
from configs import binance_config

class BinanceWebsocketManager:
    """This class is responsible for all websocket-related functions with Binance using the ThreadedWebsocketManager."""

    def __init__(self, logger: Logger) -> None:
        """Initializes the BinanceWebsocketManager using the API key and API secret from the config.
        
        Args:
            logger (Logger): The logger instance used for logging debug information.
        """
        self.logger = logger
        self.twm = ThreadedWebsocketManager(binance_config.API_KEY, binance_config.API_SECRET, testnet=binance_config.TESTNET)

    def setup_futures_kline_multiplex_websocket(self, symbols: list[str], kline_interval: str, callback: Callable) -> None:
        """Sets up a futures kline multiplex websocket for the given symbols and interval.
        
        Args:
            symbols (list[str]): A list of symbol strings to monitor.
            kline_interval (str): The interval of the kline data (e.g., '1m', '5m').
            callback (Callable): The callback function to handle the websocket data.
        """
        streams: list[str] = [f"{symbol.lower()}@kline_{kline_interval}" for symbol in symbols]

        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Setting up futures websockets, streams: {', '.join(streams)}, callback: {callback.__name__}.")
        
        self.twm.start_futures_multiplex_socket(callback=callback, streams=streams)

    def setup_user_data_websocket(self, callback: Callable) -> None:
        """Sets up a user data websocket.
        
        Args:
            callback (Callable): The callback function to handle the websocket data.
        """
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug(f"Setting up futures user socket, callback: {callback.__name__}.")
        
        self.twm.start_futures_user_socket(callback=callback)
    
    def start_websocket(self) -> None:
        """Starts the websocket manager."""
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug("Starting BinanceWebsocketManager.")
            
        self.twm.start()

    def stop_websocket(self) -> None:
        """Stops the websocket manager."""
        if szalai_strategy_config.LOG_DEBUG_DATA:
            self.logger.debug("Stopping BinanceWebsocketManager.")

        self.twm.stop()

        

    




