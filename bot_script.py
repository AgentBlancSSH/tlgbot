import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Configurer le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Données de base
PRODUCTS = {}
ORDERS = {}
ADMINS = [123456789]  # Remplacez par l'ID Telegram des administrateurs

# Générer un identifiant de commande unique
def generate_order_id():
    return str(len(ORDERS) + 1)

# Fonction pour démarrer le bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🛒 Boutique", callback_data='shop')],
        [InlineKeyboardButton("📜 Historique des commandes", callback_data='order_history')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Bienvenue sur notre service !', reply_markup=reply_markup)

# Affichage du profil utilisateur avec un bouton retour
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    profile_text = f"👤 **Votre Profil**\n\nID utilisateur: `{user.id}`\nNom d'utilisateur: @{user.username}"
    keyboard = [
        [InlineKeyboardButton("🔙 Retour à l'accueil", callback_data='go_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode="Markdown")

# Fonction pour retourner à l'accueil
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await start(update, context)

# Affichage de la boutique
async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if PRODUCTS:
        keyboard = [
            [InlineKeyboardButton(f"📦 {category}", callback_data=f'category_{category}')] for category in PRODUCTS
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('🛍️ Choisissez une catégorie de produit:', reply_markup=reply_markup)
    else:
        await query.message.reply_text('Aucun produit disponible pour le moment.')

# Affichage de l'historique des commandes
async def show_order_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_orders = [order for order_id, order in ORDERS.items() if order['user_id'] == update.effective_user.id]
    
    if user_orders:
        order_texts = []
        for order in user_orders:
            status = order['status']
            order_summary = "\n".join([f"{item['quantity']}g de {item['product']} - ${item['price']}" for item in order['items']])
            order_texts.append(f"Commande ID: {order['order_id']}\nStatut: {status}\n{order_summary}\nTotal: ${order['total_price']}\n\n")
        
        await query.message.reply_text('Voici votre historique de commandes:\n\n' + "".join(order_texts))
    else:
        await query.message.reply_text("Vous n'avez aucune commande.")

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
    await query.message.reply_text(f'📦 {category}: Sélectionnez un produit:', reply_markup=reply_markup)

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
    await query.message.reply_text(f'🔢 Choisissez la quantité pour {product}:', reply_markup=reply_markup)

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

    await query.message.reply_text(f'✅ {quantity}g de {product} ajouté à votre commande.')

    keyboard = [
        [InlineKeyboardButton("✅ Confirmer la commande", callback_data='confirm')],
        [InlineKeyboardButton("➕ Ajouter un autre produit", callback_data='add_more')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Que souhaitez-vous faire ensuite ?", reply_markup=reply_markup)

# Fonction pour confirmer la commande
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    order_summary = "\n".join(
        [f"{item['quantity']}g de {item['product']} - ${item['price']}" for item in context.user_data['order']])
    total_price = sum([item['price'] for item in context.user_data['order']])

    order_id = generate_order_id()
    context.user_data['order_id'] = order_id

    ORDERS[order_id] = {
        "user_id": update.effective_user.id,
        "order_id": order_id,
        "items": context.user_data['order'],
        "total_price": total_price,
        "status": "En traitement"
    }

    await query.message.reply_text(f"🛒 Commande confirmée avec succès.\n\nID de commande: {order_id}\n\n{order_summary}\n\nTotal: 💰 ${total_price}")

    keyboard = [
        [InlineKeyboardButton("📲 Notifier le vendeur", callback_data=f'notify_{order_id}')],
        [InlineKeyboardButton("💬 Envoyer un message", callback_data=f'message_{order_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Vous pouvez maintenant communiquer avec le vendeur de manière anonyme.",
                                   reply_markup=reply_markup)

    # Réinitialiser les données de l'utilisateur
    context.user_data.clear()

# Suivi dynamique du statut de la commande
async def update_order_status(order_id, new_status):
    if order_id in ORDERS:
        ORDERS[order_id]['status'] = new_status

# Gérer la notification du vendeur
async def notify_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = query.data.split('_')[1]

    if order_id in ORDERS:
        await update_order_status(order_id, "En cours de préparation")
        await query.message.reply_text(f"Le statut de votre commande ID: {order_id} a été mis à jour : En cours de préparation.")
    else:
        await query.message.reply_text("Commande non trouvée.")

# Configuration et lancement du bot
if __name__ == '__main__':
    application = ApplicationBuilder().token("6940899854:AAEHzrOXvEoVTMbzftjTFEZ9VoKxD2tDWQY").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(go_back, pattern="^go_back$"))
    application.add_handler(CallbackQueryHandler(show_shop, pattern="^shop$"))
    application.add_handler(CallbackQueryHandler(show_order_history, pattern="^order_history$"))
    application.add_handler(CallbackQueryHandler(select_category, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(select_product, pattern="^(?!category_|remove_|notify_|message_).*"))
    application.add_handler(CallbackQueryHandler(select_quantity, pattern=r"^\d+$"))
    application.add_handler(CallbackQueryHandler(confirm_order, pattern="^confirm$"))
    application.add_handler(CallbackQueryHandler(notify_vendor, pattern="^notify_"))

    application.run_polling()
