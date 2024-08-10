#!/bin/bash

# Nom du script Python
PYTHON_SCRIPT="bot_scipt.py"

# Fonction pour vérifier si un paquet est installé
function check_install {
    if ! command -v $1 &> /dev/null
    then
        echo "$1 n'est pas installé. Installation en cours..."
        sudo apt-get install -y $1
    else
        echo "$1 est déjà installé."
    fi
}

# Vérification et installation de Python
check_install python3

# Vérification et installation de pip
check_install pip3

# Mise à jour de pip
echo "Mise à jour de pip..."
pip3 install --upgrade pip

# Liste des packages Python nécessaires
REQUIRED_PIP_PACKAGES=(
    "python-telegram-bot"
    "matplotlib"
)

# Installation des packages Python nécessaires
for PACKAGE in "${REQUIRED_PIP_PACKAGES[@]}"; do
    if ! pip3 show $PACKAGE &> /dev/null
    then
        echo "Le package Python $PACKAGE n'est pas installé. Installation en cours..."
        pip3 install $PACKAGE
    else
        echo "Le package Python $PACKAGE est déjà installé."
    fi
done

# Mise à jour des packages Python installés
echo "Mise à jour des packages Python..."
pip3 list --outdated | grep -o '^\S*' | xargs -n1 pip3 install -U

# Lancement du script Python
echo "Lancement du script Python $PYTHON_SCRIPT..."
python3 $PYTHON_SCRIPT
