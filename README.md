# Dr Robotnic - Dynamic Voice Channels Discord Bot

Dr. Robotnic is an open-source Discord bot designed to intelligently 
manage dynamic voice channels. It automatically creates, manages, and 
deletes temporary voice channels based on user activity. This keeps your 
server clean and organized.

You can invite the public instance to your own server for free using
👉 [invite Dr. Robotnic](https://discord.com/oauth2/authorize?client_id=853490879753617458)
or join the support server to test it out 👉 [Support Server](https://discord.gg/rcAREJyMV5).

## Features
1. Dynamic Voice Channel Management
Automatically creates personal or activity-based voice channels when 
users join a “creator” channel.

2. Automatic Cleanup
Removes empty temporary channels to keep your server tidy.

3. Configurable Creator Channels
Server admins can customize:
   - Channel name patterns (e.g. {user}'s channel)
   - User limits
   - Parent categories
   - Permission inheritance (none, from creator, or from category)

4. SQLite Database Integration
All creator and temporary channel data is stored persistently. This 
means if the bot goes offline or restarts no data is lost, no 
orphaned Discord channels possible.

5. Slash Commands & UI Components. Controlled entirely in Discord
Built with Pycord 2.6+, using dropdowns, buttons, and modals for smooth interaction.

Requirements.txt
- Python 3.11+
- Pycord 2.6.1
- Python dotenv 1.0.0
- PyNaCl 1.5.0
- SQLite (included by default with Python)

## Commands Overview
- `/ping` -> Test the bot’s latency.
- `/creator` -> Create a new Creator Channel and open the configuration menu.

## Self-Hosting Setup
If you’d like to run your own instance of Dr. Robotnic:
1. Clone the Repository
```bash
git clone https://github.com/MeltedButter77/Robotnic.git
cd Robotnic
```
2. Install Dependencies
```bash
pip install -r requirements.txt
```
3. Run the main.py file to create the settings.json, database.db and .env files.
```bash
python main.py
```
4. Configure the Bot. Replace `TOKEN_HERE` with your bot's token. (You need to make a Discord Bot through Discord's Developer Portal)
```
TOKEN=TOKEN_HERE
```
5. Run the Bot
```bash
python main.py
```
Please make sure you have message, member and activity intents enabled in the Discord Developer Portal for your bot.

## Planned Future Features:
1. Support {count} and {activity} channel name variables
   1. Change temp channel count to always be ascending & not missing lower number
2. Owner's of temp channels being able to control its visibility, kick or ban members, edit its name & more
   1. If an owner has left, any user can claim the channel
   2. All options should be togglable by admins when creating the Creator Channel
3. Send a message on server join explaining the bot
4. Improve lack of permission handling. Currently, there is a high chance of errors if the bot has insufficient permissions.
5. Create a website to advertise and explain the bot's features
