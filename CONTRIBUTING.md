# Contributing to Eggert <img src="assets/images/eggert_construction.png" alt="Eggert" width="50" style="vertical-align: middle;"/>

Thank you for your interest in contributing to Eggert! Follow the instructions here to get started:

---

## Installation

1. Install Python 3.12 or later: <https://www.python.org/downloads/>
2. Clone the repository using the following command:

   ```
   git clone https://github.com/typegg-io/eggert-bot
   cd eggert-bot
   ```
3. (Recommended) Create and activate a virtual environment:
   ```
   python -m venv venv

   # On Linux/Mac:
   source venv/bin/activate

   # On Windows (PowerShell):
   .\venv\Scripts\activate
   ```

4. Install dependencies:

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
API_URL=https://api.typegg.io
SITE_URL=https://typegg.io
BOT_SUBDOMAIN=http://localhost:8888
```

- **`BOT_TOKEN`**: This is your bot's authentication token obtained in the **Creating a Bot** section.

Everything else is optional. The bot runs in staging mode whenever `MESSAGE_WEBHOOK` is unset,
which routes logs to the console instead of Discord and enables hot reload.

### Step 2: Configure Bot Settings

Modify bot prefix in `config.py` if needed.

### Step 3: Run the Bot

Make sure you are in the `src` directory, then run the following command:

```bash
python main.py
```


The bot should now appear as online and respond to commands, at which point you're ready for development!

<details>
<summary>Running into problems?</summary>

If you're getting an error that looks similar to the following:

```
ModuleNotFoundError: No module named 'audioop'
```
You are probably in a virtual environment using the wrong version of Python. Please ensure that you are using Python 3.12, as mentioned earlier in these instructions!

</details>

---

## Code Structure Explanation

**Project structure:**

```
/src
    /api                # TypeGG API client, one module per resource
    /commands           # Bot commands, one file per command, grouped into subdirectories
        template.txt    # Command template to copy when creating new commands
    /data               # Databases and data files (gitignored)
    /database           # Database access layer
        /bot            # users.db: Discord users, themes, settings, command usage
        /typegg         # typegg.db: imported races, quotes, matches, keystrokes
    /graphs             # Matplotlib rendering, one module per graph type
    /utils              # Helpers: strings, dates, flags, messages, errors, keystrokes
    /web_server         # aiohttp server: verification, site callbacks, public pages
bot_setup.py            # Bot subclass, flag parsing, global checks and event handlers
config.py               # Bot configuration and environment variables
error_handler.py        # Global bot error handler
main.py                 # Entry point of the application
tasks.py                # Scheduled background tasks (daily quote, status rotation)
watcher.py              # Hot reload for staging
```

**Navigating the Code:**

- `main.py` is the entry point, but the core bot logic lives in `bot_setup.py`: flag parsing,
  global checks, and the message and command event handlers.
- Each command has its own file in `/commands`, under the subdirectory matching its help category.
- Each graph has its own rendering module in `/graphs`. Command files in `/commands/graphs` build
  the message; modules in `/graphs` draw the image.
- Data related files should be stored in `/data`.

---

## Development Tooling

Linting is handled by [ruff](https://docs.astral.sh/ruff/), configured in `pyproject.toml`.

Install the git hooks once after cloning:

```bash
pip install pre-commit
pre-commit install
```

The hook autofixes unused imports and import order, then fails if anything is left. Re-stage and
commit again when it rewrites a file. To check the whole tree by hand:

```bash
ruff check src
pre-commit run --all-files
```

The ruff **formatter** is deliberately not used. It rewrites the nested quotes in f-strings that
this codebase relies on throughout its embed content. Only the linter runs.

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

If you encounter any issues, please [open an issue](https://github.com/typegg-io/eggert-bot/issues) including:

- A description of the problem
- Steps to reproduce it
- Any relevant error or log messages

---

## Pull Requests

1. Fork the repository and create a new branch for your code
2. Ensure your code follows the project's code and style conventions
3. Submit a pull request with a description of the changes
