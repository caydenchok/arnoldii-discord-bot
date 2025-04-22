# Deploying Arnoldii on Render

This guide explains how to deploy the Arnoldii Discord bot on Render.

## Deployment Steps

1. **Sign up for Render** at https://render.com

2. **Create a new Web Service**:
   - Connect your GitHub repository
   - Select the repository containing your Arnoldii bot

3. **Configure the service**:
   - **Name**: arnoldii-discord-bot (or any name you prefer)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free
   - **Instance Type**: Free

4. **Set environment variables**:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `DEEPSEEK_API_KEY`: Your DeepSeek API key
   - `PORT`: 10000 (This is required for the health check server)

5. **Deploy the service**:
   - Click "Create Web Service"
   - Wait for the deployment to complete

## Keeping the Bot Online

The bot includes a built-in HTTP server that responds to health checks, which helps prevent Render's free tier from spinning down after 15 minutes of inactivity.

To further ensure your bot stays online:

1. **Set up a health check service**:
   - Use a service like UptimeRobot (https://uptimerobot.com)
   - Create a new monitor in UptimeRobot
   - Set it to HTTP(S) type
   - Use your Render URL as the target (e.g., https://arnoldii-discord-bot.onrender.com)
   - Set the monitoring interval to 5 minutes

2. **Consider a paid plan**:
   - For $7/month, you can upgrade to Render's Individual plan for more reliable uptime

## Troubleshooting

If your bot goes offline or doesn't work as expected:

1. Check the Render logs for any errors
2. Verify your environment variables are set correctly
3. Make sure your Discord bot has the proper permissions in your server

For more detailed instructions, refer to the main README.md file.
