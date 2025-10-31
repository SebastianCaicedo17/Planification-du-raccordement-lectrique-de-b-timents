import pandas as pd

# Fichier source
input_xlsx = "reseau_en_arbre.xlsx"
# Lire le fichier Excel
df = pd.read_excel(input_xlsx)

# Filtrer : ne garder que les lignes où infra_type n'est pas "infra_intacte"
df_clean = df[df["infra_type"] != "infra_intacte"]

# Sauver dans un nouveau csv
output_csv = "reseau_en_arbre_non_intact.csv"
df_clean.to_csv(output_csv, index=False)

print(f"Fichier filtré sauvegardé sous : {output_csv}")
print(f"Lignes restantes : {len(df_clean)}")
print(df_clean.head())