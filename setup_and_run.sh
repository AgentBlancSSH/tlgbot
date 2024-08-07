#!/bin/bash

# Fonction pour afficher un message en couleur
function echo_color {
    echo -e "\033[1;32m$1\033[0m"
}

# 1. Mettre à jour le système
echo_color "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# 2. Installer Python3 et pip si nécessaire
echo_color "Vérification de Python3 et pip..."
if ! command -v python3 &> /dev/null
then
    echo_color "Python3 n'est pas installé. Installation..."
    sudo apt install python3 -y
else
    echo_color "Python3 est déjà installé."
fi

if ! command -v pip3 &> /dev/null
then
    echo_color "pip3 n'est pas installé. Installation..."
    sudo apt install python3-pip -y
else
    echo_color "pip3 est déjà installé."
fi

# 3. Installer les dépendances Python nécessaires
echo_color "Installation des dépendances Python..."
pip3 install --upgrade pip
pip3 install python-telegram-bot python-dotenv

# 4. Vérifier si le fichier .env existe
echo_color "Vérification du fichier .env..."
if [ ! -f ".env" ]; then
    echo_color "Le fichier .env est manquant. Veuillez créer un fichier .env avec votre token Telegram."
    exit 1
fi

# 5. Exécuter le script Python
echo_color "Lancement du bot Telegram..."
python3 bot.py
