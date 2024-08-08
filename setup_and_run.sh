#!/bin/bash

# Mettre à jour le système
echo "Mise à jour du système..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Installer Python et pip si ce n'est pas déjà fait
echo "Installation de Python et pip..."
sudo apt-get install -y python3 python3-pip

# Installer les dépendances Python
echo "Installation des dépendances Python..."
pip3 install --upgrade pip
pip3 install python-telegram-bot

# Assurez-vous que le script Python est exécutable
echo "Rendre le script Python exécutable..."
chmod +x bot_script.py

# Lancer le script Python
echo "Lancement du script Python..."
python3 bot_script.py

# Indiquer que tout s'est bien passé
echo "Installation terminée et script lancé avec succès."
