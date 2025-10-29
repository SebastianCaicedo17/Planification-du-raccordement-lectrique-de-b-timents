import pandas as pd

# Lecture du fichier Excel contenant le réseau
network_df = pd.read_excel("reseau_en_arbre.xlsx")

# Filtrer les infrastructures à remplacer
broken_network_df = network_df[network_df["infra_type"] == "a_remplacer"]

# Créer des ensembles (sets) d'identifiants de bâtiments
set_id_batiments = set(network_df["id_batiment"].values)
set_id_broken_batiments = set(broken_network_df["id_batiment"].values)

# Initialiser les listes pour les résultats
list_id_batiment = []
state_batiment = []

# Déterminer l'état de chaque bâtiment
for id_batiment in set_id_batiments:
    list_id_batiment.append(id_batiment)
    if id_batiment in set_id_broken_batiments:
        state_batiment.append("a_reparer")
    else:
        state_batiment.append("intact")

# Créer un DataFrame final avec l'état de chaque bâtiment
state_df = pd.DataFrame({
    "id_batiment": list_id_batiment,
    "state_batiment": state_batiment
})
state_df.to_csv("etat_batiments.csv", index=False)

# Afficher le résultat
print(state_df)
