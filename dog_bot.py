import logging
import json
import os
from datetime import datetime
from telegram import Update, ForceReply
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = 'YOUR_BOT_TOKEN'  # <<< IMPORTANT: Replace with your actual bot token
DATA_FILE = 'dog_care_data.json' # File to store weights and reminders

# --- Conversation States for Weight Input ---
GET_WEIGHT = 0
GET_WEIGHT_DATE = 1

# --- Conversation States for Reminder Input ---
GET_REMINDER_TIME = 0
GET_REMINDER_MESSAGE = 1

# --- Data Structure ---
# The data will be stored as a dictionary:
# {
#   "user_id": {
#     "weights": [
#       {"date": "YYYY-MM-DD", "weight": 12.5},
#       ...
#     ],
#     "reminders": [
#       {"time": "HH:MM", "message": "Feed the dog"},
#       ...
#     ]
#   },
#   ...
# }
user_data = {}

# --- Scheduler Initialization ---
scheduler = BackgroundScheduler()

# --- Helper Functions ---

def load_data():
    """Loads user data from the JSON file."""
    global user_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                user_data = json.load(f)
            logger.info("Data loaded successfully.")
        except json.JSONDecodeError:
            logger.warning("Data file is corrupt or empty. Starting with empty data.")
            user_data = {}
    else:
        logger.info("Data file not found. Starting with empty data.")
    return user_data

def save_data():
    """Saves user data to the JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=4)
        logger.info("Data saved successfully.")
    except IOError as e:
        logger.error(f"Error saving data: {e}")

def get_user_data(user_id):
    """Retrieves or initializes data for a given user ID."""
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"weights": [], "reminders": []}
    return user_data[str(user_id)]

def schedule_reminder_job(updater, chat_id, reminder_time, reminder_message):
    """Schedules a single daily reminder job."""
    try:
        # Parse time (HH:MM)
        hour, minute = map(int, reminder_time.split(':'))

        # Define the job function
        def send_reminder():
            updater.bot.send_message(chat_id=chat_id, text=f"🔔 Reminder: {reminder_message}")
            logger.info(f"Reminder sent to {chat_id} at {reminder_time}")

        # Create a unique job ID for each reminder
        job_id = f"reminder_{chat_id}_{reminder_time}_{reminder_message.replace(' ', '_')}"
        
        # Check if a similar job already exists to prevent duplicates on restart
        if scheduler.get_job(job_id):
            logger.info(f"Job '{job_id}' already exists. Skipping scheduling.")
            return

        scheduler.add_job(
            send_reminder,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True # Replace if a job with the same ID already exists
        )
        logger.info(f"Reminder scheduled for chat_id {chat_id} at {reminder_time} with message: {reminder_message}")
        return True
    except ValueError:
        logger.error(f"Invalid time format: {reminder_time}")
        return False
    except Exception as e:
        logger.error(f"Error scheduling reminder job: {e}")
        return False

def remove_reminder_job(job_id):
    """Removes a scheduled job by its ID."""
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Job '{job_id}' removed successfully from scheduler.")
        return True
    except JobLookupError:
        logger.warning(f"Job '{job_id}' not found in scheduler.")
        return False
    except Exception as e:
        logger.error(f"Error removing job '{job_id}': {e}")
        return False

def repopulate_scheduled_jobs(updater):
    """Repopulates the scheduler with reminders from user_data on bot start."""
    for user_id_str, data in user_data.items():
        chat_id = int(user_id_str) # Convert back to int for chat_id
        for reminder in data.get("reminders", []):
            schedule_reminder_job(updater, chat_id, reminder["time"], reminder["message"])
    logger.info("Scheduled jobs repopulated from data file.")

# --- Command Handlers ---

def start(update: Update, context: CallbackContext) -> None:
    """Sends a welcome message when the command /start is issued."""
    user_name = update.message.from_user.first_name
    update.message.reply_text(
        f"Hi {user_name}! I'm your dog care bot. "
        "I can help you track your dog's weight and send daily reminders.\n\n"
        "Here are the commands you can use:\n"
        "/addweight - Add a new weight entry\n"
        "/viewweights - View all recorded weights\n"
        "/addreminder - Set a new daily reminder\n"
        "/listreminders - See your current reminders\n"
        "/deletereminder <index> - Delete a specific reminder (e.g., /deletereminder 1)\n"
        "/cancel - Cancel the current operation"
    )

# --- Weight Tracking Conversation Handlers ---

def add_weight_start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation for adding dog weight."""
    update.message.reply_text(
        "Please enter your dog's weight (e.g., 15.2 kg or 33.5 lbs):"
    )
    return GET_WEIGHT

