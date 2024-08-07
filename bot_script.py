import os
import telebot
from telebot import apihelper
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN_E")

# Initialize the bot with the token
bot = telebot.TeleBot(API_TOKEN)

# Define a simple start command handler
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I'm your friendly Telegram bot. How can I assist you today?")

# A command to handle unknown messages or commands
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

# Start the bot and handle errors
try:
    bot.infinity_polling()
except apihelper.ApiTelegramException as e:
    print(f"An error occurred with the Telegram API: {e}")
except KeyboardInterrupt:
    print("Bot stopped manually.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
