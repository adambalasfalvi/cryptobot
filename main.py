import sys
from logic.strategies.szalai_strategy import SzalaiStrategy

def main():
    """Initializes and runs strategies."""
    
    # Initialize the SzalaiStrategy
    szalai_strategy = SzalaiStrategy()

    # Run the strategy
    try:   
        szalai_strategy.start_strategy()
    except KeyboardInterrupt:
        szalai_strategy.stop_strategy()
        sys.exit(0)
    except ValueError as e:
        szalai_strategy.logger.error(e)
        sys.exit(1)
    except Exception as e:
        szalai_strategy.logger.exception(e)
        szalai_strategy.stop_strategy()
        sys.exit(1)

# Entry point of the script
if __name__ == "__main__":
    main()