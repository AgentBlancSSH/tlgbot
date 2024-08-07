import os
import json
import telebot
from telebot import types

# Charger le token Telegram depuis le fichier .env
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN_E")

bot = telebot.TeleBot(API_TOKEN)

user_dict = {}

class User:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        with open("data_file.json", "r") as f:
            self.json_data = json.load(f)
        self.divisions_list = list(self.json_data["מחלקות"])
        self.current_divisions_list = {}

# Fonction d'accueil du bot
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    welcome_message = (
        "שלום!, אני רובוט רשימת הקניות שלך.\n"
        "בכל עת תוכל לשלוח לי את רשימת הקניות שלך (כל מוצר בשורה חדשה) ואני אסדר לפי מחלקות :)\n"
        "שליחת start/ תאפשר מיון של רשימה חדשה\n"
        "שליחת add/ תאפשר הוספת מוצרים חדשים למחלקה קיימת\n\n"
        "במידה וחסרה מחלקה אנא פנה ליוצר שלי"
    )
    msg = bot.reply_to(message, welcome_message)
    bot.register_next_step_handler(msg, process_shopping_list)

def process_shopping_list(message):
    chat_id = message.chat.id
    shopping_list = message.text.splitlines()
    shopping_list = strip_start_and_end(shopping_list)
    
    user = User(chat_id)
    user_dict[chat_id] = user
    
    at_least_1_item_found = False
    
    for item in shopping_list:
        found, div = find_item(user.json_data, item)
        if found:
            user.current_divisions_list.setdefault(div, []).append(item)
            at_least_1_item_found = True
        else:
            bot.send_message(chat_id, f"הפריט {item} איננו מוכר לי.")
    
    if at_least_1_item_found:
        bot.send_message(chat_id, pretty_output(user))
    else:
        bot.send_message(chat_id, "נסה שוב מההתחלה")

def strip_start_and_end(shopping_list):
    return [item.strip() for item in shopping_list]

def pretty_output(user):
    ordered_output = ""
    for div, items in user.current_divisions_list.items():
        ordered_output += f"* {div} *\n" + "\n".join(items) + "\n\n"
    return ordered_output

def find_item(json_data, item):
    for div, products in json_data["מחלקות"].items():
        if item in products:
            return True, div
    return False, None

# Gestion de la commande '/add'
@bot.message_handler(commands=["add"])
def send_add_welcome(message):
    chat_id = message.chat.id
    user = User(chat_id)
    instructions = (
        ":אנא הכנס בשורה הראשונה את שם המחלקה המתאימה שברצונך להוסיף אליה מוצרים\n"
        "ובשורות הבאות פריט בשורה ולאחריו מחיר הפריט לדוגמה:\n"
        "מוצרי חלב וביצים\n"
        "חלב\n"
        "7\n"
        "חמאה\n"
        "5\n"
        "לבדיקת שייכות מוצר למחלקה: https://www.shukcity.co.il/categories?level1=79653"
    )
    msg = bot.reply_to(message, instructions)
    bot.register_next_step_handler(msg, process_add)

def process_add(message):
    chat_id = message.chat.id
    user = User(chat_id)
    lines = strip_start_and_end(message.text.splitlines())
    
    div = lines[0]
    if div not in user.json_data["מחלקות"]:
        bot.send_message(chat_id, "נראה שהמחלקה שהזנת לא מתאימה למחלקות הקיימות.")
        return
    
    for i in range(1, len(lines), 2):
        item = lines[i]
        price = lines[i + 1] if i + 1 < len(lines) else "לא צוין מחיר"
        
        found, _ = find_item(user.json_data, item)
        if found:
            bot.send_message(chat_id, f"הפריט {item} כבר מופיע במחלקה {div}")
        else:
            user.json_data["מחלקות"][div].append(item)
            with open("data_file.json", "w") as f:
                json.dump(user.json_data, f)
            bot.send_message(chat_id, f"הפריט {item} התווסף בהצלחה למחלקת {div}. תודה")

# Démarrer le bot
bot.infinity_polling()
