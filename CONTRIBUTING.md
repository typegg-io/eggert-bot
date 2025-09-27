# Contributing to Eggert <img src="assets/images/eggert_construction.png" alt="Eggert" width="50" style="vertical-align: bottom;"/>

Thank you for your interest in contributing to Eggert! Follow the instructions here to get started:

---

## Installation

1. Install Python 3.12 or later: <https://www.python.org/downloads/>
2. Clone the repository using the following command:

   ```
   git clone https://github.com/typegg-io/eggert-bot
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

---

## Creating a Bot

To test Eggert, you'll need to create your own Discord bot and retrieve it's token:

### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, give your application a name and click **Create**.

### Step 2: Obtaining the Token

Under the **Bot** tab, click **Reset Token** to obtain your bot's token. Save this for later.\
_Anyone with this token can run your bot, do not share it!_

### Step 3: Bot Permissions & Intents

To ensure the bot functions correctly, it requires specific **intents** and **permissions**.

Enable the bots required **intents**:

1. Under the **Bot** tab, scroll to **Privileged Gateway Intents**
2. Enable the following **intents**:
   - **Message Content Intent** – Allows the bot to read user messages for commands
   - **Server Members Intent** – Required to add/remove roles

When adding the bot to a server, it will require the following **permissions**:

#### General Permissions

- **Manage Roles** – Required to add and remove roles from users
  - **Note**: The bot cannot manage roles above its own role
- **View Channels** - Required to view guild channels

#### Text Permissions

- **Send Messages** – Allows the bot to reply to commands
- **Embed Links** - Allows the bot to send rich embeds
- **Attach Files** - Allows the bot to attach images and other files
- **Read Message History** – Ensures the bot can access previous messages in a channel

#### Installation Context

Under installation, ensure the **Guild Install** option is enabled. This allows the bot to be invited via an OAuth link.

### Step 4: Adding the Bot

To invite the bot with the necessary permissions to a server, use the following OAuth link:

```
https://discord.com/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=268553216&integration_type=0&scope=bot
```

Replace `YOUR_BOT_ID` with your bot's client ID. This can be found under General Information > Application ID.

To add any additional permissions, use the [Discord Permissions Calculator](https://discordapi.com/permissions.html).

---

## Setup

### Step 1: Configure Environment Variables

Create a `.env` file in the project's root directory and include the following:

```
BOT_TOKEN=[Your Bot Token]
API_URL=https://api.typegg.io/v1
SITE_URL=https://typegg.io
```

- **`BOT_TOKEN`**: This is your bot's authentication token obtained in the **Creating a Bot** section.

### Step 2: Configure Bot Settings

Modify bot prefix in `config.py` if needed.

### Step 3: Run the Bot
Make sure you are in the `src` directory, then run the following command:
```bash
python main.py
```

The bot should now appear as online and respond to commands, at which point you're ready for development!

---

## Code Structure Explanation

**Project structure:**

```
/src
    /api                # Files for handling web requests
    /commands           # Bot command files
        template.txt    # Command template to copy when creating new commands
    /data               # Bot's database is stored here
    /database           # Files for handling database interactions
    /graphs             # Graphing module responsible for generating and managing graphs
    /utils              # Utility files and helper functions
config.py               # Bot configuration file
error_handler.py        # Global bot error handler
main.py                 # Entry point of the application
web_server.py           # Web server to listen for verification requests
```

**Navigating the Code:**

- Core bot logic is located in `main.py`.
- Each command has its own file in `/commands`.
- Data related files should be stored in `/data`.
- Each graph has its own file in `/graphs`

---

## Adding New Commands

1. Navigate to `/commands`, under the appropriate subdirectory
2. Create a new Python file for the command (file name should match the name of the command)
3. Copy the code from `template.txt` into the new file
4. Update the class name, and the function name to match the name of the command
5. Update the info dictionary with the command name, aliases, description, and parameter string
6. Parameters are received from the class's main function, and can be passed to a run function for further processing and output

---

## Reporting Issues

If you encounter any issues, please [open an issue](https://github.com/TypeGGio/TypeGG-Stats/issues) including:

- A description of the problem
- Steps to reproduce it
- Any relevant error or log messages

---

## Pull Requests

1. Fork the repository and create a new branch for your code
2. Ensure your code follows the project's code and style conventions
3. Submit a pull request with a description of the changes
