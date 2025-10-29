import os
from dataclasses import dataclass
from typing import List, Dict, Iterable, Union
import pandas as pd


# ------------------------------------------------------------
# Modélisation du réseau: classes Infra et Batiment
# ------------------------------------------------------------

@dataclass
class Infra:
    """Représente un tronçon d'infrastructure électrique."""
    infra_id: str
    length: float
    infra_type: str  # "infra_intacte" ou "a_remplacer"
    nb_houses: int

    def get_infra_difficulty(self) -> float:
        """Difficulté locale: longueur par maison (length / nb_houses).

        - Si nb_houses == 0, on évite la division par 0 en considérant 1 maison.
        """
        denominator = self.nb_houses if self.nb_houses > 0 else 1
        return float(self.length) / float(denominator)

    def repair_infra(self) -> None:
        """Marque l'infrastructure comme réparée."""
        self.infra_type = "infra_intacte"

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
    """Charge le réseau depuis reseau_en_arbre.csv si présent,
    sinon depuis reseau_en_arbre.xlsx.

    Colonnes attendues:
    - infra_id
    - longueur
    - infra_type
    - nb_maisons
    - id_batiment
    """
    csv_path = "reseau_en_arbre.csv"
    xlsx_path = "reseau_en_arbre.xlsx"

    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    elif os.path.exists(xlsx_path):
        return pd.read_excel(xlsx_path)
    else:
        raise FileNotFoundError(
            "Aucun fichier de réseau trouvé: reseau_en_arbre.csv ou reseau_en_arbre.xlsx"
        )


# ------------------------------------------------------------
# Construction des objets et calcul des difficultés
# ------------------------------------------------------------

def build_infras_from_df(df: pd.DataFrame) -> List[Infra]:
    """Crée les objets Infra à partir des lignes du DataFrame.

    Note: on IGNORE les infrastructures intactes; seules celles "a_remplacer"
    sont transformées en objets Infra pour le calcul de difficulté.
    """
    required_cols = {"infra_id", "longueur", "infra_type", "nb_maisons", "id_batiment"}
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        # Tentative de renommage si le fichier utilise d'autres conventions
        renaming_candidates: Dict[str, str] = {
            "length": "longueur",
            "nb_houses": "nb_maisons",
        }
        to_rename = {src: dst for src, dst in renaming_candidates.items() if src in df.columns and dst not in df.columns}
        if to_rename:
            df = df.rename(columns=to_rename)
            missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes: {missing}. Colonnes présentes: {list(df.columns)}")

    infras: List[Infra] = []
    for _, row in df.iterrows():
        # Ne garder que les tronçons à remplacer
        if str(row["infra_type"]) != "a_remplacer":
            continue
        infras.append(
            Infra(
                infra_id=str(row["infra_id"]),
                length=float(row["longueur"]),
                infra_type=str(row["infra_type"]),
                nb_houses=int(row["nb_maisons"]),
            )
        )
    return infras


def group_infras_by_building(df: pd.DataFrame, infras: List[Infra]) -> List[Batiment]:
    """Groupe les infras par id_batiment et construit les Batiment."""
    build_id_series: Iterable[str] = (str(row["id_batiment"]) for _, row in df.iterrows())
    by_building: Dict[str, List[Infra]] = {}
    for building_id, infra in zip(build_id_series, infras):
        by_building.setdefault(building_id, []).append(infra)

    buildings: List[Batiment] = [Batiment(id_building=b_id, list_infras=lst) for b_id, lst in by_building.items()]
    return buildings


def main() -> None:
    # 1) Charger les données
    df = load_network_dataframe()

    # 2) Créer les Infra
    infras = build_infras_from_df(df)

    # 3) Créer les Batiment par groupement
    buildings = group_infras_by_building(df, infras)

    # 4) Trier du plus facile (difficulté faible) au plus difficile
    buildings_sorted = sorted(buildings)

    # 5) Affichage clair
    for b in buildings_sorted:
        difficulty = b.get_building_difficulty()
        print(f"{b.id_building} → difficulté = {difficulty:.2f}")


if __name__ == "__main__":

    # (Objectif futur: ajouter coût pondéré, rentabilité, etc.)
    main()


