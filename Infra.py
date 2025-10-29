class Infra:
    def __init__(self, infra_id: str, length: float, infra_type: str, nb_houses: int):
        self.infra_id = infra_id
        self.length = length
        self.infra_type = infra_type
        self.nb_houses = nb_houses

    def __str__(self):
        """Retourne une représentation lisible de l'objet."""
        return f"Infra(id={self.infra_id}, longueur={self.longueur}, type={self.infra_type}, nb_houdes={self.nb_houdes})"

    def repair_infra(self, infra_id):
        """Modifie le type de l'infrastructure."""
        
        if (self.infra_type == "a_reparer"):
            self.infra_type = "intact"
            print(f"L'infrastructure {self.infra_id} est a réparer. Nouveau type : {self.infra_type}")
            return self
        else:
            return None
        
    def get_infra_difficulty(self):
        infra_difficulty = self.length / self.nb_houses
        return infra_difficulty

    def __radd__(self, other):
        """
        Permet d'utiliser sum() sur une liste d'objets Infra.
        Ici, on additionne les longueurs.
        """
        if other == 0:  # condition nécessaire pour sum()
            return self.longueur
        return other + self.longueur
        
