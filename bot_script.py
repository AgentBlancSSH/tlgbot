import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
import string

# Configurer le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Données de base
PRODUCTS = {}
ORDERS = {}
CONVERSATIONS = {}
ADMINS = [123456789]  # Remplacez par l'ID Telegram des administrateurs
VENDORS = [987654321]  # Liste des IDs Telegram des vendeurs

# Générer un identifiant de commande unique
def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Fonction pour démarrer le bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if PRODUCTS:
        keyboard = [
            [InlineKeyboardButton(f"📦 {category}", callback_data=f'category_{category}')] for category in PRODUCTS
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('🛍️ Veuillez choisir une catégorie de produit:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Aucun produit disponible pour le moment.')

# Fonction pour gérer la sélection de la catégorie
async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category = query.data.split('_')[1]
    context.user_data['category'] = category

    keyboard = [
        [InlineKeyboardButton(f"{product} - 💰 ${PRODUCTS[category][product]['price']}", callback_data=product)]
        for product in PRODUCTS[category]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f'📦 {category}: Sélectionnez un produit:', reply_markup=reply_markup)

# Fonction pour gérer la sélection du produit
async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product = query.data
    category = context.user_data['category']
    context.user_data['product'] = product

    quantities = PRODUCTS[category][product]["quantities"]
    keyboard = [
        [InlineKeyboardButton(f'{q}g - 💵 ${PRODUCTS[category][product]["price"] * q}', callback_data=str(q))] for q in quantities
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f'🔢 Choisissez la quantité pour {product}:', reply_markup=reply_markup)

# Fonction pour gérer la sélection de la quantité
async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    quantity = int(query.data)
    product = context.user_data['product']
    category = context.user_data['category']

    if 'order' not in context.user_data:
        context.user_data['order'] = []

    context.user_data['order'].append({
        'category': category,
        'product': product,
        'quantity': quantity,
        'price': PRODUCTS[category][product]["price"] * quantity
    })
    await query.answer()

    await query.edit_message_text(f'✅ {quantity}g de {product} ajouté à votre commande.')

    keyboard = [
        [InlineKeyboardButton("✅ Confirmer la commande", callback_data='confirm')],
        [InlineKeyboardButton("➕ Ajouter un autre produit", callback_data='add_more')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Que souhaitez-vous faire ensuite ?", reply_markup=reply_markup)

# Fonction pour confirmer la commande et gérer les paiements
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    order_summary = "\n".join(
        [f"{item['quantity']}g de {item['product']} - ${item['price']}" for item in context.user_data['order']])
    total_price = sum([item['price'] for item in context.user_data['order']])

    order_id = generate_order_id()
    context.user_data['order_id'] = order_id

    ORDERS[order_id] = {
        "user_id": update.effective_user.id,
        "order": context.user_data['order'],
        "vendor_id": None,
        "total_price": total_price,
        "payment_method": None,
        "paid": False
    }

    # Enforce crypto payment for orders above 300€
    if total_price > 300:
        await query.edit_message_text(f"🛒 Commande confirmée avec succès.\n\nID de commande: {order_id}\n\n{order_summary}\n\nTotal: 💰 ${total_price}\n\n⚠️ Les paiements en crypto-monnaie sont obligatoires pour les commandes au-dessus de 300€.")
        keyboard = [
            [InlineKeyboardButton("💸 Payer en Bitcoin", callback_data=f'pay_bitcoin_{order_id}')],
            [InlineKeyboardButton("💸 Payer en Ethereum", callback_data=f'pay_ethereum_{order_id}')]
        ]
    else:
        await query.edit_message_text(f"🛒 Commande confirmée avec succès.\n\nID de commande: {order_id}\n\n{order_summary}\n\nTotal: 💰 ${total_price}")
        keyboard = [
            [InlineKeyboardButton("💸 Payer en Bitcoin", callback_data=f'pay_bitcoin_{order_id}')],
            [InlineKeyboardButton("💸 Payer en Ethereum", callback_data=f'pay_ethereum_{order_id}')],
            [InlineKeyboardButton("💵 Payer en Espèces", callback_data=f'pay_cash_{order_id}')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Veuillez choisir votre méthode de paiement:", reply_markup=reply_markup)

# Gestion des paiements
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split('_')
    payment_method = data[1]
    order_id = data[2]

    if order_id in ORDERS:
        ORDERS[order_id]["payment_method"] = payment_method
        ORDERS[order_id]["paid"] = True

        # Assigner un vendeur disponible
        ORDERS[order_id]["vendor_id"] = random.choice(VENDORS)
        vendor_id = ORDERS[order_id]["vendor_id"]

        # Démarrer la conversation
        CONVERSATIONS[order_id] = {"client": update.effective_user.id, "vendor": vendor_id}

        await query.edit_message_text(f"✅ Paiement reçu en {payment_method.capitalize()} pour la commande {order_id}. Le vendeur sera notifié.")
        await context.bot.send_message(chat_id=vendor_id, text=f"Une commande (ID: {order_id}) a été confirmée et payée via {payment_method.capitalize()}.")
    else:
        await query.edit_message_text("❌ Erreur : Commande introuvable.")

# Gérer la notification du vendeur
async def notify_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = query.data.split('_')[1]

    if order_id in ORDERS:
        vendor_id = ORDERS[order_id]["vendor_id"]
        if vendor_id:
            await context.bot.send_message(chat_id=vendor_id, text=f"Une commande (ID: {order_id}) a été confirmée.")
            await query.edit_message_text(f"Le vendeur a été notifié de votre commande (ID: {order_id}).")
        else:
            await query.edit_message_text(f"Aucun vendeur n'est encore associé à cette commande (ID: {order_id}).")
    else:
        await query.edit_message_text(f"Commande non trouvée (ID: {order_id}).")

# Gérer l'envoi de messages anonymes
async def anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = query.data.split('_')[1]
    context.user_data['current_order'] = order_id

    await query.message.reply_text(f"💬 Envoyez votre message pour la commande ID: {order_id}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'current_order' in context.user_data:
        order_id = context.user_data['current_order']
        user_message = update.message.text

        if order_id in CONVERSATIONS:
            client_id = CONVERSATIONS[order_id]["client"]
            vendor_id = CONVERSATIONS[order_id]["vendor"]

            # Si le message provient du client
            if update.effective_user.id == client_id:
                await context.bot.send_message(chat_id=vendor_id, text=f"Message anonyme du client pour la commande {order_id}: {user_message}")
                await update.message.reply_text("💬 Votre message a été envoyé anonymement au vendeur.")
            # Si le message provient du vendeur
            elif update.effective_user.id == vendor_id:
                await context.bot.send_message(chat_id=client_id, text=f"Message anonyme du vendeur pour la commande {order_id}: {user_message}")
                await update.message.reply_text("💬 Votre message a été envoyé anonymement au client.")
        else:
            await update.message.reply_text("❌ Erreur : Conversation non trouvée.")

        # Suppression du contexte de l'ordre après l'envoi du message
        del context.user_data['current_order']

# Gestion des messages d'ouverture et de fermeture
async def open_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔓 Le service est maintenant ouvert.")
    # Supprimer le message de fermeture précédent
    if 'close_message' in context.chat_data:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.chat_data['close_message'])

async def close_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text("🔒 Le service est maintenant fermé.")
    context.chat_data['close_message'] = message.message_id
    # Supprimer le message d'ouverture précédent
    if 'open_message' in context.chat_data:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.chat_data['open_message'])

# Configuration du bot avec les handlers
def main():
    app = ApplicationBuilder().token("6940899854:AAEHzrOXvEoVTMbzftjTFEZ9VoKxD2tDWQY").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(select_category, pattern="^category_"))
    app.add_handler(CallbackQueryHandler(select_product, pattern="^[^_]*$"))
    app.add_handler(CallbackQueryHandler(select_quantity, pattern="^\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_order, pattern="^confirm$"))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(notify_vendor, pattern="^notify_"))
    app.add_handler(CallbackQueryHandler(anonymous_message, pattern="^message_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("open", open_message))
    app.add_handler(CommandHandler("close", close_message))

    app.run_polling()

if __name__ == "__main__":
    main()
