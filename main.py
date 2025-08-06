import sys
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
# nest_asyncio.apply()

from logic.strategies.szalai_strategy import SzalaiStrategy


async def main_async():
    """Asynchronous main function to run the strategy."""
    
    # Initialize the SzalaiStrategy
    szalai_strategy = SzalaiStrategy()

    try:  
        await szalai_strategy.start_strategy()    
    except KeyboardInterrupt:
        await szalai_strategy.stop_strategy()
        return 0
    except ValueError as e:
        szalai_strategy.logger.error(e)
        await szalai_strategy.stop_strategy()
        return 1
    except Exception as e:
        szalai_strategy.logger.exception(e)
        await szalai_strategy.stop_strategy()
        return 1
    return 0

def main():
    """Initializes and runs strategies."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)
    
# Entry point of the script
if __name__ == "__main__":
    main()