from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import numpy as np


DEFAULT_GT_PATH = Path("comparison/0_GT.ifc")
DEFAULT_GENERATED_PATH = Path("comparison/0_generated.ifc")
ROUND_DIGITS = 6
POSITION_TOLERANCE = 50.0


@dataclass(frozen=True)
class BaselineRecord:
    category: str
    length: float
    start: tuple[float, float]
    end: tuple[float, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare GT IFC and generated IFC using wall/opening baselines and "
            "opening-void relationships."
        )
    )
    parser.add_argument(
        "--gt",
        type=Path,
        default=DEFAULT_GT_PATH,
        help=f"Ground-truth IFC path. Default: {DEFAULT_GT_PATH}",
    )
    parser.add_argument(
        "--generated",
        type=Path,
        default=DEFAULT_GENERATED_PATH,
        help=f"Generated IFC path. Default: {DEFAULT_GENERATED_PATH}",
    )
    return parser.parse_args()


def rounded(value: float) -> float:
    return round(float(value), ROUND_DIGITS)


def rounded_point(point: np.ndarray) -> tuple[float, float]:
    return (rounded(point[0]), rounded(point[1]))


def make_geom_settings() -> ifcopenshell.geom.settings:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    return settings


def get_world_matrix_si(model: ifcopenshell.file, placement: ifcopenshell.entity_instance) -> np.ndarray:
    unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    matrix = ifcopenshell.util.placement.get_local_placement(placement).copy()
    matrix[:3, 3] *= unit_scale
    return matrix


def get_wall_baseline_record(model: ifcopenshell.file, wall: ifcopenshell.entity_instance) -> BaselineRecord | None:
    if not wall.Representation:
        return None

    axis_representation = None
    for representation in wall.Representation.Representations or []:
        if representation.RepresentationIdentifier == "Axis":
            axis_representation = representation
            break
    if axis_representation is None or not axis_representation.Items:
        return None

    axis_item = axis_representation.Items[0]
    if not axis_item.is_a("IfcPolyline"):
        return None

    points = axis_item.Points
    if len(points) < 2:
        return None

    p0_local = np.array([float(points[0].Coordinates[0]), float(points[0].Coordinates[1]), 0.0, 1.0])
    p1_local = np.array([float(points[-1].Coordinates[0]), float(points[-1].Coordinates[1]), 0.0, 1.0])
    matrix = get_world_matrix_si(model, wall.ObjectPlacement)
    p0_world = (matrix @ p0_local)[:3]
    p1_world = (matrix @ p1_local)[:3]
    length = float(np.linalg.norm(p1_world[:2] - p0_world[:2]))

    return BaselineRecord(
        category="wall",
        length=rounded(length),
        start=rounded_point(p0_world[:2]),
        end=rounded_point(p1_world[:2]),
    )


def opening_local_bbox_si(
    model: ifcopenshell.file,
    opening: ifcopenshell.entity_instance,
    geom_settings: ifcopenshell.geom.settings,
) -> tuple[np.ndarray, np.ndarray]:
    shape = ifcopenshell.geom.create_shape(geom_settings, opening)
    verts_world = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    placement = get_world_matrix_si(model, opening.ObjectPlacement)
    inverse = np.linalg.inv(placement)
    verts_local = (inverse @ np.c_[verts_world, np.ones(len(verts_world))].T).T[:, :3]
    return verts_local.min(axis=0), verts_local.max(axis=0)


def get_opening_category_by_fill(model: ifcopenshell.file) -> dict[int, str]:
    categories: dict[int, str] = {}
    for rel in model.by_type("IfcRelFillsElement"):
        opening = rel.RelatingOpeningElement
        fill = rel.RelatedBuildingElement
        if fill.is_a("IfcDoor"):
            categories[opening.id()] = "door"
        elif fill.is_a("IfcWindow"):
            categories[opening.id()] = "window"
    return categories


