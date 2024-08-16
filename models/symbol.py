class Symbol:
    """
    Represents a trading symbol.

    Attributes:
        symbol (str): The trading symbol.
        price_precision (int): The price precision.
        quantity_precision (int): The quantity precision.
        base_asset_precision (int): The base asset precision.
        quote_precision (int): The quote precision.
    """

    def __init__(
        self, 
        symbol: str, 
        price_precision: int,
        quantity_precision: int,
        base_asset_precision: int,
        quote_precision: int 
    ) -> None:
        """
        Initializes a new instance of the Symbol class.

        Args:
            symbol (str): The trading symbol.
            price_precision (int): The price precision.
            quantity_precision (int): The quantity precision.
            base_asset_precision (int): The base asset precision.
            quote_precision (int): The quote precision.
        """
        self.symbol = symbol
        self.price_precision = price_precision
        self.quantity_precision = quantity_precision
        self.base_asset_precision = base_asset_precision
        self.quote_precision = quote_precision