def add_weight_get_weight(update: Update, context: CallbackContext) -> int:
    """Receives the weight input and asks for the date."""
    weight_str = update.message.text
    try:
        weight = float(weight_str.split()[0]) # Try to parse the number
        context.user_data['temp_weight'] = weight
        update.message.reply_text(
            "Got it! Now, please enter the date for this weight (YYYY-MM-DD). "
            "Enter 'today' for today's date."
        )
        return GET_WEIGHT_DATE
    except ValueError:
        update.message.reply_text(
            "That doesn't look like a valid weight. Please enter a number (e.g., 15.2):"
        )
        return GET_WEIGHT

def add_weight_get_date(update: Update, context: CallbackContext) -> int:
    """Receives the date input and saves the weight entry."""
    date_str = update.message.text.lower()
    if date_str == 'today':
        date = datetime.now().strftime('%Y-%m-%d')
    else:
        try:
            # Validate date format
            datetime.strptime(date_str, '%Y-%m-%d')
            date = date_str
        except ValueError:
            update.message.reply_text(
                "Invalid date format. Please use YYYY-MM-DD or 'today'. Try again:"
            )
            return GET_WEIGHT_DATE

    user_id = update.message.from_user.id
    user_data_entry = get_user_data(user_id)
    weight = context.user_data.get('temp_weight')

    if weight is not None:
        user_data_entry["weights"].append({"date": date, "weight": weight})
        save_data()
        update.message.reply_text(
            f"Successfully recorded your dog's weight: {weight} on {date}."
        )
    else:
        update.message.reply_text(
            "Something went wrong. Please start again with /addweight."
        )

    # Clear temporary data and end conversation
    context.user_data.pop('temp_weight', None)
    return ConversationHandler.END

def view_weights(update: Update, context: CallbackContext) -> None:
    """Displays all recorded weights for the user."""
    user_id = update.message.from_user.id
    user_data_entry = get_user_data(user_id)
    weights = user_data_entry.get("weights", [])

    if not weights:
        update.message.reply_text("You haven't recorded any weights yet. Use /addweight to add one!")
        return

    response_text = "🐾 Your Dog's Weight History:\n"
    # Sort weights by date for better readability
    sorted_weights = sorted(weights, key=lambda x: x['date'])
    for entry in sorted_weights:
        response_text += f"- Date: {entry['date']}, Weight: {entry['weight']} kg/lbs\n" # Assuming unit based on user input for now

    update.message.reply_text(response_text)

# --- Reminder Setting Conversation Handlers ---

