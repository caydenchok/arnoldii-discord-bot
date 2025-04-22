import os
import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

# Track start time for uptime reporting
start_time = time.time()

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

# Create bot instance with auto-reconnect
bot = commands.Bot(
    command_prefix='a!',  # Changed to 'a!' for Arnoldii
    intents=intents,
    reconnect=True,  # Enable auto-reconnect
    max_messages=None,  # Don't store message cache to save memory
    heartbeat_timeout=60.0  # Increase heartbeat timeout
)

@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} has connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected to {len(bot.guilds)} servers')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="mentions and calls"))
    logger.info("Arnoldii is ready to chat!")

@bot.event
async def on_connect():
    logger.info("Bot connected to Discord gateway")

@bot.event
async def on_disconnect():
    logger.error("Bot disconnected from Discord gateway")

@bot.event
async def on_resumed():
    logger.info("Bot connection resumed")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Discord error in {event}: {str(args[0])}")

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

# Simple HTTP server for health checks with bot status
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global bot
        status_code = 200

        if self.path == '/status':
            # Detailed status endpoint
            latency_str = f"{bot.latency * 1000:.2f}ms" if bot.is_ready() else "N/A"
            content = f"""Arnoldii Bot Status:
- Running: Yes
- Connected to Discord: {bot.is_ready()}
- Server Count: {len(bot.guilds) if bot.is_ready() else 'N/A'}
- Latency: {latency_str}
- Uptime: {time.time() - start_time:.2f} seconds
"""
            if not bot.is_ready():
                status_code = 503  # Service Unavailable
        else:
            # Simple health check
            content = 'Arnoldii is alive!'

        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress HTTP logs to avoid cluttering the output
        return

def start_http_server():
    server_address = ('', int(os.getenv('PORT', 10000)))
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Starting HTTP server on port {server_address[1]}")
    httpd.serve_forever()

# Heartbeat task to help keep the connection alive
@tasks.loop(minutes=5)
async def connection_heartbeat():
    """Send a heartbeat to help maintain the Discord connection"""
    try:
        logger.info(f"Heartbeat: Bot is {'connected' if bot.is_ready() else 'not connected'} to Discord")
        logger.info(f"Heartbeat: Connected to {len(bot.guilds)} servers")

        # Log latency
        if bot.latency:
            logger.info(f"Heartbeat: Current latency: {bot.latency * 1000:.2f}ms")

        # If we're not connected, try to reconnect
        if not bot.is_ready() and bot.ws and bot.ws.socket and not bot.ws.socket.open:
            logger.warning("Heartbeat: Connection appears to be closed. Attempting to reconnect...")
            try:
                await bot.close()
                await asyncio.sleep(5)
                await bot.start(TOKEN)
            except Exception as e:
                logger.error(f"Heartbeat: Failed to reconnect: {e}")
    except Exception as e:
        logger.error(f"Heartbeat: Error in heartbeat task: {e}")

@connection_heartbeat.before_loop
async def before_heartbeat():
    """Wait until the bot is ready before starting the heartbeat"""
    await bot.wait_until_ready()

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

    # Start the heartbeat task
    connection_heartbeat.start()
    logger.info("Connection heartbeat task started")

    # Start the bot
    try:
        logger.info("Starting bot connection to Discord...")
        await bot.start(TOKEN)
    except discord.errors.LoginFailure as e:
        logger.error(f"Failed to login to Discord: {e}")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
