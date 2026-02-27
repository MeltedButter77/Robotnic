# Robotnic - Dynamic Voice Channels Discord Bot

Robotnic is an open-source Discord bot designed to intelligently 
manage dynamic voice channels. It automatically creates, manages, and 
deletes temporary voice channels based on user activity. This keeps your 
server clean and organized.

You can invite the public instance to your own server for free using
👉[invite Robotnic](https://discord.com/oauth2/authorize?client_id=853490879753617458)
or join the support server to test it out 👉[Support Server](https://discord.gg/rcAREJyMV5).

Alternativly, you can test its functionallity in our 👉[Example Server](https://discord.gg/xm5aNaW737). It includes pre-configured creator channels that show off the variety of use cases for Robotnic.

See the bot's current stats on its 👉[website](https://jackschultz.dev/Robotnic/) or read a bit about its development on 👉[jackschultz.dev](https://jackschultz.dev/projects/discordBot.html).

## Example gif
![dr-robotnic](https://github.com/user-attachments/assets/c20813de-2453-497d-adc2-e1d23843603d)

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

4. Users can control their channel

The owner of a channel has many controls over it like:
   - Lock or Hide from a default role set in the creator
   - Allow or Ban any role or user
   - Change its name
   - Change the limit
   - Change

5. Highly configurable for server owners

As a server owner you can:
   - Enable or disable each control available to channel owners
   - Set a logging channel and edit which events are logged
   - Editable profanity filter powered by [profanity.dev](https://www.profanity.dev/)

6. SQLite Database Integration

All creator and temporary channel data is stored persistently. This 
means if the bot goes offline or restarts no data is lost, no 
orphaned Discord channels possible.

7. Slash Commands & UI Components. 

Controlled entirely within Discord using dropdowns, buttons, and modals built with Pycord 2.6+ for smooth interaction.

Requirements.txt
- py-cord==2.7.0
- PyNaCl==1.5.0
- python-dotenv>=1.0.0
- topggpy>=1.4.0
- requests>=2.31
- SQLite (included by default with Python)

## Commands Overview
- `/setup` -> Create a new Creator Channel and open the configuration menu.
- `/settings controls` -> Change which controls are avaliable for channel owners to use
- `/settings logging` -> Enable channel logging and edit which events to log
- `/settings profanity_filter` -> Select your preferred way to handle profanity in channel names

## Self-Hosting Setup
If you’d like to run your own instance of Robotnic:
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
4. Configure the Bot. In the .env file, replace `TOKEN_HERE` with your bot's token. (You need to make a Discord Bot through Discord's Developer Portal)
```
TOKEN=TOKEN_HERE
```
5. Run the Bot
```bash
python main.py
```
Optionally: Edit the settings.json below is the default settings with explinations of their options. Please note json does not support comments, do not include comments in your settings.json file.
```
{    
    {
    // Enables or disables console and logfile output for the bot or discord. 
    // If your bot isn't working correctly, change "bot" to true. 
    // Then reading the debug errors may explain the problem.
    "debug": {
        "discord": false,
        "bot": true
    },
    // Allows setting a channel ID to notify the bot owner of enabled events
    "notifications": {
        "channel_id": null,
        "start": true,
        "reconnect": true,
        "stop": true,
        "guild_join": true,
        "channel_create": false,
        "channel_remove": false
    },
    // Edit the status of the bot. Accepts variables {server_count} and {member_count}
    "status": {
        "text": "Online in {server_count} servers | {member_count} users."
    }
}

```
Please make sure you have message, member and activity intents enabled in the Discord Developer Portal for your bot.

## Planned Future Features
Join the 👉[Discord Server](https://discord.gg/rcAREJyMV5) to keep up to date with any developments.
