"""Stable stratification without dependence on file order or Python hash seeds."""
import hashlib
from collections import defaultdict


def rank(record, seed, salt):
    return hashlib.sha256(f"{seed}|{salt}|{record.record_id}".encode()).hexdigest()


def stratified(records, count, seed, salt):
    groups = defaultdict(list)
    for record in records:
        groups[record.reference].append(record)
    for key in groups:
        groups[key].sort(key=lambda r: rank(r, seed, salt))
    selected = []
    while groups and len(selected) < count:
        for key in sorted(list(groups)):
            if len(selected) == count:
                break
            selected.append(groups[key].pop(0))
            if not groups[key]:
                del groups[key]
    return selected


def samples(records, config, profile, smoke_per_line=None):
    seed = config["seed"]
    selected_profile = config["profiles"][profile]
    full = config["profiles"]["full"]
    groups = defaultdict(list)
    for record in records:
        groups[record.reference].append(record)
    main, smoke, dropped = [], [], []
    for key, values in sorted(groups.items()):
        values.sort(key=lambda r: rank(r, seed, "main"))
        if profile == "full" and len(values) < full.get("minimum_eligible", 50):
            dropped.append({"template_line": key, "eligible_records": len(values)})
            continue
        # Reserve full sample even when smoking or running small.
        boundary = min(len(values), full["records_per_line"])
        smoke.extend(values[boundary:boundary + (smoke_per_line or 5)])
        main.extend(values[:min(selected_profile["records_per_line"], boundary)])
    if smoke_per_line is not None:
        main = smoke
        if not main:
            raise ValueError("No held-out smoke records; prepare more data or reduce full records_per_line before freezing")
    composite = stratified(main, min(len(main), selected_profile["composite_records"]), seed, "composite")
    # Use composite intersection for both repeated and shuffled comparisons across all methods.
    repeat = stratified(composite, selected_profile["repeat_records"], seed, "repeat")
    shuffle = stratified(composite, selected_profile["shuffle_records"], seed, "shuffle")
    return {"main": main, "composite": composite, "repeat": repeat, "shuffle": shuffle, "dropped": dropped}
