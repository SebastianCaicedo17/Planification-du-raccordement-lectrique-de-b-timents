import pandas as pd
from typing import List, Dict, Set

from reseau_model import (
    load_network_dataframe,
    build_infras_from_df,
    group_infras_by_building,
    Batiment,
)


def compute_building_difficulty_dynamic(b: Batiment, repaired_ids: Set[str]) -> float:
    # Ignore any infra whose infra_id has already been repaired globally
    total = 0.0
    for infra in b.list_infras:
        if infra.infra_id in repaired_ids:
            continue
        total += infra.get_infra_difficulty()
    return total


def compute_building_cost_and_duration(b: Batiment, workers_per_infra: int = 4) -> Dict[str, float]:
    """Compute total cost (euros) and duration (hours) for a building.

    Assumptions:
    - Cost = sum(length_m * price_per_meter) for all infras
    - Duration per infra = (length_m * hours_per_meter) / min(4, workers_per_infra)
    - Total duration with parallel crews = max(per-infra durations)
    - Total workers = workers_per_infra * nb_infra (all infras done concurrently)
    """
    total_cost = 0.0
    per_infra_hours = []
    effective_workers = max(1, min(4, workers_per_infra))
    for infra in b.list_infras:
        price_per_m = infra.get_prix()
        hours_per_m = infra.get_duree()
        total_cost += float(infra.longueur) * price_per_m
        per_infra_hours.append((float(infra.longueur) * hours_per_m) / float(effective_workers))
    total_hours = max(per_infra_hours) if per_infra_hours else 0.0
    total_workers = effective_workers * len(b.list_infras)
    return {"cost_eur": total_cost, "duration_h": total_hours, "workers_total": total_workers}


def select_order_with_repair(buildings: List[Batiment]):
    """Greedy: hopital(s) first, then ecole(s), then others.
    After picking a building, mark all its infras as repaired, then recompute difficulties.
    Returns ordered list of building ids.
    """
    pick_metrics: Dict[str, Dict] = {}
    # Global repaired infra ids (shared segments not double-counted)
    repaired_ids: Set[str] = set()
    remaining: Dict[str, Batiment] = {b.id_building: b for b in buildings}
    pick_cost: Dict[str, float] = {}

    def current_sorted(ids: List[str]) -> List[str]:
        # compute dynamic difficulty
        scored = []
        for bid in ids:
            b = remaining[bid]
            diff = compute_building_difficulty_dynamic(b, repaired_ids)
            scored.append((diff, bid))
        scored.sort(key=lambda x: x[0])
        return [bid for _, bid in scored]

    # group by type
    hospitals = [b.id_building for b in buildings if b.type_batiment == "hopital"]
    schools = [b.id_building for b in buildings if b.type_batiment == "ecole"]
    others = [b.id_building for b in buildings if b.type_batiment not in ("hopital", "ecole")]

    ordered: List[str] = []

    for group in (hospitals, schools, others):
        # pick greedily within the group
        pool = [bid for bid in group if bid in remaining]
        while pool:
            pool = current_sorted(pool)
            bid = pool.pop(0)
            # record dynamic difficulty at selection time and metrics
            pick_cost[bid] = compute_building_difficulty_dynamic(remaining[bid], repaired_ids)
            pick_metrics[bid] = compute_building_cost_and_duration(remaining[bid], workers_per_infra=4)
            ordered.append(bid)
            # repair all infras of this building by flipping state and marking globally
            for infra in remaining[bid].list_infras:
                infra.repair_infra()
                repaired_ids.add(infra.infra_id)
            # remove from remaining
            remaining.pop(bid, None)
            # refresh pool (in case some buildings end up with 0 diff, still keep order by recalc)
            pool = [p for p in pool if p in remaining]

    # Any building with no infras (phase 0 candidates) may remain only if it had empty list
    ordered.extend([bid for bid in remaining.keys()])
    for bid in remaining.keys():
        pick_cost.setdefault(bid, 0.0)
        pick_metrics.setdefault(bid, compute_building_cost_and_duration(remaining[bid], workers_per_infra=4))
    return ordered, pick_cost, pick_metrics


