eeezrzrimport os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Le token du bot Telegram n'est pas configuré.")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Stocker les données utilisateurs et commandes
users = {}
orders = {}

# Admins list
ADMINS = [123456789]  # Remplacez par les IDs Telegram des administrateurs

# Produits disponibles (initialement)
PRODUCTS = {
    '2.5g/L': 20.0,
    '3g/L': 25.0,
    '5g/L': 35.0
}

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    users[user_id] = {'panier': [], 'profil': {}, 'historique': []}
    
    keyboard = [
        [InlineKeyboardButton("Profil", callback_data='profil')],
        [InlineKeyboardButton("Boutique", callback_data='boutique')],
        [InlineKeyboardButton("Historique de Commande", callback_data='historique')]
    ]
    if user_id in ADMINS:
        keyboard.append([InlineKeyboardButton("Panneau Admin", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Bienvenue chez PTC France, veuillez choisir une option de navigation :", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    query.answer()

    if query.data == 'profil':
        handle_profil(query, user_id)
    elif query.data == 'boutique':
        show_boutique(query, user_id)
    elif query.data == 'historique':
        show_historique(query, user_id)
    elif query.data.startswith('add_to_cart'):
        _, product = query.data.split(':')
        add_to_cart(query, user_id, product)
    elif query.data == 'panier':
        handle_panier(query, user_id)
    elif query.data == 'valider_commande':
        ask_for_profil_info(query, user_id)
    elif query.data == 'annuler_commande':
        annuler_commande(query, user_id)
    elif query.data == 'admin_panel':
        admin_panel(query)
    elif query.data.startswith('update_status'):
        _, user, order_idx, status = query.data.split(':')
        update_order_status(query, int(user), int(order_idx), status)

def handle_profil(query, user_id):
    profil_info = users[user_id]['profil']
    if not profil_info:
        query.edit_message_text("Votre profil est vide. Veuillez le compléter.")
        ask_for_name(query, user_id)
    else:
        query.edit_message_text(f"Votre profil :\nNom: {profil_info.get('nom', 'N/A')}\nAdresse: {profil_info.get('adresse', 'N/A')}\nEmail: {profil_info.get('email', 'N/A')}\nTéléphone: {profil_info.get('telephone', 'N/A')}")

def ask_for_name(query, user_id):
    query.message.reply_text("Veuillez entrer votre nom et prénom :")
    context.bot.add_handler(MessageHandler(Filters.text & ~Filters.command, collect_name))

def collect_name(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    users[user_id]['profil']['nom'] = update.message.text
    ask_for_address(update)

def ask_for_address(update: Update):
    update.message.reply_text("Veuillez entrer votre adresse :")
    context.bot.add_handler(MessageHandler(Filters.text & ~Filters.command, collect_address))

def collect_address(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    users[user_id]['profil']['adresse'] = update.message.text
    ask_for_email(update)

def ask_for_email(update: Update):
    update.message.reply_text("Veuillez entrer votre email :")
    context.bot.add_handler(MessageHandler(Filters.text & ~Filters.command, collect_email))

def collect_email(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    email = update.message.text
    if is_valid_email(email):
        users[user_id]['profil']['email'] = email
        ask_for_phone(update)
    else:
        update.message.reply_text("Email invalide, veuillez réessayer.")
        ask_for_email(update)

def ask_for_phone(update: Update):
    update.message.reply_text("Veuillez entrer votre numéro de téléphone :")
    context.bot.add_handler(MessageHandler(Filters.text & ~Filters.command, collect_phone))

def collect_phone(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    users[user_id]['profil']['telephone'] = update.message.text
    update.message.reply_text("Profil complété. Vous pouvez maintenant finaliser votre commande.")

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def show_boutique(query, user_id):
    keyboard = [
        [InlineKeyboardButton(f"2.5g/L - {PRODUCTS['2.5g/L']}€", callback_data='add_to_cart:2.5g/L')],
        [InlineKeyboardButton(f"3g/L - {PRODUCTS['3g/L']}€", callback_data='add_to_cart:3g/L')],
        [InlineKeyboardButton(f"5g/L - {PRODUCTS['5g/L']}€", callback_data='add_to_cart:5g/L')],
        [InlineKeyboardButton("Voir Panier", callback_data='panier')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("Bienvenue dans la boutique de PTC FRANCE, veuillez choisir un dosage :", reply_markup=reply_markup)

def add_to_cart(query, user_id, product):
    users[user_id]['panier'].append(product)
    query.edit_message_text(f"Produit ajouté au panier : {product}\n\nPanier actuel : {', '.join(users[user_id]['panier'])}")
    show_boutique(query, user_id)

def handle_panier(query, user_id):
    panier = users[user_id]['panier']
    if not panier:
        query.edit_message_text("Votre panier est vide.")
    else:
        recap = '\n'.join(f"{item} - {PRODUCTS[item]}€" for item in panier)
        total = sum(PRODUCTS[item] for item in panier)
        keyboard = [
            [InlineKeyboardButton("Valider la commande", callback_data='valider_commande')],
            [InlineKeyboardButton("Annuler la commande", callback_data='annuler_commande')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(f"Récapitulatif de commande :\n{recap}\n\nTotal : {total}€", reply_markup=reply_markup)

def ask_for_profil_info(query, user_id):
    profil_info = users[user_id]['profil']
    if not profil_info:
        ask_for_name(query, user_id)
    else:
        validate_order(query, user_id)

def validate_order(query, user_id):
    orders.setdefault(user_id, []).append(users[user_id]['panier'])
    query.message.reply_text("Votre commande a bien été validée et transmise à nos administrateurs.")
    notify_admins(user_id)
    users[user_id]['historique'].append({'panier': users[user_id]['panier'], 'statut': 'Commande validée'})
    users[user_id]['panier'] = []

def annuler_commande(query, user_id):
    users[user_id]['panier'] = []
    query.edit_message_text("Votre commande a été annulée.")

def show_historique(query, user_id):
    historique = users[user_id]['historique']
    if not historique:
        query.edit_message_text("Aucune commande passée.")
    else:
        commandes = '\n'.join(f"Commande {i+1}: {cmd['panier']} - Statut: {cmd['statut']}" for i, cmd in enumerate(historique))
        query.edit_message_text(f"Votre historique de commandes :\n{commandes}")

def notify_admins(user_id):
    for admin_id in ADMINS:
        context.bot.send_message(chat_id=admin_id, text=f"Nouvelle commande de l'utilisateur {user_id} : {users[user_id]['panier']}")

def admin_panel(query):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        query.edit_message_text("Accès refusé.")
        return

    admin_menu = [
        [InlineKeyboardButton("Voir les commandes", callback_data='admin_orders')],
        [InlineKeyboardButton("Modifier les prix des produits", callback_data='admin_edit_prices')]
    ]
    reply_markup = InlineKeyboardMarkup(admin_menu)
    query.edit_message_text("Panneau d'administration :", reply_markup=reply_markup)

def update_order_status(query, user_id, order_idx, status):
    orders[user_id][order_idx]['statut'] = status
    query.edit_message_text(f"Statut de la commande mis à jour pour l'utilisateur {user_id}.")
    context.bot.send_message(chat_id=user_id, text=f"Votre commande {order_idx+1} est maintenant : {status}")

def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
