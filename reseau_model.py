import os
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Union
import unicodedata


# ------------------------------------------------------------
# Modélisation du réseau: classes Infra et Batiment
# ------------------------------------------------------------

# Mappings prix et durée selon le type d'infrastructure
def _normalize_infra_key(value: str) -> str:
    if not value:
        return ""
    t = value.strip().lower()
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('ascii')
    t = t.replace('-', '').replace(' ', '')
    return t

def _is_a_remplacer(value: str) -> bool:
    if value is None:
        return False
    t = str(value).strip().lower()
    return t in {"a_remplacer", "a remplacer", "a-remplacer"}


# Mappings prix et durée avec clés normalisées (sans accents/espaces/tirets)
_INFRA_PRICE_MAPPING: Dict[str, float] = {
    "aerien": 500.0,
    "semiaerien": 750.0,
    "fourreau": 900.0,
}

_INFRA_DURATION_MAPPING: Dict[str, float] = {
    "aerien": 2.0,
    "semiaerien": 4.0,
    "fourreau": 5.0,
}


@dataclass
class Infra:
    """Représente un tronçon d'infrastructure électrique."""
    building_id: str
    infra_id: str
    longueur: float
    type_infra: str  # "aérien", "semi-aérien", ou "fourreau" (type technique)
    nb_houses: int
    infra_state: str = "a_remplacer"

    def get_prix(self) -> float:
        """Retourne le prix par mètre selon le type_infra."""
        key = _normalize_infra_key(self.type_infra)
        return _INFRA_PRICE_MAPPING.get(key, 0.0)

    def get_duree(self) -> float:
        """Retourne la durée par mètre selon le type_infra."""
        key = _normalize_infra_key(self.type_infra)
        return _INFRA_DURATION_MAPPING.get(key, 0.0)

    def get_infra_difficulty(self) -> float:
        """Difficulté locale: longueur × durée × cout / nb_maisons.

        - Si nb_houses == 0, on évite la division par 0 en considérant 1 maison.
        """
        if str(self.infra_state) == "infra_intacte":
            return 0.0
        denominator = self.nb_houses if self.nb_houses > 0 else 1
        return (float(self.longueur) * self.get_duree() * self.get_prix()) / float(denominator)

    def repair_infra(self) -> None:
        """Marque l'infrastructure comme réparée (intacte)."""
        self.infra_state = "infra_intacte"

    def __radd__(self, other: Union[int, float]) -> float:
        """Permet sum(liste_infras) en additionnant les difficultés.

        - sum appelle d'abord 0 + item: on gère donc le cas numérique.
        """
        if isinstance(other, (int, float)):
            return other + self.get_infra_difficulty()
        return NotImplemented


@dataclass
class Batiment:
    """Représente un bâtiment et ses infrastructures associées."""
    id_building: str
    type_batiment: str
    list_infras: List[Infra]

    def get_building_difficulty(self) -> float:
        """Somme des difficultés des infras connectées."""
        return sum(self.list_infras)

    def __lt__(self, other: "Batiment") -> bool:
        """Comparaison par difficulté pour trier du plus facile au plus difficile."""
        return self.get_building_difficulty() < other.get_building_difficulty()


# ------------------------------------------------------------
# Chargement des données (CSV prioritaire, fallback sur XLSX)
# ------------------------------------------------------------

