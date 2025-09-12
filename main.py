import sys
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
# nest_asyncio.apply()

from logic.strategies import szalai_strategy
from logic.strategies.szalai_strategy import SzalaiStrategy

def main():
    """Initializes and runs strategies."""
    strategy = SzalaiStrategy()
    try:
        asyncio.run(strategy.start_strategy())
    except KeyboardInterrupt:
        asyncio.run(strategy.stop_strategy())
        return 0
    except ValueError as e:
        strategy.logger.error(e)
        asyncio.run(strategy.stop_strategy())
        return 1
    except Exception as e:
        strategy.logger.exception(e)
        asyncio.run(strategy.stop_strategy())
        return 1
    
# Entry point of the script
if __name__ == "__main__":
    main()