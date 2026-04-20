# ifc_comparison

`ifc_comparison` is a starter repository for **IFC-based comparison and evaluation** of reconstructed BIMs against reference BIMs.

The intended use case is engineering-oriented assessment in 2D-to-BIM or floorplan-to-BIM workflows, where image-level metrics alone are not sufficient. Instead of evaluating only visual overlap, this repository is designed to support comparison at the **IFC element and parameter level**, with a focus on whether reconstructed building elements are correct in terms of:

- **dimensions**
- **placements**
- **host–opening relationships**

## Motivation

Many floorplan analysis methods report computer-vision metrics such as IoU, mAP, or F1, but these metrics do not directly indicate whether the reconstructed BIM is usable for engineering tasks. In BIM reconstruction, a result can look visually plausible while still containing incorrect element sizes, misplaced components, or invalid host relations.

This repository is therefore intended as a lightweight code base for comparing two IFC files:

- a **reference IFC** (ground truth / baseline / manually prepared BIM)
- a **reconstructed IFC** (predicted BIM)

and producing evaluation results that are closer to engineering expectations.

## Planned scope

The repository is intended to support workflows such as:

1. **IFC parsing**
   - load reference and reconstructed IFC files
   - extract comparable entities such as walls, openings, and spaces

2. **Element-level comparison**
   - compare geometric parameters such as length, thickness, width, and height
   - compare placements in the global or local coordinate system
   - check whether openings are hosted by the correct building elements

3. **Metric computation**
   - dimension-oriented accuracy
   - placement-oriented accuracy
   - host-relation validity
   - per-element logs for error inspection

4. **Case-level reporting**
   - export summary statistics
   - save per-sample comparison results
   - support error analysis for failed or partially matched cases

## Suggested repository structure

```text
ifc_comparison/
├─ README.md
├─ requirements.txt
├─ compare_ifc.py
├─ src/
│  ├─ io/
│  ├─ extraction/
│  ├─ matching/
│  ├─ metrics/
│  └─ reporting/
├─ examples/
│  ├─ reference.ifc
│  └─ prediction.ifc
└─ outputs/
```

## Example workflow

```bash
python compare_ifc.py \
  --reference examples/reference.ifc \
  --prediction examples/prediction.ifc \
  --output outputs/
```

A typical run may include:

- loading both IFC files
- extracting target entities
- matching comparable elements
- computing dimension, placement, and host-relation results
- exporting a summary report

## Notes

- This README is written as an **initial project description** for a currently empty repository.
- You can adapt the actual metric names, scripts, and folder structure once the implementation is finalized.
- If the project is aligned with an academic paper, it is recommended to keep the code terminology consistent with the paper terminology.

## Related research context

This repository is conceptually aligned with IFC-based engineering-oriented evaluation for automated BIM reconstruction, especially workflows that assess reconstructed BIM elements by **dimensions, placements, and host relations** rather than relying only on perception-oriented metrics.

## License

Add your preferred license here.