def load_network_dataframe() -> pd.DataFrame:
    """Charge uniquement reseau_en_arbre_final.xlsx (feuille reseau_en_arbre). Simple et strict."""
    final_xlsx = "reseau_en_arbre_final.xlsx"
    if not os.path.exists(final_xlsx):
        raise FileNotFoundError("Fichier reseau_en_arbre_final.xlsx introuvable")

    df = pd.read_excel(final_xlsx, sheet_name="reseau_en_arbre")
    # Correction minimale: harmoniser 'nb maisons' -> 'nb_maisons'
    if "nb maisons" in df.columns and "nb_maisons" not in df.columns:
        df = df.rename(columns={"nb maisons": "nb_maisons"})

    return df

    # Fallback historique: CSV/XLSX + fichiers annexes infra.csv / batiments.csv
    csv_path = "reseau_en_arbre.csv"
    xlsx_path = "reseau_en_arbre.xlsx"

    if os.path.exists(csv_path):
        network_df = pd.read_csv(csv_path)
    elif os.path.exists(xlsx_path):
        network_df = pd.read_excel(xlsx_path)
    else:
        raise FileNotFoundError(
            "Aucun fichier de réseau trouvé: reseau_en_arbre_final.xlsx, reseau_en_arbre.csv ou reseau_en_arbre.xlsx"
        )

    if not os.path.exists("infra.csv"):
        raise FileNotFoundError("Fichier infra.csv introuvable")
    infra_df = pd.read_csv("infra.csv")

    if not os.path.exists("batiments.csv"):
        raise FileNotFoundError("Fichier batiments.csv introuvable")
    batiments_df = pd.read_csv("batiments.csv")

    network_df = network_df.merge(
        infra_df,
        left_on="infra_id",
        right_on="id_infra",
        how="left"
    )

    network_df = network_df.merge(
        batiments_df[["id_batiment", "nb_maisons"]],
        on="id_batiment",
        how="left"
    )

    if "nb_maisons_x" in network_df.columns:
        network_df["nb_maisons"] = network_df["nb_maisons_y"].fillna(network_df["nb_maisons_x"])
        network_df = network_df.drop(columns=["nb_maisons_x", "nb_maisons_y"], errors="ignore")

    return network_df


# ------------------------------------------------------------
# Construction des objets et calcul des difficultés
# ------------------------------------------------------------

def build_infras_from_df(df: pd.DataFrame) -> List[Infra]:
    """Crée les objets Infra à partir des lignes du DataFrame.

    Note: on ignore la colonne 'infra_type' (tous à remplacer). On prend toutes
    les lignes avec un 'type_infra' renseigné.
    """
    required_cols = {"infra_id", "longueur", "type_infra", "nb_maisons", "id_batiment"}
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}. Colonnes présentes: {list(df.columns)}")

    # Diagnostic minimal: lignes sans type_infra
    diag_missing_type = df[(df["type_infra"].isna() | (df["type_infra"].astype(str).str.strip() == ""))]
    if len(diag_missing_type) > 0:
        sample = diag_missing_type[["id_batiment", "infra_id"]].head(10).to_dict(orient="records")
        print(f"ATTENTION: {len(diag_missing_type)} lignes 'a_remplacer' sans type_infra. Exemples: {sample}")

    infras: List[Infra] = []
    for _, row in df.iterrows():
        # Vérifier que type_infra est présent
        type_infra_val = str(row.get("type_infra", "")).strip()
        if pd.isna(row.get("type_infra")) or not type_infra_val:
            continue  # Ignorer les infras sans type_infra
        
        infras.append(
            Infra(
                building_id=str(row["id_batiment"]),
                infra_id=str(row["infra_id"]),
                longueur=float(row["longueur"]),
                type_infra=type_infra_val,
                nb_houses=int(row["nb_maisons"]) if not pd.isna(row["nb_maisons"]) else 0,
            )
        )
    return infras


