import os
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('arnoldii')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} has connected to Discord!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="mentions and calls"))
    logger.info("Arnoldii is ready to chat!")

@bot.event
async def on_message(message):
    # Process commands first (this is needed for commands to work with on_message)
    await bot.process_commands(message)

@bot.command(name='hello')
async def hello(ctx):
    """Simple command to test if the bot is working"""
    await ctx.send(f'Hello! I am Arnoldii, developed by Astragate. How can I help you today?')

# Run the bot
def main():
    # Load DeepSeek knowledge cog if API key is available
    if os.getenv('DEEPSEEK_API_KEY'):
        bot.load_extension('cogs.deepseek_knowledge')
        logger.info("DeepSeek knowledge capabilities enabled")
    else:
        logger.warning("DeepSeek API key not found. Chatbot features disabled.")
        logger.warning("Please set the DEEPSEEK_API_KEY environment variable.")

    # Start the bot
    bot.run(TOKEN)

if __name__ == '__main__':
    main()
