# Binance API key and secret (only needed for authenticated endpoints)
$apiKey = "hoyinEKcYyPHBf7DSOL4YscSjpX8iRKs1Sj03WjxWsh2r1iFeYcChjD80HsWY342"
$apiSecret = "NElUR1utqiVuX4MM4g8dtQ1XtqxrZBYlGhwUDYSQIGa30jhkO1WPxbDeNyTZJz9y"

# Base URL for Binance Futures API
$baseUrl = "https://fapi.binance.com"

# Frequency of requests in seconds
$intervalSeconds = 10

# Define endpoints with HTTP method
$endpoints = @(
    @{ Method = "GET";    Path = "/fapi/v1/exchangeInfo" },
    @{ Method = "GET";    Path = "/fapi/v1/openOrders" },
    @{ Method = "GET";    Path = "/fapi/v1/time" },
    @{ Method = "GET";    Path = "/fapi/v3/account" },
    @{ Method = "GET";    Path = "/fapi/v3/balance" },
    @{ Method = "GET";    Path = "/fapi/v1/order" },
    @{ Method = "GET";    Path = "/fapi/v2/ticker/price" },
    @{ Method = "GET";    Path = "/fapi/v1/klines" },

    @{ Method = "POST";   Path = "/fapi/v1/order" },
    @{ Method = "POST";   Path = "/fapi/v1/leverage" },

    @{ Method = "DELETE"; Path = "/fapi/v1/order" },
    @{ Method = "DELETE"; Path = "/fapi/v1/allOpenOrders" }
)

# Function to send a request
function Send-Request {
    param (
        [string]$method,
        [string]$path
    )

    $url = "$baseUrl$path"

    $headers = @{
        "X-MBX-APIKEY" = $apiKey
    }

    try {
        switch ($method) {
            "GET" {
                Invoke-RestMethod -Uri $url -Method GET -Headers $headers -ErrorAction Stop
                Write-Host "[$(Get-Date -Format T)] GET $path → OK"
            }
            "POST" {
                # Dummy payload to avoid side effects
                $body = @{ symbol = "BTCUSDT"; side = "BUY"; type = "MARKET"; quantity = 0.001 }
                Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -ErrorAction Stop
                Write-Host "[$(Get-Date -Format T)] POST $path → OK"
            }
            "DELETE" {
                # Dummy params to avoid side effects
                $params = "?symbol=BTCUSDT"
                Invoke-RestMethod -Uri "$url$params" -Method DELETE -Headers $headers -ErrorAction Stop
                Write-Host "[$(Get-Date -Format T)] DELETE $path → OK"
            }
            default {
                Write-Host "Unsupported method: $method"
            }
        }
    }
    catch {
        Write-Host "[$(Get-Date -Format T)] $method $path → ERROR: $_"
    }
}

# Main loop
while ($true) {
    foreach ($endpoint in $endpoints) {
        Send-Request -method $endpoint.Method -path $endpoint.Path
    }

    Write-Host "`nSleeping $intervalSeconds seconds...`n"
    Start-Sleep -Seconds $intervalSeconds
}