def group_infras_by_building(df: pd.DataFrame, infras: List[Infra]) -> List[Batiment]:
    """Groupe les infras par id_batiment et construit les Batiment, inclut le type_batiment.

    Inclut désormais tous les bâtiments présents dans le DataFrame (même sans infra à remplacer)
    afin que le comptage corresponde au fichier source (ex: 86 bâtiments).
    """
    # Créer un mapping id_batiment -> type_batiment (take unique ou le 1er trouvé)
    building_type_map: Dict[str, str] = {}
    if "type_batiment" in df.columns:
        for _, row in df.iterrows():
            b_id = str(row["id_batiment"])
            tpe = normalize_type_batiment(str(row["type_batiment"])) if not pd.isna(row["type_batiment"]) else "other"
            if b_id not in building_type_map:
                building_type_map[b_id] = tpe

    # Grouper les infras par bâtiment, en évitant les doublons globaux d'infra_id
    by_building: Dict[str, List[Infra]] = {}
    assigned_infra_ids: Set[str] = set()
    for infra in infras:
        if infra.infra_id in assigned_infra_ids:
            # Ne pas compter deux fois le même tronçon s'il est référencé par plusieurs bâtiments
            continue
        by_building.setdefault(infra.building_id, []).append(infra)
        assigned_infra_ids.add(infra.infra_id)

    # Inclure tous les id_batiment présents, même si aucune infra à remplacer
    all_building_ids = [str(b) for b in df["id_batiment"].dropna().unique()]
    for b_id in all_building_ids:
        by_building.setdefault(b_id, [])

    buildings: List[Batiment] = [
        Batiment(id_building=b_id, list_infras=lst, type_batiment=building_type_map.get(b_id, "other"))
        for b_id, lst in by_building.items()
    ]
    return buildings


def normalize_type_batiment(tp: str):
    if not tp:
        return "other"
    # Minuscule, retire accents, espaces, etc.
    t = tp.strip().lower()
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('ascii')
    t = t.replace(' ', '')
    if 'hopital' in t:
        return 'hopital'
    if 'ecole' in t:
        return 'ecole'
    if 'habitation' in t:
        return 'habitation'
    return t or 'other'


def main() -> None:
    # 1) Charger les données
    df = load_network_dataframe()
    # 2) Créer les Infra
    infras = build_infras_from_df(df)
    # 3) Créer les Batiment par groupement
    buildings = group_infras_by_building(df, infras)

    # Priorité tri: hopital (0), ecole (1), reste (2), puis difficulté croissante
    def priority_key(b: Batiment):
        t = b.type_batiment
        if t == "hopital":
            prio = 0
        elif t == "ecole":
            prio = 1
        else:
            prio = 2
        return (prio, b.get_building_difficulty())

    buildings_sorted = sorted(buildings, key=priority_key)
    # Ne pas afficher les bâtiments sans infra à remplacer
    buildings_sorted_display = [b for b in buildings_sorted if len(b.list_infras) > 0]

    # 5) Affichage clair avec compteur
    print("Classement des batiments (avec infras a remplacer):")
    for index, b in enumerate(buildings_sorted_display, start=1):
        difficulty = b.get_building_difficulty()
        print(f"{index:>3}. {b.id_building} [{b.type_batiment}] - difficulte {difficulty:.2f}")

    # Afficher le nombre d'id_batiment avec au moins une infra à remplacer
    # puis nombre de Batiment classés, puis liste d'id_batiment manquants
    original_building_ids = df["id_batiment"].dropna().unique()
    classified_building_ids = [b.id_building for b in buildings_sorted_display]
    missing_building_ids = [b for b in original_building_ids if b not in classified_building_ids]

    print(f"\nBati avec au moins une infra (toutes lignes prises): {len(original_building_ids)}")
    print(f"Bati classes (affiches): {len(classified_building_ids)}")
    if missing_building_ids:
        print(f"WARNING: Les bâtiments suivants n'ont pas été classés: {missing_building_ids}")
        # Diagnostic succinct par id manquant (sans utiliser 'infra_type')
        try:
            check = df[df["id_batiment"].isin(missing_building_ids)]
            grp = []
            for bid in missing_building_ids[:10]:
                sub = check[check["id_batiment"] == bid]
                n_total = len(sub)
                n_type_missing = len(sub[sub["type_infra"].isna() | (sub["type_infra"].astype(str).str.strip() == "")])
                vals_type_infra = sorted(list({str(x).strip() for x in sub["type_infra"].dropna().unique()}))
                grp.append({"id": bid, "rows": n_total, "type_infra_vide": n_type_missing, "type_infra_vals": vals_type_infra})
            print(f"DIAG: {grp}")
        except Exception:
            pass

    # Nettoyage: pas de comparaisons avec d'autres feuilles dans l'affichage final


if __name__ == "__main__":

    # (Objectif futur: ajouter coût pondéré, rentabilité, etc.)
    main()


