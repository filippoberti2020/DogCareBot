# PawsomeBot

A Python Telegram bot designed to help dog owners track their furry friend's weight and manage daily care reminders.

## ✨ Features

- **Weight Tracking**: Manually add your dog's weight on a specific date.
- **Daily Reminders**: Set multiple custom daily reminders at specific times.
- **Persistent Data**: All weights and reminders are saved to a JSON file, so your data is safe even if the bot restarts.

## 🚀 Setup and Run

### 1. Clone the Repository (or save the code):
Save the provided Python code into a file (e.g., `pawsome_bot.py`).

### 2. Install Dependencies:
Make sure you have Python installed, then install the required libraries:

```bash
pip install python-telegram-bot==13.7 apscheduler
```

### 3. Get Your Bot Token:
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram.
2. Use the `/newbot` command to create a new bot.
3. BotFather will give you an API Token.

### 4. Configure the Bot:
Open the `pawsome_bot.py` file and replace `'YOUR_BOT_TOKEN'` with the token you received from BotFather:

```python
BOT_TOKEN = 'YOUR_BOT_TOKEN'  # <<< IMPORTANT: Replace with your actual bot token
```

### 5. Run the Bot:
Execute the Python script from your terminal:

```bash
python pawsome_bot.py
```

The bot will start listening for messages.

## 🐾 Usage

Once the bot is running, you can interact with it on Telegram:

### 📋 Basic Commands
- **`/start`** - Get a welcome message and list of available commands
- **`/cancel`** - Cancel any ongoing conversation

### ⚖️ Weight Tracking
- **`/addweight`** - Record your dog's weight with date tracking
- **`/viewweights`** - View all your recorded weight measurements

### ⏰ Reminder Management
- **`/addreminder`** - Set up a new daily reminder (time + message)
- **`/listreminders`** - View all your active reminders
- **`/deletereminder <number>`** - Remove a reminder (e.g. `/deletereminder 2`)

💡 **Pro Tip:** All your data is automatically saved and persists even if the bot restarts!

🐶 Enjoy using PawsomeBot to keep your furry friend happy and healthy! ❤️
