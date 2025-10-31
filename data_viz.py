import pandas as pd
import matplotlib.pyplot as plt

# --- Création manuelle du DataFrame (ou lecture CSV propre)
data = {
    "phase": [0, 1, 2, 3, 4],
    "nb_batiments": [1, 62, 9, 5, 2],
    "nb_infrastructures": [3, 142, 29, 17, 6],
    "nb_maisons": [1, 289, 20, 7, 3],
    "duree_heures": [9.35, 21.07, 37.67, 38.17, 43.17],
    "cout_euros": ["18 483,26", "787 344,58", "215 073,70", "141 049,04", "73 384,95"]
}

df = pd.DataFrame(data)

# --- Nettoyage du coût (remplacement espace/virgule et conversion en float)
df["cout_euros"] = (
    df["cout_euros"]
    .str.replace(" ", "", regex=False)   # supprime les espaces
    .str.replace(",", ".", regex=False)  # remplace virgule par point
    .astype(float)
)

# --- Tri par phase
df = df.sort_values("phase")

# --- Diagramme en barres : coût par phase
plt.figure(figsize=(8, 5))
plt.bar(df["phase"], df["cout_euros"], color="steelblue")
plt.title("💰 Coût (€) par Phase du Chantier")
plt.xlabel("Phase")
plt.ylabel("Coût (en euros)")
plt.xticks(df["phase"])
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()


fig, ax1 = plt.subplots(figsize=(9, 5))

# Barres : coût
ax1.bar(df["phase"], df["cout_euros"], color="skyblue", label="Coût (€)")
ax1.set_xlabel("Phase")
ax1.set_ylabel("Coût (€)", color="blue")
ax1.tick_params(axis="y", labelcolor="blue")

# Courbe : durée
ax2 = ax1.twinx()
ax2.plot(df["phase"], df["duree_heures"], color="orange", marker="o", label="Durée (heures)")
ax2.set_ylabel("Durée (heures)", color="orange")
ax2.tick_params(axis="y", labelcolor="orange")

plt.title("Comparaison du coût et de la durée par phase")
plt.grid(axis="x", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()
