# Monorail Train Model Specifications

## Base Unit
- **Grid Size**: 5.0 units (this is the fundamental unit of measurement in the game world)

## Train Car Dimensions (Each of 4 cars)

### Main Car Body
- **Length**: 5.0 units (100% of grid size)
- **Width**: 5.0 units (100% of grid size)
- **Height**: 3.0 units (60% of grid size)
- **Shape**: Rectangular prism (cube-based footprint to match platform)

### Car Connections (3 connection pieces between 4 cars)
- **Length**: 0.0 units (Cars flush against each other for square snapping)
- **Height**: 2.0 units (approx 66% of car height)
- **Width**: 2.5 units (50% of car width)
- **Position**: Between each pair of cars (internal/recessed)

## Overall Train Dimensions

### Total Length
- **Length**: 20.0 units
  - 4 cars × 5.0 units = 20.0 units
  - 3 connections × 0.0 units = 0.0 units
  - Total = 20.0 units

### Width
- **Maximum Width**: 5.0 units (car width)

### Height
- **Maximum Height**: 3.0 units (car height)

## Summary for 3D Modeler

**Train Composition:**
- 4 identical train cars
- 3 connection pieces (zero length, used for internal structure)

**Each Train Car:**
- Dimensions: 5.0 × 5.0 × 3.0 units (Length × Width × Height)
- Shape: Rectangular prism with square base. Top part may have rounded/beveled edges, but the bottom face MUST be a 5.0 x 5.0 square to match the platforms.

**Each Connection Piece:**
- Dimensions: 0.0 × 2.5 × 2.0 units (Length × Width × Height)
- Position: Internal between cars.

**Total Train Length:** 20.0 units

**Color:** Green (RGB: 0, 255, 0) - solid color, no texture

**Orientation:** Train can be placed horizontally (along X-axis) or vertically (along Z-axis), but dimensions remain the same relative to the train's local coordinate system.

## Notes
- The train sits on top of stool surfaces (which are 5.0 × 5.0 units square)
- The train car base dimensions (5.0 x 5.0) exactly match the platform surfaces.
- The train spans exactly 4 grid squares (4 × 5.0 = 20 units)
- The model should be designed to be modular - the 4 cars should be separate or easily separable components
- All measurements are in game world units (not necessarily real-world measurements unless specified otherwise)

