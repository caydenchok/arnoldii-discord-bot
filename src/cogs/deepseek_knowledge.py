import os
import logging
import discord
from discord.ext import commands, tasks
import asyncio
import time
import json
import requests
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
import gc

logger = logging.getLogger('arnoldii.deepseek')

class DeepSeekKnowledge(commands.Cog):
    """Main cog for Arnoldii chatbot using DeepSeek API"""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"  # Default model

        # Store conversation history for each channel (with a limit on total channels)
        self.conversation_history = defaultdict(lambda: deque(maxlen=5))
        self.max_channels = 10  # Limit the number of channels we store history for
        self.channel_last_used = {}  # Track when each channel was last used

        # System prompt for DeepSeek
        self.system_prompt = (
            "You are Arnoldii, an advanced AI assistant developed by Astragate. "
            "You are helpful, friendly, and extremely knowledgeable. "
            "Always introduce yourself as 'Arnoldii, developed by Astragate' when meeting someone new. "
            "You can answer questions on a wide range of topics with accurate, up-to-date information. "
            "When you don't know something, admit it rather than making up information. "
            "Keep your responses conversational but informative."
        )

        # Track usage to avoid exceeding rate limits or budget
        self.usage_tracking = {
            'total_tokens': 0,
            'requests_today': 0,
            'last_reset': datetime.now().date()
        }

        # Start memory cleanup task
        self.memory_cleanup.start()

    async def call_deepseek_api(self, messages):
        """Call the DeepSeek API with the given messages"""
        if not self.api_key:
            return "Error: DeepSeek API key not configured. Please set the DEEPSEEK_API_KEY environment variable."

        # Check if we need to reset the daily counter
        today = datetime.now().date()
        if today > self.usage_tracking['last_reset']:
            self.usage_tracking['requests_today'] = 0
            self.usage_tracking['last_reset'] = today

        # Increment request counter
        self.usage_tracking['requests_today'] += 1

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,  # Reduced from 1000 to save memory
            "stream": False
        }

        try:
            # Define a synchronous function for the request
            def _make_request():
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                return response.json()

            # Run the request in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            response_json = await loop.run_in_executor(None, _make_request)

            # Track token usage if available in the response
            if 'usage' in response_json and 'total_tokens' in response_json['usage']:
                self.usage_tracking['total_tokens'] += response_json['usage']['total_tokens']
                logger.info(f"Total tokens used: {self.usage_tracking['total_tokens']}")

            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content']
            else:
                logger.error(f"Unexpected API response: {response_json}")
                return "I encountered an error while processing your request. Please try again later."

        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return f"I encountered an error: {str(e)}"

    def _manage_channel_history(self, channel_id):
        """Manage channel history to prevent memory bloat"""
        # Update the last used time for this channel
        current_time = time.time()
        self.channel_last_used[channel_id] = current_time

        # If we have too many channels, remove the oldest ones
        if len(self.conversation_history) > self.max_channels:
            # Find the least recently used channels
            channels_by_time = sorted(self.channel_last_used.items(), key=lambda x: x[1])
            # Remove oldest channels until we're under the limit
            channels_to_remove = len(self.conversation_history) - self.max_channels
            for i in range(channels_to_remove):
                if i < len(channels_by_time):
                    old_channel = channels_by_time[i][0]
                    if old_channel in self.conversation_history:
                        del self.conversation_history[old_channel]
                        del self.channel_last_used[old_channel]
                        logger.info(f"Removed history for channel {old_channel} to save memory")

    def _format_conversation(self, channel_id, new_user_message=None):
        """Format the conversation history for the AI"""
        # Manage channel history first
        self._manage_channel_history(channel_id)

        # Start with the system prompt
        formatted = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history - convert to list to avoid iteration issues
        history_list = list(self.conversation_history[channel_id])
        for speaker, message in history_list:
            role = "assistant" if speaker == "Arnoldii" else "user"
            formatted.append({"role": role, "content": message})

        # Add the new message if provided
        if new_user_message:
            formatted.append({"role": "user", "content": new_user_message})

        return formatted

    async def send_response(self, ctx, response):
        """Send a response, splitting into chunks if necessary"""
        # Limit extremely long responses to save memory
        if len(response) > 6000:
            response = response[:6000] + "... (response truncated to save memory)"

        if len(response) > 1900:
            # Process one chunk at a time to avoid storing all chunks in memory
            for i in range(0, len(response), 1900):
                chunk = response[i:i+1900]
                if i == 0:
                    await ctx.send(chunk)
                else:
                    await ctx.send(f"(continued) {chunk}")
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
        else:
            await ctx.send(response)

        # Force garbage collection after sending large responses
        if len(response) > 3000:
            gc.collect()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that might be directed at Arnoldii"""
        # Don't respond to our own messages
        if message.author == self.bot.user:
            return

        # Don't respond to commands (they start with the bot's prefix)
        if message.content.startswith('a!'):
            return

        # Check if the bot is mentioned or called by name
        is_mentioned = self.bot.user.mentioned_in(message) and not message.mention_everyone
        is_called = any(name.lower() in message.content.lower() for name in ['arnoldii', 'arnold'])

        if is_mentioned or is_called:
            async with message.channel.typing():
                # Get the content of the message
                content = message.content

                # If the bot is mentioned, remove the mention from the content
                if is_mentioned:
                    content = re.sub(f'<@!?{self.bot.user.id}>', '', content).strip()

                # If the content is empty after removing the mention, treat it as a greeting
                if not content:
                    content = "Hello"

                # Add the user message to history
                channel_id = message.channel.id
                self.conversation_history[channel_id].append(("User", content))

                # Format the conversation with history
                messages = self._format_conversation(channel_id)

                # Call the API
                start_time = time.time()
                response = await self.call_deepseek_api(messages)
                response_time = time.time() - start_time
                logger.info(f"DeepSeek API response time: {response_time:.2f} seconds")

                # Add the bot's response to history
                self.conversation_history[channel_id].append(("Arnoldii", response))

                # Send the response
                await self.send_response(message.channel, response)

    @commands.command(name='chat')
    async def chat(self, ctx, *, message: str):
        """Chat with Arnoldii"""
        async with ctx.typing():
            # Add the user message to history
            channel_id = ctx.channel.id
            self.conversation_history[channel_id].append(("User", message))

            # Format the conversation with history
            messages = self._format_conversation(channel_id)

            # Call the API
            start_time = time.time()
            response = await self.call_deepseek_api(messages)
            response_time = time.time() - start_time
            logger.info(f"DeepSeek API response time: {response_time:.2f} seconds")

            # Add the bot's response to history
            self.conversation_history[channel_id].append(("Arnoldii", response))

            # Send the response
            await self.send_response(ctx, response)

    @commands.command(name='clear')
    async def clear_chat(self, ctx):
        """Clear the conversation history for this channel"""
        channel_id = ctx.channel.id
        self.conversation_history[channel_id].clear()
        await ctx.send("✅ Conversation history cleared!")

    @commands.command(name='usage')
    async def check_usage(self, ctx):
        """Check the current DeepSeek API usage"""
        if ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="DeepSeek API Usage",
                description="Current usage statistics for the DeepSeek API",
                color=discord.Color.blue()
            )

            embed.add_field(name="Total Tokens Used", value=str(self.usage_tracking['total_tokens']), inline=True)
            embed.add_field(name="Requests Today", value=str(self.usage_tracking['requests_today']), inline=True)
            embed.add_field(name="Last Reset", value=str(self.usage_tracking['last_reset']), inline=True)

            await ctx.send(embed=embed)
        else:
            await ctx.send("You need administrator permissions to check API usage.")

    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        # Cancel the memory cleanup task
        self.memory_cleanup.cancel()
        # Clear conversation history to free memory
        self.conversation_history.clear()
        self.channel_last_used.clear()
        # Force garbage collection
        gc.collect()
        logger.info("DeepSeek knowledge cog unloaded and memory cleaned up")

    @tasks.loop(minutes=30)
    async def memory_cleanup(self):
        """Periodically clean up memory to prevent leaks"""
        try:
            # Remove old channel histories
            current_time = time.time()
            channels_to_remove = []

            # Find channels that haven't been used in the last 2 hours
            for channel_id, last_used in self.channel_last_used.items():
                if current_time - last_used > 7200:  # 2 hours in seconds
                    channels_to_remove.append(channel_id)

            # Remove the old channels
            for channel_id in channels_to_remove:
                if channel_id in self.conversation_history:
                    del self.conversation_history[channel_id]
                    del self.channel_last_used[channel_id]

            if channels_to_remove:
                logger.info(f"Memory cleanup: removed {len(channels_to_remove)} inactive channels")

            # Force garbage collection
            gc.collect()

            # Log memory usage if possible
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                logger.info(f"Current memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
            except ImportError:
                pass  # psutil not available

        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")

    @memory_cleanup.before_loop
    async def before_memory_cleanup(self):
        """Wait until the bot is ready before starting the cleanup task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(DeepSeekKnowledge(bot))
