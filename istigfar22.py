import tkinter as tk

# Fonction pour incrémenter le compteur
def incrementer_istighfar():
    global compteur_istighfar
    compteur_istighfar += 1
    label_compteur.config(text=f"Compteur d'Istighfar: {compteur_istighfar}")

# Fonction pour quitter l'application
def quitter():
    print(f"Vous avez fait {compteur_istighfar} istighfar.")
    root.quit()

# Initialisation du compteur
compteur_istighfar = 0

# Création de la fenêtre principale
root = tk.Tk()
root.title("Compteur d'Istighfar")

# Configuration de la taille de la fenêtre
root.geometry("300x200")

# Rendre la fenêtre flottante (toujours au-dessus)
root.attributes("-topmost", True)

# Création d'un label pour afficher le compteur
label_compteur = tk.Label(root, text=f"Compteur d'Istighfar: {compteur_istighfar}", font=("Arial", 16))
label_compteur.pack(pady=20)

# Bouton pour incrémenter l'istighfar
button_istighfar = tk.Button(root, text="Faire un Istighfar", command=incrementer_istighfar, font=("Arial", 14))
button_istighfar.pack(pady=10)

# Bouton pour quitter l'application
button_quitter = tk.Button(root, text="Quitter", command=quitter, font=("Arial", 14))
button_quitter.pack(pady=10)

# Lancer l'interface graphique
root.mainloop()
