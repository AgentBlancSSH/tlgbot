import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import matplotlib.pyplot as plt

# Remplacez par votre jeton de bot Telegram
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Liste des administrateurs (IDs Telegram)
ADMIN_IDS = [123456789]  # Remplacez par les IDs des administrateurs

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Création des tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price REAL,
                        stock INTEGER,
                        category_id INTEGER,
                        FOREIGN KEY (category_id) REFERENCES categories (id)
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        status TEXT,
                        order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT,
                        user_id INTEGER,
                        chat_id INTEGER,
                        points INTEGER DEFAULT 0
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
                        user_id INTEGER,
                        rating INTEGER,
                        comment TEXT,
                        FOREIGN KEY (product_id) REFERENCES products (id)
                      )''')

    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def notify_admins(context: CallbackContext, message: str):
    for admin_id in ADMIN_IDS:
        context.bot.send_message(chat_id=admin_id, text=message)

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("👤 Utilisateur", callback_data='user')],
        [InlineKeyboardButton("🛍 Boutique", callback_data='shop')],
        [InlineKeyboardButton("📜 Historique", callback_data='history')],
        [InlineKeyboardButton("🏆 Mes Points", callback_data='points')],
        [InlineKeyboardButton("📊 Rapports (Admin)", callback_data='reports') if is_admin(update.message.from_user.id) else None]
    ]
    reply_markup = InlineKeyboardMarkup([k for k in keyboard if k])
    update.message.reply_text('Bienvenue! Que voulez-vous faire?', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'user':
        handle_user(query, context)
    elif query.data == 'shop':
        handle_shop(query, context)
    elif query.data == 'history':
        handle_history(query, context)
    elif query.data == 'points':
        show_points(query, context)
    elif query.data == 'reports':
        generate_reports(query, context)
    elif query.data.startswith('category_'):
        show_products(query, context, query.data.split('_')[1])
    elif query.data == 'past_orders':
        show_past_orders(query, context)
    elif query.data == 'current_orders':
        show_current_orders(query, context)

def handle_user(query, context):
    user_info = f"Nom d'utilisateur: {query.from_user.username}\nID utilisateur: {query.from_user.id}\nChat ID: {query.message.chat_id}"
    keyboard = [[InlineKeyboardButton("⬅ Retour", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=user_info, reply_markup=reply_markup)

def handle_shop(query, context):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()

    keyboard = [[InlineKeyboardButton(category[1], callback_data=f'category_{category[0]}')] for category in categories]
    keyboard.append([InlineKeyboardButton("⬅ Retour", callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text="Choisissez une catégorie:", reply_markup=reply_markup)

def handle_history(query, context):
    keyboard = [
        [InlineKeyboardButton("📦 Commandes Passées", callback_data='past_orders')],
        [InlineKeyboardButton("⏳ Commandes en Cours", callback_data='current_orders')],
        [InlineKeyboardButton("⬅ Retour", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Sélectionnez l'historique:", reply_markup=reply_markup)

def show_products(query, context, category_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE category_id = ?', (category_id,))
    products = cursor.fetchall()
    conn.close()

    if products:
        text = "Produits disponibles:\n\n"
        for product in products:
            text += f"{product[1]} - {product[2]}\nPrix: {product[3]} EUR\nStock: {product[4]} unités\n\n"
    else:
        text = "Aucun produit disponible dans cette catégorie."

    keyboard = [[InlineKeyboardButton("⬅ Retour", callback_data='shop')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def show_past_orders(query, context):
    orders = get_past_orders()
    if orders:
        text = "Commandes passées:\n\n"
        for order in orders:
            text += f"Commande #{order[0]} - Produit ID: {order[2]} - Quantité: {order[3]} - Date: {order[5]}\n\n"
    else:
        text = "Aucune commande passée."

    keyboard = [[InlineKeyboardButton("⬅ Retour", callback_data='history')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def show_current_orders(query, context):
    orders = get_current_orders()
    if orders:
        text = "Commandes en cours:\n\n"
        for order in orders:
            text += f"Commande #{order[0]} - Produit ID: {order[2]} - Quantité: {order[3]} - Statut: {order[4]}\n\n"
    else:
        text = "Aucune commande en cours."

    keyboard = [[InlineKeyboardButton("⬅ Retour", callback_data='history')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def show_points(query, context):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (query.from_user.id,))
    points = cursor.fetchone()[0]
    conn.close()

    text = f"Vous avez accumulé {points} points de fidélité!"
    keyboard = [[InlineKeyboardButton("⬅ Retour", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def generate_reports(query, context):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Exemple simple de rapport : nombre de ventes par produit
    cursor.execute('''SELECT p.name, COUNT(o.id) as num_sales
                      FROM orders o
                      JOIN products p ON o.product_id = p.id
                      WHERE o.status = "delivered"
                      GROUP BY o.product_id''')
    report_data = cursor.fetchall()

    if report_data:
        products = [row[0] for row in report_data]
        sales = [row[1] for row in report_data]

        # Générer un graphique
        plt.figure(figsize=(10, 5))
        plt.bar(products, sales, color='blue')
        plt.xlabel('Produits')
        plt.ylabel('Nombre de ventes')
        plt.title('Rapport de Ventes par Produit')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('sales_report.png')

        # Envoyer le graphique
        context.bot.send_photo(chat_id=query.message.chat_id, photo=open('sales_report.png', 'rb'))

    else:
        context.bot.send_message(chat_id=query.message.chat_id, text="Aucun rapport disponible.")

    conn.close()

def add_product(name, description, price, stock, category_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, description, price, stock, category_id) VALUES (?, ?, ?, ?, ?)',
                   (name, description, price, stock, category_id))
    conn.commit()
    conn.close()

def modify_product(product_id, name, description, price, stock, category_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET name = ?, description = ?, price = ?, stock = ?, category_id = ? WHERE id = ?',
                   (name, description, price, stock, category_id, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def add_category(name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

def modify_category(category_id, name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
    conn.commit()
    conn.close()

def delete_category(category_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()

def mark_order_as_delivered(order_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = "delivered" WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()

    # Notifier les administrateurs
    notify_admins(context=None, message=f"Commande #{order_id} marquée comme livrée.")

def get_current_orders():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE status = "pending"')
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_past_orders():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE status = "delivered"')
    orders = cursor.fetchall()
    conn.close()
    return orders

def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