def get_opening_baseline_record(
    model: ifcopenshell.file,
    opening: ifcopenshell.entity_instance,
    category: str,
    geom_settings: ifcopenshell.geom.settings,
) -> BaselineRecord | None:
    minimum, maximum = opening_local_bbox_si(model, opening, geom_settings)
    center_y = (minimum[1] + maximum[1]) * 0.5

    start_local = np.array([minimum[0], center_y, minimum[2], 1.0])
    end_local = np.array([maximum[0], center_y, minimum[2], 1.0])
    matrix = get_world_matrix_si(model, opening.ObjectPlacement)
    start_world = (matrix @ start_local)[:3]
    end_world = (matrix @ end_local)[:3]
    length = float(np.linalg.norm(end_world[:2] - start_world[:2]))

    return BaselineRecord(
        category=category,
        length=rounded(length),
        start=rounded_point(start_world[:2]),
        end=rounded_point(end_world[:2]),
    )


def normalize_records(records: list[BaselineRecord]) -> list[BaselineRecord]:
    if not records:
        return []
    xmin = min(min(record.start[0], record.end[0]) for record in records)
    ymin = min(min(record.start[1], record.end[1]) for record in records)

    normalized: list[BaselineRecord] = []
    for record in records:
        normalized.append(
            BaselineRecord(
                category=record.category,
                length=record.length,
                start=(rounded(record.start[0] - xmin), rounded(record.start[1] - ymin)),
                end=(rounded(record.end[0] - xmin), rounded(record.end[1] - ymin)),
            )
        )
    return normalized


def collect_records(
    model: ifcopenshell.file,
) -> tuple[list[BaselineRecord], list[BaselineRecord], list[BaselineRecord]]:
    geom_settings = make_geom_settings()
    wall_records: list[BaselineRecord] = []
    opening_records: list[BaselineRecord] = []
    opening_has_void_flags: list[bool] = []

    for wall in model.by_type("IfcWall"):
        record = get_wall_baseline_record(model, wall)
        if record is not None:
            wall_records.append(record)

    opening_categories = get_opening_category_by_fill(model)
    openings_with_voids = {rel.RelatedOpeningElement.id() for rel in model.by_type("IfcRelVoidsElement")}
    for opening in model.by_type("IfcOpeningElement"):
        category = opening_categories.get(opening.id())
        if category is None:
            continue
        record = get_opening_baseline_record(model, opening, category, geom_settings)
        if record is None:
            continue
        opening_records.append(record)
        opening_has_void_flags.append(opening.id() in openings_with_voids)

    all_records = wall_records + opening_records
    normalized_all_records = normalize_records(all_records)
    normalized_walls = normalized_all_records[: len(wall_records)]
    normalized_openings = normalized_all_records[len(wall_records) :]

    normalized_opening_void_records = [
        record
        for record, has_void in zip(normalized_openings, opening_has_void_flags)
        if has_void
    ]

    return normalized_walls, normalized_openings, normalized_opening_void_records


def counter_by_category_and_length(records: list[BaselineRecord]) -> Counter:
    return Counter((record.category, record.length) for record in records)


def counter_exact(records: list[BaselineRecord]) -> Counter:
    return Counter(records)


def count_matches(gt_counter: Counter, generated_counter: Counter) -> dict[str, int]:
    result = {"wall": 0, "door": 0, "window": 0}
    for key, gt_count in gt_counter.items():
        category = key[0] if isinstance(key, tuple) else key.category
        result[category] += min(gt_count, generated_counter.get(key, 0))
    return result


def points_within_tolerance(
    point_a: tuple[float, float],
    point_b: tuple[float, float],
    tolerance: float,
) -> bool:
    return (
        abs(point_a[0] - point_b[0]) <= tolerance
        and abs(point_a[1] - point_b[1]) <= tolerance
    )