def add_reminder_start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation for adding a daily reminder."""
    update.message.reply_text(
        "What time should I send the reminder daily? (e.g., 08:30 for 8:30 AM, 14:00 for 2 PM)"
    )
    return GET_REMINDER_TIME

def add_reminder_get_time(update: Update, context: CallbackContext) -> int:
    """Receives the reminder time and asks for the message."""
    time_str = update.message.text
    try:
        # Validate time format (HH:MM)
        datetime.strptime(time_str, '%H:%M')
        context.user_data['temp_reminder_time'] = time_str
        update.message.reply_text("Great! Now, what's the reminder message? (e.g., 'Feed the dog', 'Give medication')")
        return GET_REMINDER_MESSAGE
    except ValueError:
        update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 09:00, 15:30). Try again:"
        )
        return GET_REMINDER_TIME

def add_reminder_get_message(update: Update, context: CallbackContext) -> int:
    """Receives the reminder message, saves and schedules the reminder."""
    reminder_message = update.message.text
    reminder_time = context.user_data.get('temp_reminder_time')

    if reminder_time and reminder_message:
        user_id = update.message.from_user.id
        user_data_entry = get_user_data(user_id)

        # Store the reminder
        user_data_entry["reminders"].append({
            "time": reminder_time,
            "message": reminder_message
        })
        save_data()

        # Schedule the job
        if schedule_reminder_job(context.dispatcher.updater, user_id, reminder_time, reminder_message):
            update.message.reply_text(
                f"Daily reminder set for {reminder_time} with message: '{reminder_message}' 🔔"
            )
        else:
            update.message.reply_text(
                "Failed to schedule reminder. Please check the time format."
            )
    else:
        update.message.reply_text(
            "Something went wrong. Please start again with /addreminder."
        )

    # Clear temporary data and end conversation
    context.user_data.pop('temp_reminder_time', None)
    return ConversationHandler.END

def list_reminders(update: Update, context: CallbackContext) -> None:
    """Lists all active reminders for the user."""
    user_id = update.message.from_user.id
    user_data_entry = get_user_data(user_id)
    reminders = user_data_entry.get("reminders", [])

    if not reminders:
        update.message.reply_text("You have no active reminders. Use /addreminder to set one!")
        return

    response_text = "⏰ Your Active Reminders:\n"
    for i, reminder in enumerate(reminders):
        response_text += f"{i + 1}. At {reminder['time']}: {reminder['message']}\n"
    response_text += "\nTo delete a reminder, use /deletereminder <number> (e.g., /deletereminder 1)"
    update.message.reply_text(response_text)

def delete_reminder(update: Update, context: CallbackContext) -> None:
    """Deletes a specific reminder by its index."""
    user_id = update.message.from_user.id
    user_data_entry = get_user_data(user_id)
    reminders = user_data_entry.get("reminders", [])

    if not context.args:
        update.message.reply_text("Please specify the reminder number to delete. E.g., /deletereminder 1")
        return

    try:
        index_to_delete = int(context.args[0]) - 1 # Convert to 0-based index
        if not (0 <= index_to_delete < len(reminders)):
            update.message.reply_text("Invalid reminder number. Please use a number from the /listreminders command.")
            return

        deleted_reminder = reminders.pop(index_to_delete)
        save_data()

        # Remove the job from the APScheduler
        job_id = f"reminder_{user_id}_{deleted_reminder['time']}_{deleted_reminder['message'].replace(' ', '_')}"
        remove_reminder_job(job_id)

        update.message.reply_text(
            f"Reminder '{deleted_reminder['message']}' at {deleted_reminder['time']} deleted successfully!"
        )
    except ValueError:
        update.message.reply_text("Invalid input. Please provide a number (e.g., /deletereminder 1).")
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        update.message.reply_text("An error occurred while trying to delete the reminder.")


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the current conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Operation canceled. You can start a new command anytime.'
    )
    # Clear any temporary user data from the context
    context.user_data.clear()
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log the errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main() -> None:
    """Start the bot."""
    # Load existing data first
    load_data()

    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler for adding weight
    add_weight_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addweight', add_weight_start)],
        states={
            GET_WEIGHT: [MessageHandler(Filters.text & ~Filters.command, add_weight_get_weight)],
            GET_WEIGHT_DATE: [MessageHandler(Filters.text & ~Filters.command, add_weight_get_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(add_weight_conv_handler)

    # Add conversation handler for adding reminder
    add_reminder_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addreminder', add_reminder_start)],
        states={
            GET_REMINDER_TIME: [MessageHandler(Filters.text & ~Filters.command, add_reminder_get_time)],
            GET_REMINDER_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, add_reminder_get_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(add_reminder_conv_handler)

    # On different commands, add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("viewweights", view_weights))
    dispatcher.add_handler(CommandHandler("listreminders", list_reminders))
    dispatcher.add_handler(CommandHandler("deletereminder", delete_reminder))
    dispatcher.add_handler(CommandHandler("cancel", cancel))


    # Log all errors
    dispatcher.add_error_handler(error_handler)

    # Start the Scheduler
    scheduler.start()
    # Repopulate jobs after scheduler starts
    repopulate_scheduled_jobs(updater)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    
    # Save data before exiting
    save_data()

if __name__ == '__main__':
    main()
