import socket
import aiohttp
from logging import Logger
from typing import Optional

class SessionManager:
    """
    Manages optimized aiohttp sessions.
    
    This class provides optimized TCP connector configuration with:
    - DNS caching to prevent resolution delays
    - Connection pooling for better performance
    - Keep-alive settings for persistent connections
    - Low-latency socket configuration
    """

    def __init__(self, logger: Logger):
        """
        Initialize the SessionManager with a logger.
        
        Args:
            logger (Logger): Logger instance for logging session events
        """
        self.logger = logger
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None

    def _create_socket_factory(self):
        """
        Create a custom socket factory with optimized settings for trading APIs.
        
        Returns:
            callable: Socket factory function optimized for low-latency trading
        """
        def socket_factory(addr_info):
            """Custom socket factory with optimized settings for trading."""
            family, type_, proto, _, _ = addr_info
            sock = socket.socket(family=family, type=type_, proto=proto)
            
            # Enable keep-alive for persistent connections
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
            
            # Keep-alive settings - optimized for trading APIs
            if hasattr(socket, 'TCP_KEEPIDLE'):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)    # Start keep-alive after 60s
            if hasattr(socket, 'TCP_KEEPINTVL'):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)   # Send keep-alive every 10s
            if hasattr(socket, 'TCP_KEEPCNT'):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)      # Max 6 keep-alive probes
            
            # Optimize for low latency (disable Nagle's algorithm)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
            
            # Set socket buffer sizes for better performance
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 64KB receive buffer
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64KB send buffer
            
            return sock
        
        return socket_factory
    
    def _create_optimized_connector(self) -> aiohttp.TCPConnector:
        """
        Create an optimized TCP connector.
        
        Returns:
            aiohttp.TCPConnector: Optimized connector with DNS caching and connection pooling
        """
        return aiohttp.TCPConnector(
            limit=50,                   # Total connection pool limit (good for multiple symbols)
            limit_per_host=10,          # Limit per host (Binance API endpoints)
            ttl_dns_cache=300,          # DNS cache TTL (5 minutes)
            use_dns_cache=True,         # Enable DNS caching
            keepalive_timeout=60,       # Keep connections alive for 60 seconds
            enable_cleanup_closed=True, # Clean up closed connections automatically
            force_close=False,          # Don't force close connections
            socket_factory=self._create_socket_factory()
        )
    
    def create_session(self) -> aiohttp.ClientSession:
        """
        Create an optimized aiohttp session for trading APIs.
        
        Returns:
            aiohttp.ClientSession: Optimized session with connection pooling and DNS caching
        """
        if self.session and not self.session.closed:
            self.logger.warning("Session already exists and is not closed. Closing existing session.")
            # Don't await here since this might be called from sync context
            # The caller should handle closing the existing session
        
        # Create optimized connector
        self.connector = self._create_optimized_connector()
        
        # Create session with optimized settings
        timeout = aiohttp.ClientTimeout(
            total=30,      # Total timeout for request
            connect=10,    # Connection timeout
            sock_read=20   # Socket read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=timeout
        )
        
        self.logger.info("Optimized aiohttp session created.")
        
        return self.session
    
    async def close_session(self) -> None:
        """
        Close the aiohttp session and connector gracefully.
        """
        try:
            if self.session and not self.session.closed:
                self.logger.debug("Closing aiohttp session")
                await self.session.close()
                
            if self.connector and not self.connector.closed:
                self.logger.debug("Closing TCP connector")
                await self.connector.close()
                
            self.session = None
            self.connector = None
            
        except Exception as e:
            self.logger.warning(f"Error closing session manager: {e}")
    
    def get_session(self) -> aiohttp.ClientSession:
        """
        Get the current session, creating one if it doesn't exist.
        
        Returns:
            Optional[aiohttp.ClientSession]: Current session or None if not created
        """
        if not self.session or self.session.closed:
            return self.create_session()
        return self.session