def directionally_consistent(gt_record: BaselineRecord, gen_record: BaselineRecord) -> bool:
    gt_vector = np.array(
        [gt_record.end[0] - gt_record.start[0], gt_record.end[1] - gt_record.start[1]],
        dtype=float,
    )
    gen_vector = np.array(
        [gen_record.end[0] - gen_record.start[0], gen_record.end[1] - gen_record.start[1]],
        dtype=float,
    )
    gt_norm = float(np.linalg.norm(gt_vector))
    gen_norm = float(np.linalg.norm(gen_vector))
    if gt_norm == 0.0 or gen_norm == 0.0:
        return gt_norm == gen_norm
    return float(np.dot(gt_vector, gen_vector) / (gt_norm * gen_norm)) > 0.0


def count_tolerant_matches(
    gt_records: list[BaselineRecord],
    generated_records: list[BaselineRecord],
    tolerance: float,
) -> dict[str, int]:
    result = {"wall": 0, "door": 0, "window": 0}
    used_generated: set[int] = set()

    for gt_record in gt_records:
        for index, gen_record in enumerate(generated_records):
            if index in used_generated:
                continue
            if gt_record.category != gen_record.category:
                continue
            if gt_record.length != gen_record.length:
                continue
            if not points_within_tolerance(gt_record.start, gen_record.start, tolerance):
                continue
            if not points_within_tolerance(gt_record.end, gen_record.end, tolerance):
                continue
            if not directionally_consistent(gt_record, gen_record):
                continue
            used_generated.add(index)
            result[gt_record.category] += 1
            break

    return result


def category_totals(records: list[BaselineRecord]) -> dict[str, int]:
    totals = {"wall": 0, "door": 0, "window": 0}
    for record in records:
        totals[record.category] += 1
    return totals


def print_section(title: str, gt_totals: dict[str, int], matched: dict[str, int]) -> None:
    print(title)
    print(f"  walls:   {matched['wall']} / {gt_totals['wall']}")
    print(f"  doors:   {matched['door']} / {gt_totals['door']}")
    print(f"  windows: {matched['window']} / {gt_totals['window']}")


def main() -> None:
    args = parse_args()
    if not args.gt.exists():
        raise FileNotFoundError(f"GT IFC not found: {args.gt}")
    if not args.generated.exists():
        raise FileNotFoundError(f"Generated IFC not found: {args.generated}")

    gt_model = ifcopenshell.open(str(args.gt))
    generated_model = ifcopenshell.open(str(args.generated))

    gt_walls, gt_openings, gt_opening_voids = collect_records(gt_model)
    gen_walls, gen_openings, gen_opening_voids = collect_records(generated_model)

    gt_all = gt_walls + gt_openings
    gen_all = gen_walls + gen_openings

    gt_totals = category_totals(gt_all)

    length_matches = count_tolerant_matches(
        gt_all,
        gen_all,
        tolerance=POSITION_TOLERANCE,
    )
    exact_matches = count_matches(
        counter_exact(gt_all),
        counter_exact(gen_all),
    )

    gt_opening_totals = category_totals(gt_openings)
    void_matches = count_matches(
        counter_exact(gt_openings),
        counter_exact(gen_opening_voids),
    )

    print(f"GT file:        {args.gt}")
    print(f"Generated file: {args.generated}")
    print()
    print_section(
        f"(1) Type + Baseline Length + Normalized Start/End Within {POSITION_TOLERANCE:g}",
        gt_totals=gt_totals,
        matched=length_matches,
    )
    print()
    print_section(
        "(2) Type + Length + Normalized Start/End",
        gt_totals=gt_totals,
        matched=exact_matches,
    )
    print()
    print("(3) Opening Has IfcRelVoidsElement")
    print(f"  doors:   {void_matches['door']} / {gt_opening_totals['door']}")
    print(f"  windows: {void_matches['window']} / {gt_opening_totals['window']}")
    print(
        f"  total:   {void_matches['door'] + void_matches['window']} / "
        f"{gt_opening_totals['door'] + gt_opening_totals['window']}"
    )


if __name__ == "__main__":
    main()
