from logic.strategies.szalai_strategy import SzalaiStrategy

def main():
    """Initializes and runs strategies."""
    
    # Initialize the SzalaiStrategy
    szalai_strategy = SzalaiStrategy()

    # Run the strategy
    try:   
        szalai_strategy.start_strategy()
    except KeyboardInterrupt:
        # Stop the strategy
        szalai_strategy.stop_strategy()

# Entry point of the script
if __name__ == "__main__":
    main()