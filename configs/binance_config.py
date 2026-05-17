# API key for authenticating with the Binance API.
#API_KEY = "hoyinEKcYyPHBf7DSOL4YscSjpX8iRKs1Sj03WjxWsh2r1iFeYcChjD80HsWY342"
API_KEY = "d0yfkb3qvWGCfH7krNaLKm0aBsml0CRhMvVVV5JLvP2RYCHQGrm5pp0ayMvkbcZC"

# API secret for authenticating with the Binance API.
#API_SECRET = "NElUR1utqiVuX4MM4g8dtQ1XtqxrZBYlGhwUDYSQIGa30jhkO1WPxbDeNyTZJz9y"
API_SECRET = "H5oFkp3KhvJMMSykmlqRNFHtbuxEkMQIvvYHauQ1psXcrz7riP3gbR4grM39ZAC7"

# Boolean flag indicating whether to use the Binance testnet environment.
# Set to True for testnet (for testing purposes) and False for the live environment.
TESTNET = True

if TESTNET:
    BASE_URL = "https://demo-fapi.binance.com"
    EXCHANGE_STRING = "binance.com-futures-testnet"
else:
    BASE_URL = "https://fapi.binance.com"
    EXCHANGE_STRING = "binance.com-futures"