import os
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    # Don't respond to our own messages
    if message.author == bot.user:
        return

    # Process commands first (this is needed for commands to work with on_message)
    await bot.process_commands(message)

@bot.command(name='hello')
async def hello(ctx):
    """Simple command to test if the bot is working"""
    await ctx.send(f'Hello! I am Arnoldii, developed by Astragate. How can I help you today?')

# Simple HTTP server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Arnoldii is alive!')

def start_http_server():
    server_address = ('', int(os.getenv('PORT', 10000)))
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Starting HTTP server on port {server_address[1]}")
    httpd.serve_forever()

# Run the bot
async def main():
    # Start HTTP server in a separate thread to keep the bot alive on Render
    if os.getenv('PORT'):
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        logger.info("HTTP server thread started")

    # Load DeepSeek knowledge cog if API key is available
    if os.getenv('DEEPSEEK_API_KEY'):
        await bot.load_extension('cogs.deepseek_knowledge')
        logger.info("DeepSeek knowledge capabilities enabled")
    else:
        logger.warning("DeepSeek API key not found. Chatbot features disabled.")
        logger.warning("Please set the DEEPSEEK_API_KEY environment variable.")

    # Start the bot
    await bot.start(TOKEN)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