def assign_phases(order: List[str], buildings: List[Batiment], pick_cost: Dict[str, float]) -> pd.DataFrame:
    # Phase rules (user spec):
    # - 0: hôpital
    # - 1: ~40% du coût (hors hôpitaux)
    # - 2,3,4: ~20% chacun (reste du coût)
    id_to_b: Dict[str, Batiment] = {b.id_building: b for b in buildings}

    hospitals = [bid for bid in order if id_to_b[bid].type_batiment == "hopital"]
    non_hospitals = [bid for bid in order if id_to_b[bid].type_batiment != "hopital"]

    # phase 0: those with zero infra
    phase_records = []
    # Phase 0: hôpitaux
    for bid in hospitals:
        phase_records.append((bid, 0))

    # Répartition par coût sur les non-hôpitaux
    total_cost = sum(pick_cost.get(bid, 0.0) for bid in non_hospitals)
    t1 = 0.40 * total_cost
    t2 = t1 + 0.20 * total_cost
    t3 = t2 + 0.20 * total_cost

    cum = 0.0
    for bid in non_hospitals:
        cost = pick_cost.get(bid, 0.0)
        if cum < t1:
            phase = 1
        elif cum < t2:
            phase = 2
        elif cum < t3:
            phase = 3
        else:
            phase = 4
        phase_records.append((bid, phase))
        cum += cost

    df = pd.DataFrame(phase_records, columns=["id_batiments", "phase"])
    # remove duplicates keeping first assignment (hospital/school over others)
    df = df.drop_duplicates(subset=["id_batiments"], keep="first")
    return df


def main() -> None:
    df = load_network_dataframe()
    infras = build_infras_from_df(df)
    buildings = group_infras_by_building(df, infras)

    # Filter out buildings with no infras before dynamic ordering
    buildings_with_infra = [b for b in buildings if len(b.list_infras) > 0]
    order, pick_cost, pick_metrics = select_order_with_repair(buildings_with_infra)
    phases_df = assign_phases(order, buildings, pick_cost)

    # Compute metrics for output columns
    rows = []
    id_to_b = {b.id_building: b for b in buildings}
    for _, row in phases_df.iterrows():
        bid = row["id_batiments"]
        phase = int(row["phase"])
        b = id_to_b[bid]
        metrics = pick_metrics.get(bid) or compute_building_cost_and_duration(b, workers_per_infra=4)
        nb_infra = len(b.list_infras)
        # nb maisons: take max across infras for this building (data repetition-safe)
        nb_maisons_vals = [infra.nb_houses for infra in b.list_infras]
        nb_maisons = max(nb_maisons_vals) if nb_maisons_vals else 0
        # Hospital safety check: require at least 20% margin within 20h autonomy
        hospital_ok = None
        margin_target_h = 20.0 * 0.8  # must finish within 16h to keep 20% buffer
        if b.type_batiment == "hopital":
            hospital_ok = metrics["duration_h"] <= margin_target_h
        rows.append({
            "id_batiments": bid,
            "phase": phase,
            "nb_infra": nb_infra,
            "nb_ouvriers": int(metrics["workers_total"]),
            "duree_heures": round(metrics["duration_h"], 2),
            "cout_euros": round(metrics["cost_eur"], 2),
            "nb_maisons": nb_maisons,
            "hopital_ok_marge_20pct": hospital_ok,
        })

    out_df = pd.DataFrame(rows, columns=[
        "id_batiments",
        "phase",
        "nb_infra",
        "nb_ouvriers",
        "duree_heures",
        "cout_euros",
        "nb_maisons",
        "hopital_ok_marge_20pct",
    ])
    out_df.to_csv("phases_plan.csv", index=False)
    print(f"CSV ecrit: phases_plan.csv ({len(out_df)} lignes)")


if __name__ == "__main__":
    main()


