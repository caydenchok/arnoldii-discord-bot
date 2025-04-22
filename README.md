# Arnoldii Discord Bot

Arnoldii is an AI assistant for Discord developed by Astragate. It uses the DeepSeek API to provide intelligent conversations and answer questions.

## Features

- **Intelligent Conversations**: Chat naturally with Arnoldii about any topic
- **Conversation Memory**: Arnoldii remembers the context of your conversations
- **Natural Interaction**: Mention Arnoldii or call it by name to get a response

## Requirements

- Python 3.8 or higher
- A Discord bot token
- DeepSeek API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/arnoldii-discord.git
   cd arnoldii-discord
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file and add your Discord bot token and DeepSeek API key.

## Running the Bot

```
python main.py
```

## Interacting with Arnoldii

### Commands

- `a!hello` - Test if the bot is working
- `a!chat <message>` - Chat with Arnoldii
- `a!clear` - Clear the conversation history for the current channel
- `a!usage` - Check DeepSeek API usage (admin only)

### Natural Interaction

Arnoldii can also respond to natural mentions without commands:

1. **Mention the bot**: Type `@Arnoldii` followed by your message
2. **Call by name**: Include "Arnoldii" or "Arnold" in your message

Examples:
- `@Arnoldii what's the weather like today?`
- `Hey Arnoldii, tell me a joke`
- `Arnold, what do you think about AI?`

The bot maintains conversation history in each channel, allowing for more natural back-and-forth interactions.

## Setting Up API Keys

### DeepSeek API

1. Sign up for an account at [DeepSeek](https://deepseek.com)
2. Navigate to your account settings or API section
3. Generate an API key
4. Add the API key to your `.env` file as `DEEPSEEK_API_KEY=your_key_here`

## Setting Up a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable "Message Content Intent"
5. Copy the token and add it to your `.env` file
6. Go to the "OAuth2" tab, then "URL Generator"
7. Select "bot" under "Scopes" and select the following permissions:
   - Send Messages
   - Read Message History
8. Copy the generated URL and open it in your browser to add the bot to your server

## About Arnoldii

Arnoldii is an advanced AI assistant developed by Astragate. It's designed to provide helpful, friendly, and knowledgeable responses to a wide range of questions and topics.

## License

MIT
