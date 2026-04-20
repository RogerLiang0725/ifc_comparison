# ifc_comparison

`ifc_comparison` provides a lightweight prototype for **IFC-based engineering-oriented comparison** between a reference BIM and a reconstructed BIM.

The current implementation is aligned with the three IFC-based evaluation criteria defined in the manuscript: **dimension accuracy** (`A_dim`), **placement accuracy** (`A_place`), and **host-relation accuracy** (`A_host`). In this repository, these criteria are operationalized through direct comparison of IFC-derived wall and opening representations rather than image-level overlap metrics. The manuscript defines these three criteria as element-level correctness in terms of **metric extent**, **dimension-plus-placement consistency**, and **opening–host relations**, respectively. fileciteturn3file1

## Current scope

At present, the repository contains a comparison script, `ifc_comparison.py`, that evaluates two IFC files by extracting comparable wall and opening records and checking them under three engineering-oriented criteria. The script loads a ground-truth IFC and a generated IFC, extracts wall baselines from `IfcWall` axis representations, extracts opening baselines from `IfcOpeningElement`, and uses `IfcRelVoidsElement` and `IfcRelFillsElement` to identify opening categories and void-host relations. fileciteturn2file1 fileciteturn2file2

## IFC-based criteria implemented in the current script

### 1. Dimension accuracy (`A_dim`)
This criterion evaluates whether a reconstructed element preserves the correct metric extent. Consistent with the manuscript, the core concern is whether the reconstructed element matches the ground-truth element in its geometric magnitude. In the current code, this is approximated through element-type-aware baseline comparison, where wall and opening records are compared by category and baseline length after normalization into a shared local coordinate frame. fileciteturn3file1 fileciteturn2file3

### 2. Placement accuracy (`A_place`)
This criterion is stricter than `A_dim` and requires the reconstructed element to be correct in both dimension and geometric placement. In the manuscript, `A_place` requires dimensional agreement together with positional agreement in a unified coordinate system. In the current script, this is reflected by comparing normalized baseline start and end points, together with direction consistency, after both IFC models are transformed into a comparable local frame. A tolerant matching mode is also provided in the script to support position checks within a predefined threshold. fileciteturn3file1 fileciteturn2file3

### 3. Host-relation accuracy (`A_host`)
This criterion evaluates whether openings are assigned to the correct host walls. The manuscript defines this metric through IFC relational records of type `IfcRelVoidsElement`. In the current implementation, opening-related records are filtered by fill type (`IfcDoor` / `IfcWindow`), and the script checks whether the compared opening participates in a valid `IfcRelVoidsElement` relation. This serves as the current repository-level implementation of host-aware opening validation. fileciteturn3file1 fileciteturn2file2

## Current implementation details

The current code uses the following comparison logic:

- **Walls** are represented by the baseline extracted from the `Axis` representation of `IfcWall`, using the corresponding `IfcPolyline` in world coordinates. fileciteturn2file1
- **Openings** are represented by a baseline derived from the local bounding box of each `IfcOpeningElement`, converted to world coordinates through the opening placement matrix. fileciteturn2file2
- **Normalization** is performed by translating all extracted records into a shared local frame using the lower-left corner of the compared layout extent, which is consistent with the manuscript’s use of a unified coordinate system for IFC comparison. fileciteturn2file2 fileciteturn3file1
- **Host-aware checking** currently relies on the presence of `IfcRelVoidsElement` for opening-related validation. fileciteturn2file2

## Usage

```bash
python ifc_comparison.py \
  --gt comparison/0_GT.ifc \
  --generated comparison/0_generated.ifc
```

The script currently prints three comparison sections:

1. a tolerance-based comparison for type, baseline length, and normalized start/end positions
2. an exact comparison for type, length, and normalized start/end positions
3. an opening-relation check based on `IfcRelVoidsElement` 

These outputs correspond to the current code-level implementation of the three engineering-oriented IFC comparison aspects. fileciteturn2file0

## Notes

This repository is intended to support engineering-oriented BIM evaluation in dimension-aware 2D-to-BIM reconstruction workflows. The current implementation is a practical comparison script built around wall baselines, opening baselines, and IFC host relations, and it reflects the core evaluation direction of the manuscript rather than a complete final benchmark package. The manuscript explicitly frames the engineering-oriented assessment around **dimensions**, **placements**, and **host relations**, which this repository follows. fileciteturn3file1

**Other code is being prepared for upload.**
