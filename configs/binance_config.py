# API key for authenticating with the Binance API.
API_KEY = "hoyinEKcYyPHBf7DSOL4YscSjpX8iRKs1Sj03WjxWsh2r1iFeYcChjD80HsWY342"

# API secret for authenticating with the Binance API.
API_SECRET = "NElUR1utqiVuX4MM4g8dtQ1XtqxrZBYlGhwUDYSQIGa30jhkO1WPxbDeNyTZJz9y"

# Boolean flag indicating whether to use the Binance testnet environment.
# Set to True for testnet (for testing purposes) and False for the live environment.
TESTNET = False

if TESTNET:
    BASE_URL = "https://testnet.binancefuture.com"
else:
    BASE_URL = "https://fapi.binance.com"