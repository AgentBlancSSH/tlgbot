#!/bin/bash

# Fonction pour afficher des messages colorés
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

function print_colored() {
    echo -e "${2}${1}${RESET}"
}

# Mise à jour du système
print_colored "Mise à jour du système..." $BLUE
sudo apt-get update && sudo apt-get upgrade -y || { print_colored "Échec de la mise à jour du système." $RED; exit 1; }

# Vérification de Python3 et pip3
print_colored "Vérification de Python3 et pip..." $BLUE
if ! command -v python3 &> /dev/null; then
    print_colored "Python3 n'est pas installé. Installation en cours..." $YELLOW
    sudo apt-get install python3 -y || { print_colored "Échec de l'installation de Python3." $RED; exit 1; }
else
    print_colored "Python3 est déjà installé." $GREEN
fi

if ! command -v pip3 &> /dev/null; then
    print_colored "pip3 n'est pas installé. Installation en cours..." $YELLOW
    sudo apt-get install python3-pip -y || { print_colored "Échec de l'installation de pip3." $RED; exit 1; }
else
    print_colored "pip3 est déjà installé." $GREEN
fi

# Création de l'environnement virtuel
print_colored "Création de l'environnement virtuel..." $BLUE
python3 -m venv venv || { print_colored "Échec de la création de l'environnement virtuel." $RED; exit 1; }
source venv/bin/activate

# Vérification et création du fichier .env
if [ ! -f .env ]; then
    print_colored "Le fichier .env est manquant. Veuillez entrer votre token Telegram pour créer le fichier .env." $YELLOW
    read -p "Entrez votre token Telegram : " API_TOKEN_E

    # Créer le fichier .env avec le token
    echo "API_TOKEN_E=$API_TOKEN_E" > .env
    print_colored "Le fichier .env a été créé avec succès." $GREEN
else
    print_colored "Le fichier .env existe déjà." $GREEN
fi

# Vérification du fichier requirements.txt
if [ ! -f requirements.txt ]; then
    print_colored "Le fichier requirements.txt est manquant. Création d'un fichier requirements.txt par défaut." $YELLOW
    cat <<EOF > requirements.txt
pyTelegramBotAPI==4.11.0
python-dotenv==0.19.2
EOF
    print_colored "Le fichier requirements.txt a été créé avec les dépendances de base." $GREEN
fi

# Installation des dépendances Python
print_colored "Installation des dépendances Python..." $BLUE
pip install -r requirements.txt || { print_colored "Échec de l'installation des dépendances Python." $RED; deactivate; exit 1; }

# Démarrer le bot
print_colored "Démarrage du bot..." $BLUE
python3 bot_script.py || { print_colored "Échec du démarrage du bot." $RED; deactivate; exit 1; }

print_colored "Le script setup_and_run.sh a été exécuté avec succès." $GREEN
