# Personal AI Agent

Connect your Home Assistant to Personal AI for intelligent voice and chat control of your smart home.

## Features

- 🗣️ Natural language control: "Turn off all the lights and lock the door"
- 🧠 AI remembers your preferences: "I like it at 72°F when I sleep"
- 🏠 Intent recognition: "I'm heading to bed" → runs your bedtime routine
- 🔒 Secure: Outbound connection only, no port forwarding needed
- ⚡ Fast: Direct WebSocket connection

## Installation

1. **Get your Agent Token**
   - Go to [Personal AI](https://your-personalai-server.com)
   - Sign up / Log in
   - Navigate to Settings → Home Assistant
   - Click "Generate Agent Token"
   - Copy the token

2. **Install the Add-on**
   - In Home Assistant, go to Settings → Add-ons
   - Click the three dots → Repositories
   - Add: `https://github.com/yourusername/personalai-ha-addon`
   - Find "Personal AI Agent" and click Install

3. **Configure**
   - Go to the add-on Configuration tab
   - Paste your Agent Token
   - Click Save
   - Start the add-on

4. **Done!**
   - Go back to Personal AI and start chatting
   - Say "Turn on the living room lights" to test

## Configuration

| Option | Description |
|--------|-------------|
| `server_url` | Personal AI server URL (default provided) |
| `agent_token` | Your unique agent token from Personal AI |

## Troubleshooting

**Add-on won't start**
- Check that your agent token is correct
- Look at the add-on logs for error messages

**Commands not working**
- Verify the add-on shows "Connected to Personal AI!" in logs
- Make sure your devices are named clearly in Home Assistant

**Connection drops**
- The agent automatically reconnects
- Check your internet connection

## Privacy & Security

- The agent connects **outbound** to Personal AI (no incoming ports needed)
- Your HA token stays local - only commands are sent through the tunnel
- All communication is encrypted via WSS (WebSocket Secure)
- You can revoke access anytime by stopping the add-on

## Support

- [Documentation](https://docs.your-personalai-server.com)
- [Discord Community](https://discord.gg/xxx)
- [GitHub Issues](https://github.com/yourusername/personalai-ha-addon/issues)
