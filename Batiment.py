class Batiment:
    def __init__(self, id_building: str, list_infras: list, building_type: str,  nb_maisons: int):
        self.id_building = id_building,
        self.list_infras = list_infras,
        self.building_type = building_type,
        self.nb_maisons = nb_maisons

    def get_building_difficulty(self):
        total_difficulty = 0.0

        for infra in self.list_infras:
            difficulty = infra.get_infra_difficulty()
            if difficulty is not None:
                total_difficulty += difficulty
        return total_difficulty

    def __iter__(self):
        """Rend le bâtiment itérable sur ses infrastructures."""
        return iter(self.list_infras)