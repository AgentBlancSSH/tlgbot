import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Stocker les données utilisateurs et commandes
users = {}
orders = {}
order_counter = 1

# Admins list (les IDs des admins seront ajoutés via une commande)
ADMINS = []

# Produits disponibles (initialement)
PRODUCTS = {
    '2.5g/L': 20.0,
    '3g/L': 25.0,
    '5g/L': 35.0
}

# Variables de configuration à être définies par l'administrateur
TOKEN = None
CHANNEL_ID = None

# Initialiser le logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Aucun nom d'utilisateur"
    if user_id not in users:
        users[user_id] = {'panier': [], 'profil': {'username': username}, 'historique': []}
    
    welcome_text = f"👋 Bienvenue {username} !\n\n" \
                   "Utilisez /shop pour voir nos produits.\n" \
                   "Utilisez /cart pour voir votre panier.\n" \
                   "Utilisez /checkout pour finaliser votre commande."
    update.message.reply_text(welcome_text)

def request_config(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        update.message.reply_text("❌ Vous n'avez pas les droits pour configurer le bot.")
        return
    
    update.message.reply_text("Veuillez entrer le TOKEN du bot.")
    context.user_data['config_stage'] = 'TOKEN'

def handle_config(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        update.message.reply_text("❌ Vous n'avez pas les droits pour configurer le bot.")
        return

    stage = context.user_data.get('config_stage')
    
    if stage == 'TOKEN':
        global TOKEN
        TOKEN = update.message.text.strip()
        update.message.reply_text("TOKEN enregistré. Veuillez entrer l'ID du canal privé pour les alertes.")
        context.user_data['config_stage'] = 'CHANNEL_ID'
    
    elif stage == 'CHANNEL_ID':
        global CHANNEL_ID
        CHANNEL_ID = update.message.text.strip()
        update.message.reply_text("ID du canal enregistré. Configuration terminée.")
        context.user_data['config_stage'] = None

def show_user_info(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Aucun nom d'utilisateur"
    
    user_info = f"🆔 ID: {user_id}\n" \
                f"👤 Username: @{username}\n\n" \
                "💬 Ces informations sont uniquement utilisées pour les reçus de commande."
    update.message.reply_text(user_info)

def admin_panel(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    if user_id not in ADMINS:
        update.message.reply_text("❌ Vous n'avez pas accès à cette commande.")
        return
    
    buttons = [
        [InlineKeyboardButton("Ajouter un produit ➕", callback_data='add_product')],
        [InlineKeyboardButton("Modifier un produit ✏️", callback_data='edit_product')],
        [InlineKeyboardButton("Supprimer un produit 🗑️", callback_data='remove_product')],
        [InlineKeyboardButton("Voir les commandes en cours 📦", callback_data='view_orders')],
        [InlineKeyboardButton("Liste des utilisateurs 👥", callback_data='list_users')],
        [InlineKeyboardButton("Ajouter un administrateur ➕", callback_data='add_admin')],
        [InlineKeyboardButton("Supprimer un administrateur 🗑️", callback_data='remove_admin')],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text("🛠️ Panneau d'administration", reply_markup=reply_markup)

def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMINS:
        query.answer("❌ Vous n'avez pas accès à cette commande.")
        return
    
    if query.data == 'add_product':
        query.message.reply_text("Entrez le nom du produit et le prix séparés par une virgule (e.g., 3g/L,25.0)")
        context.user_data['admin_action'] = 'add_product'
    elif query.data == 'edit_product':
        query.message.reply_text("Entrez le nom du produit à modifier.")
        context.user_data['admin_action'] = 'edit_product'
    elif query.data == 'remove_product':
        query.message.reply_text("Entrez le nom du produit à supprimer.")
        context.user_data['admin_action'] = 'remove_product'
    elif query.data == 'view_orders':
        show_orders(update, context)
    elif query.data == 'list_users':
        list_users(update, context)
    elif query.data == 'add_admin':
        query.message.reply_text("Entrez l'ID de l'utilisateur à ajouter comme administrateur.")
        context.user_data['admin_action'] = 'add_admin'
    elif query.data == 'remove_admin':
        query.message.reply_text("Entrez l'ID de l'administrateur à supprimer.")
        context.user_data['admin_action'] = 'remove_admin'
    query.answer()

def handle_admin_response(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    if user_id not in ADMINS:
        update.message.reply_text("❌ Vous n'avez pas accès à cette commande.")
        return
    
    action = context.user_data.get('admin_action')
    if action == 'add_product':
        try:
            name, price = map(str.strip, update.message.text.split(','))
            PRODUCTS[name] = float(price)
            update.message.reply_text(f"Produit ajouté : {name} à {price} €")
        except ValueError:
            update.message.reply_text("❌ Format incorrect. Utilisez: nom, prix")
    elif action == 'edit_product':
        name = update.message.text.strip()
        if name in PRODUCTS:
            update.message.reply_text(f"Entrez le nouveau prix pour {name}.")
            context.user_data['product_to_edit'] = name
        else:
            update.message.reply_text("❌ Produit non trouvé.")
    elif action == 'remove_product':
        name = update.message.text.strip()
        if name in PRODUCTS:
            del PRODUCTS[name]
            update.message.reply_text(f"Produit supprimé : {name}")
        else:
            update.message.reply_text("❌ Produit non trouvé.")
    elif 'product_to_edit' in context.user_data:
        try:
            price = float(update.message.text.strip())
            name = context.user_data['product_to_edit']
            PRODUCTS[name] = price
            update.message.reply_text(f"Produit modifié : {name} à {price} €")
            del context.user_data['product_to_edit']
        except ValueError:
            update.message.reply_text("❌ Prix invalide.")
    
    elif action == 'add_admin':
        new_admin_id = int(update.message.text.strip())
        if new_admin_id not in ADMINS:
            ADMINS.append(new_admin_id)
            update.message.reply_text(f"L'utilisateur avec l'ID {new_admin_id} a été ajouté comme administrateur.")
        else:
            update.message.reply_text(f"L'utilisateur avec l'ID {new_admin_id} est déjà administrateur.")
    
    elif action == 'remove_admin':
        admin_id = int(update.message.text.strip())
        if admin_id in ADMINS:
            ADMINS.remove(admin_id)
            update.message.reply_text(f"L'administrateur avec l'ID {admin_id} a été supprimé.")
        else:
            update.message.reply_text(f"L'utilisateur avec l'ID {admin_id} n'est pas un administrateur.")
    
    # Reset action
    context.user_data['admin_action'] = None

def shop(update: Update, context: CallbackContext):
    products_text = "🛒 *Produits disponibles :*\n\n"
    for name, price in PRODUCTS.items():
        products_text += f"• {name} - {price} €\n"
    
    update.message.reply_text(products_text, parse_mode=ParseMode.MARKDOWN)

def cart(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_cart = users[user_id]['panier']
    
    if not user_cart:
        update.message.reply_text("🛒 Votre panier est vide.")
        return
    
    cart_text = "🛒 *Votre panier :*\n\n"
    total = 0
    for item in user_cart:
        cart_text += f"• {item['product']} - {item['price']} €\n"
        total += item['price']
    
    cart_text += f"\n💰 *Total :* {total} €"
    update.message.reply_text(cart_text, parse_mode=ParseMode.MARKDOWN)

def checkout(update: Update, context: CallbackContext):
    global order_counter
    user_id = update.message.from_user.id
    user_cart = users[user_id]['panier']
    
    if not user_cart:
        update.message.reply_text("🛒 Votre panier est vide.")
        return
    
    checkout_text = "🛒 *Détails de votre commande :*\n\n"
    total = 0
    for item in user_cart:
        checkout_text += f"• {item['product']} - {item['price']} €\n"
        total += item['price']
    
    checkout_text += f"\n💰 *Total :* {total} €\n\n" \
                     "📧 Nous vous contacterons pour confirmer votre commande."
    
    update.message.reply_text(checkout_text, parse_mode=ParseMode.MARKDOWN)
    
    # Sauvegarder la commande
    order_id = order_counter
    orders[order_id] = {
        'user_id': user_id,
        'cart': user_cart,
        'total': total,
        'status': 'En attente'
    }
    users[user_id]['historique'].append(order_id)
    order_counter += 1
    
    # Clear cart after checkout
    users[user_id]['panier'] = []
    
    # Alerter un canal privé
    send_order_alert(context, order_id)

def send_order_alert(context: CallbackContext, order_id):
    if CHANNEL_ID:
        order = orders[order_id]
        user_id = order['user_id']
        username = users[user_id]['profil'].get('username', "Utilisateur inconnu")
        alert_text = f"🔔 *Nouvelle commande* 🔔\n\n" \
                     f"🆔 ID Commande: {order_id}\n" \
                     f"👤 Client: @{username}\n" \
                     f"💰 Total: {order['total']} €\n" \
                     f"📦 Statut: {order['status']}\n\n" \
                     "Veuillez traiter cette commande."
        context.bot.send_message(chat_id=CHANNEL_ID, text=alert_text, parse_mode=ParseMode.MARKDOWN)

def update_order_status(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data.split(':')
    action = data[0]
    order_id = int(data[1])
    
    if user_id not in ADMINS:
        query.answer("❌ Vous n'avez pas accès à cette commande.")
        return
    
    if action == 'process':
        orders[order_id]['status'] = 'En traitement'
    elif action == 'ship':
        orders[order_id]['status'] = 'Expédiée'
    elif action == 'deliver':
        orders[order_id]['status'] = 'Livrée'
    
    # Mettre à jour le message avec le nouveau statut
    query.message.edit_text(format_order_details(order_id), reply_markup=get_order_buttons(order_id), parse_mode=ParseMode.MARKDOWN)
    query.answer("Statut mis à jour.")

def show_orders(update: Update, context: CallbackContext):
    if not orders:
        update.message.reply_text("📦 Aucune commande en cours.")
        return
    
    for order_id, order in orders.items():
        update.message.reply_text(format_order_details(order_id), reply_markup=get_order_buttons(order_id), parse_mode=ParseMode.MARKDOWN)

def format_order_details(order_id):
    order = orders[order_id]
    user_id = order['user_id']
    username = users[user_id]['profil'].get('username', "Utilisateur inconnu")
    
    return f"🆔 ID Commande: {order_id}\n" \
           f"👤 Client: @{username}\n" \
           f"💰 Total: {order['total']} €\n" \
           f"📦 Statut: {order['status']}\n"

def get_order_buttons(order_id):
    buttons = [
        [InlineKeyboardButton("En traitement 🛠️", callback_data=f'process:{order_id}')],
        [InlineKeyboardButton("Expédiée 🚚", callback_data=f'ship:{order_id}')],
        [InlineKeyboardButton("Livrée 📦", callback_data=f'deliver:{order_id}')],
    ]
    return InlineKeyboardMarkup(buttons)

def list_users(update: Update, context: CallbackContext):
    if not users:
        update.message.reply_text("👥 Aucun utilisateur enregistré.")
        return
    
    users_text = "👥 *Liste des utilisateurs :*\n\n"
    for user_id, user_data in users.items():
        users_text += f"• @{user_data['profil'].get('username', 'Aucun nom d\'utilisateur')} (ID: {user_id})\n"
    
    update.message.reply_text(users_text, parse_mode=ParseMode.MARKDOWN)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("userinfo", show_user_info))
    dp.add_handler(CommandHandler("admin", admin_panel))
    dp.add_handler(CommandHandler("shop", shop))
    dp.add_handler(CommandHandler("cart", cart))
    dp.add_handler(CommandHandler("checkout", checkout))
    dp.add_handler(CommandHandler("requestconfig", request_config))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_admin_response))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_config))
    dp.add_handler(CallbackQueryHandler(handle_callback_query))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
