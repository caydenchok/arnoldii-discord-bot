"""
Arnoldii Discord Bot - An AI assistant developed by Astragate
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import and run the bot
from src.bot import main

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
