# UN1C0RN^2 meadow data center

## Pixel facility map

`facility-map-pixel.blend` is the editable, expanded open-roof campus for the
facility map and digital twin. It contains two server halls with 24 racks,
network operations, power and cooling, an operations annex, and surrounding
green land with geometric trees, walking paths and a service apron. The scene
keeps the cream, blue and lavender palette, with no branding or text.

The website loads `frontend/public/models/facility-campus.glb` into Three.js.
Drag to orbit; Shift-drag, right-drag or Pan mode moves the view. Scroll or use
the zoom buttons to zoom. Reset restores the initial view, and Expand opens a
larger workspace. Arrow keys rotate, + / − zoom, 0 resets, and Escape closes the
expanded view. Reduced-motion settings disable inertial camera movement.

The transparent 480 × 336 PNG is a fallback when WebGL or model loading is
unavailable. The interactive view renders at 85% of the canvas's CSS dimensions
with crisp pixel scaling and no antialiasing for a fine pixel texture that keeps
room details clear. Labels remain at full resolution. A matching grass plane extends
beyond the viewport and follows the camera target so the land has no visible
edge while rotating, zooming or panning. The frontend adds Blender-modeled voxel unicorns along the clear corridor and campus paths. While they walk, their legs and tails animate continuously; Pause team restores rendering on camera, model or size
changes only. Reduced-motion preferences start the team paused. Names and
appearance colors are configured in `frontend/src/lib/team-members.ts`.

```sh
blender --background --python assets/blender/create_facility_map.py
```

This generates the `.blend`, `.glb`, fallback `.png` and
`frontend/src/lib/facility-map-layout.json`. The JSON includes both static image
coordinates and 3D anchors. Live markers project through the interactive camera
so they follow the rooms during dragging. Re-run the script after changing the
camera or room positions. The Blender file keeps individual editable objects;
the GLB merges meshes by material to limit browser draw calls.

## Reference building exterior

`meadow-data-center.blend` recreates the Home building reference with the same
voxel modeling, orthographic camera and soft daylight used by the campus. It
keeps the three rooftop cross fans, four six-drawer server racks, blue equipment
bay, low service wing, card reader, utility conduits and two ground units. Each
part is named and individually editable, with no textures or font dependencies.

Home uses `frontend/public/models/meadow-data-center.png`, the cream and
lavender Blender exterior, to share the facility map’s materials and voxel
style. The matching `meadow-data-center.glb` remains available as a 3D option.
The earlier graphite facade is retained as `data-center-gray.svg`.
The original lavender reference is retained as `data-center-pixel.svg`.

```sh
blender --background --python assets/blender/create_meadow_building.py
```

This rebuilds the `.blend`, `.png` and `.glb` together.

## Original exterior option

`sentinel-data-center.blend` is the editable Blender scene for the original 3D option.
The scene contains the server hall, control wing, rooftop cooling, outdoor
chillers, server cabinets, voxel planting, pixel signage, camera and lights.
Everything is modeled geometry with named materials; no external textures are
needed.

Its transparent render is `frontend/public/models/sentinel-data-center.png`,
at 256 × 224 pixels. The current Home page uses the reference building render described above.
This original Blender source and render are retained as an optional 3D variant.

To rebuild the scene and render with Blender 4.5, run from the repository root:

```sh
blender --background --python assets/blender/create_data_center.py
```

The script replaces the generated `.blend` and `.png`. Edit the script to make
reproducible model changes, or open the `.blend` in Blender for manual editing.

## Unicorn NPCs

`unicorn-npcs.blend` contains four editable voxel unicorns using the campus's
cream, lavender and blue materials, flat faces and stepped cuboid details.
Each has a golden pyramid horn and rose, lavender, mint or peach accents.
The frontend loads `unicorn-npcs.glb` and animates the separate leg and tail
pivots along the existing routes. The models face their direction of travel
and remain three-dimensional while orbiting the campus.

```sh
blender --background --python assets/blender/create_unicorn_npcs.py
```

This rebuilds the editable `.blend`, optimized `.glb` and a transparent
`unicorn-npcs-preview.png` lineup. Names, variants and routes are configured
in `frontend/src/lib/team-members.ts`.

### Cover unicorns

The cover uses walking and grazing atlases rendered directly from the same
`unicorn-npcs.blend` models as the map, with four palettes and four poses.
The existing meadow movement and reduced-motion behavior are preserved.

```sh
blender --background --python assets/blender/render_cover_unicorns.py
```

This produces `unicorn-voxel-walk-atlas.png` and
`unicorn-voxel-graze-atlas.png`. The cover meadow uses the map's softer sage
grass palette alongside the cream-and-lavender exterior render.

## Covered campus entrance

`facility-exterior.blend` uses the actual `facility-map-pixel.blend` campus with
full exterior walls, main and annex roofs, and matching rooftop cooling units.
Its transparent `frontend/public/models/facility-exterior.png` render appears on
the home meadow's horizon. The entrance button opens the original uncovered interactive map. The map source and GLB are unchanged.

Regenerate with Blender in background mode:

```sh
blender --background --python assets/blender/create_facility_exterior.py
```
