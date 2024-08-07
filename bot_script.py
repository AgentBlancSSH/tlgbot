import os
import telebot
from telebot import types
from dotenv import load_dotenv
import sqlite3

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN_E")

# Initialize the bot and database connection
bot = telebot.TeleBot(API_TOKEN)
conn = sqlite3.connect('ptcfrance.db', check_same_thread=False)
cursor = conn.cursor()

# Initialize database schema
def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        last_name TEXT,
                        address TEXT,
                        postal_code TEXT,
                        email TEXT,
                        phone TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        dosage REAL,
                        price REAL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS order_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER,
                        status TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()

init_db()

# Helper functions to handle database interactions
def get_user_profile(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def update_user_profile(user_id, first_name, last_name, address, postal_code, email, phone):
    cursor.execute('''REPLACE INTO users (user_id, first_name, last_name, address, postal_code, email, phone)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', (user_id, first_name, last_name, address, postal_code, email, phone))
    conn.commit()

def add_product_to_cart(user_id, product_id, quantity):
    cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))
    conn.commit()

def get_cart(user_id):
    cursor.execute('''SELECT products.name, products.dosage, products.price, cart.quantity
                      FROM cart 
                      JOIN products ON cart.product_id = products.id
                      WHERE cart.user_id=?''', (user_id,))
    return cursor.fetchall()

def clear_cart(user_id):
    cursor.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    conn.commit()

def create_order(user_id):
    cursor.execute("INSERT INTO orders (user_id, status) VALUES (?, ?)", (user_id, "Pending"))
    order_id = cursor.lastrowid
    conn.commit()
    return order_id

def add_order_status(order_id, status):
    cursor.execute("INSERT INTO order_status (order_id, status) VALUES (?, ?)", (order_id, status))
    conn.commit()

def get_order_history(user_id):
    cursor.execute('''SELECT orders.id, orders.status, orders.created_at, group_concat(products.name || ' (' || cart.quantity || ' x ' || products.dosage || 'g/L)', ', ')
                      FROM orders
                      JOIN cart ON orders.user_id = cart.user_id
                      JOIN products ON cart.product_id = products.id
                      WHERE orders.user_id = ?
                      GROUP BY orders.id''', (user_id,))
    return cursor.fetchall()

# Start command handler
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn1 = types.KeyboardButton('Profil')
    btn2 = types.KeyboardButton('Boutique')
    btn3 = types.KeyboardButton('Historique de commande')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "Bienvenue chez PTC France. Veuillez choisir une option de navigation.", reply_markup=markup)

# Profile command handler
@bot.message_handler(func=lambda message: message.text == "Profil")
def show_profile(message):
    user_profile = get_user_profile(message.from_user.id)
    if user_profile:
        bot.send_message(message.chat.id, f"Informations du compte:\nNom: {user_profile[1]} {user_profile[2]}\nAdresse: {user_profile[3]}\nCode Postal: {user_profile[4]}\nEmail: {user_profile[5]}\nTéléphone: {user_profile[6]}")
    else:
        msg = bot.reply_to(message, "Vous n'avez pas encore configuré votre profil. Entrez votre prénom:")
        bot.register_next_step_handler(msg, process_first_name)

def process_first_name(message):
    first_name = message.text
    msg = bot.reply_to(message, "Entrez votre nom de famille:")
    bot.register_next_step_handler(msg, process_last_name, first_name)

def process_last_name(message, first_name):
    last_name = message.text
    msg = bot.reply_to(message, "Entrez votre adresse:")
    bot.register_next_step_handler(msg, process_address, first_name, last_name)

def process_address(message, first_name, last_name):
    address = message.text
    msg = bot.reply_to(message, "Entrez votre code postal:")
    bot.register_next_step_handler(msg, process_postal_code, first_name, last_name, address)

def process_postal_code(message, first_name, last_name, address):
    postal_code = message.text
    msg = bot.reply_to(message, "Entrez votre email:")
    bot.register_next_step_handler(msg, process_email, first_name, last_name, address, postal_code)

def process_email(message, first_name, last_name, address, postal_code):
    email = message.text
    msg = bot.reply_to(message, "Entrez votre numéro de téléphone:")
    bot.register_next_step_handler(msg, process_phone, first_name, last_name, address, postal_code, email)

def process_phone(message, first_name, last_name, address, postal_code, email):
    phone = message.text
    update_user_profile(message.from_user.id, first_name, last_name, address, postal_code, email, phone)
    bot.send_message(message.chat.id, "Votre profil a été mis à jour.")

# Boutique command handler
@bot.message_handler(func=lambda message: message.text == "Boutique")
def show_shop(message):
    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    for product in products:
        markup.add(types.InlineKeyboardButton(f"{product[1]} - {product[2]}g/L (Prix: {product[3]}€)", callback_data=f"product_{product[0]}"))
    bot.send_message(message.chat.id, "Bienvenue dans la boutique de PTC France. Veuillez choisir un produit.", reply_markup=markup)

# Handle adding products to the cart
@bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
def handle_product_selection(call):
    product_id = int(call.data.split("_")[1])
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton("2.5g/L", callback_data=f"add_to_cart_{product_id}_2.5")
    btn2 = types.InlineKeyboardButton("3g/L", callback_data=f"add_to_cart_{product_id}_3")
    btn3 = types.InlineKeyboardButton("5g/L", callback_data=f"add_to_cart_{product_id}_5")
    markup.add(btn1, btn2, btn3)
    bot.send_message(call.message.chat.id, "Veuillez choisir un dosage pour ce produit.", reply_markup=markup)

# Handle adding the selected product and dosage to the cart
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_cart_"))
def add_to_cart(call):
    parts = call.data.split("_")
    product_id = int(parts[2])
    dosage = float(parts[3])
    add_product_to_cart(call.from_user.id, product_id, 1)  # Add to cart with quantity 1 for simplicity
    bot.send_message(call.message.chat.id, f"Produit ajouté au panier avec dosage {dosage}g/L.")

# Command handler for viewing the cart
@bot.message_handler(func=lambda message: message.text == "Panier")
def view_cart(message):
    cart_items = get_cart(message.from_user.id)
    if cart_items:
        cart_details = "Voici votre panier:\n"
        for item in cart_items:
            cart_details += f"- {item[0]} ({item[1]}g/L): {item[3]} x {item[2]}€\n"
        cart_details += "\nFinaliser la commande ?"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Valider", callback_data="validate_order"))
        markup.add(types.InlineKeyboardButton("Annuler", callback_data="cancel_order"))
        bot.send_message(message.chat.id, cart_details, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Votre panier est vide.")

# Handle order validation
@bot.callback_query_handler(func=lambda call: call.data == "validate_order")
def validate_order(call):
    order_id = create_order(call.from_user.id)
    add_order_status(order_id, "Commande validée")
    bot.send_message(call.message.chat.id, "Commande validée. Veuillez entrer vos informations pour finaliser la commande (nom, adresse, etc.).")
    clear_cart(call.from_user.id)

# Handle order cancellation
@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def cancel_order(call):
    clear_cart(call.from_user.id)
    bot.send_message(call.message.chat.id, "Commande annulée. Vous êtes retourné à l'accueil.")

# Historique de commande (Order History) command handler
@bot.message_handler(func=lambda message: message.text == "Historique de commande")
def order_history(message):
    order_items = get_order_history(message.from_user.id)
    if order_items:
        history_details = "Historique de commande:\n"
        for order in order_items:
            history_details += f"Commande #{order[0]} - Status: {order[1]}\nDate: {order[2]}\nProduits: {order[3]}\n\n"
        bot.send_message(message.chat.id, history_details)
    else:
        bot.send_message(message.chat.id, "Vous n'avez pas encore passé de commande.")

# Admin interface (this would normally be restricted)
@bot.message_handler(commands=['admin'])
def admin_interface(message):
    if message.chat.id == YOUR_ADMIN_TELEGRAM_ID:  # Replace with actual admin Telegram ID
        cursor.execute("SELECT * FROM orders WHERE status != 'Expédié'")
        orders = cursor.fetchall()
        if orders:
            for order in orders:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Prendre en charge", callback_data=f"update_order_{order[0]}_Processing"))
                markup.add(types.InlineKeyboardButton("Colis en préparation", callback_data=f"update_order_{order[0]}_Preparation"))
                markup.add(types.InlineKeyboardButton("Colis expédié", callback_data=f"update_order_{order[0]}_Shipped"))
                bot.send_message(message.chat.id, f"Commande #{order[0]} - Status: {order[2]}", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Aucune commande en attente.")
    else:
        bot.send_message(message.chat.id, "Vous n'avez pas accès à cette commande.")

# Handle admin order status updates
@bot.callback_query_handler(func=lambda call: call.data.startswith("update_order_"))
def update_order_status(call):
    parts = call.data.split("_")
    order_id = int(parts[2])
    new_status = parts[3]
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    add_order_status(order_id, new_status)
    bot.send_message(call.message.chat.id, f"Commande #{order_id} mise à jour: {new_status}")
    conn.commit()

# Start the bot
try:
    print("Bot is starting...")
    bot.infinity_polling()
except KeyboardInterrupt:
    print("Bot stopped manually.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
