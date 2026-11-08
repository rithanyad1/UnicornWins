"""Rebuild the Home meadow building as editable voxel geometry.

Run: blender --background --python assets/blender/create_meadow_building.py
The facade follows data-center-pixel.svg and the supplied building reference.
"""
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'frontend/public/models'
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def material(name, color):
    rgb = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = .9
    return mat


cream = material('Meadow cream', 'F4F7EA')
pale = material('Pale lavender trim', 'E1D8F0')
lavender = material('Lavender foundation', 'CDB9DD')
purple = material('Purple roof and drawers', '9580D4')
dark = material('Deep purple cabinets', '65509C')
blue = material('Sky blue equipment bays', 'B3D4E4')
status = material('Soft green indicators', 'D4E7A8')
roof = material('Muted lavender roof', 'B1A0C4')


def box(name, location, dimensions, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def facade(name, x, top, width, height, mat, front=0, depth=.1):
    """Use reference pixel coordinates for front-facing cuboids; +Y goes back."""
    return box(name, ((x + width / 2) / 10, front + depth / 2,
                      (89 - top - height / 2) / 10),
               (width / 10, depth, height / 10), mat)


# Same low, wide silhouette as the reference, with a recessed service wing.
facade('Main hall / cream shell', 14, 35, 90, 52, cream, depth=4.2)
facade('Main hall / lavender foundation', 14, 83, 90, 6, lavender, front=-.02, depth=4.25)
facade('Main hall / roof slab', 10, 29, 98, 6, purple, front=-.25, depth=4.7)
facade('Main hall / roof surface', 14, 27, 90, 2, pale, depth=4.2)
facade('Main hall / fascia shadow', 14, 35, 90, 4, lavender, front=-.03)
facade('Service wing / cream shell', 102, 45, 30, 42, cream, front=.4, depth=3.4)
facade('Service wing / foundation', 102, 83, 30, 6, lavender, front=.37, depth=3.45)
facade('Service wing / roof cap', 102, 39, 34, 6, purple, front=.15, depth=3.9)
facade('Service wing / roof surface', 104, 37, 28, 2, pale, front=.4, depth=3.4)
facade('Service wing / fascia shadow', 104, 45, 28, 4, lavender, front=.37)

# Three raised cooling modules: square housings and distinctive pixel cross fans.
for index, x in enumerate((24, 50, 76), 1):
    label = f'Rooftop cooling {index}'
    facade(label + ' / plinth', x + 2, 27, 18, 4, purple, front=.35, depth=1.8)
    facade(label + ' / housing', x, 15, 22, 14, pale, front=.45, depth=1.5)
    facade(label + ' / raised lid', x + 4, 11, 14, 4, pale, front=.45, depth=1.5)
    facade(label + ' / blue inset', x + 4, 15, 14, 12, blue, front=.41)
    facade(label + ' / fan center', x + 4, 17, 14, 6, dark, front=.36)
    facade(label + ' / fan vertical', x + 8, 15, 6, 12, dark, front=.36)
    facade(label + ' / blade vertical', x + 10, 17, 2, 8, lavender, front=.32)
    facade(label + ' / blade horizontal', x + 6, 20, 10, 2, lavender, front=.32)
    for row in range(3):
        box(label + ' / side louver', ((x + 22) / 10 + .01, 1.05, 6.25 + row * .26), (.03, .75, .09), purple)

# One continuous blue equipment bay and four six-drawer server racks.
facade('Hall / ventilation inset', 20, 41, 78, 4, blue, front=-.025)
for x in range(22, 98, 6):
    facade('Hall / ventilation fin', x, 41, 2, 4, purple, front=-.07)
facade('Hall / recessed blue equipment bay', 20, 49, 78, 30, blue, front=-.025)
facade('Hall / equipment sill', 20, 79, 78, 2, pale, front=-.07)
for index, x in enumerate((24, 42, 60, 78), 1):
    facade(f'Rack {index} / cabinet', x, 51, 14, 26, dark, front=-.16, depth=.2)
    for row in range(6):
        facade(f'Rack {index} / drawer {row + 1}', x + 2, 53 + row * 4, 10, 2, purple, front=-.2)
        facade(f'Rack {index} / LED {row + 1}', x + 10, 53 + row * 4, 2, 2,
               blue if (row + index) % 3 == 1 else status, front=-.23, depth=.04)

# Service entrance, card reader, bent conduits, and a shallow entrance step.
facade('Entry / surround', 106, 57, 14, 28, pale, front=.29, depth=.2)
facade('Entry / blue door', 108, 59, 10, 26, blue, front=.25)
facade('Entry / purple window', 110, 61, 6, 6, dark, front=.2)
facade('Entry / handle', 114, 75, 2, 2, purple, front=.17)
facade('Entry / canopy', 104, 53, 18, 4, purple, front=-.05, depth=.9)
facade('Entry / card reader', 122, 63, 4, 6, dark, front=.26)
facade('Entry / reader light', 123, 64, 2, 2, status, front=.21)
facade('Entry / step', 108, 89, 12, 2, cream, front=-.05, depth=1)
for x, top, width, height in [(124, 27, 2, 10), (128, 29, 2, 8), (120, 25, 6, 2), (124, 27, 6, 2)]:
    facade('Utility conduit', x, top, width, height, lavender, front=2, depth=.2)

# The two standalone ground units keep their positions in the reference.
facade('Backup power / cabinet', 4, 73, 14, 16, pale, front=-.45, depth=1.3)
facade('Backup power / top', 2, 71, 18, 4, purple, front=-.55, depth=1.5)
for top in (77, 81, 85):
    facade('Backup power / blue grille', 6, top, 10, 2, blue, front=-.5)
facade('Outdoor cooling / housing', 126, 73, 14, 16, pale, front=-.45, depth=1.3)
facade('Outdoor cooling / footing', 126, 87, 14, 2, lavender, front=-.5, depth=1.4)
facade('Outdoor cooling / fan horizontal', 128, 77, 10, 6, purple, front=-.5)
facade('Outdoor cooling / fan vertical', 130, 75, 6, 10, purple, front=-.5)
facade('Outdoor cooling / blade vertical', 132, 77, 2, 6, blue, front=-.55)
facade('Outdoor cooling / blade horizontal', 130, 79, 6, 2, blue, front=-.55)
# Small repeating grilles on the newly visible right wall add depth without branding.
for y in (1.15, 2.15, 3.15):
    box('Service wing / side equipment panel', (13.205, y, 2.2), (.04, .65, 1.65), blue)
    for z in (1.65, 1.95, 2.25, 2.55):
        box('Service wing / side grille', (13.235, y, z), (.04, .5, .08), purple)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 432
scene.render.resolution_y = 312
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.filter_size = .1
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .82, .9, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
bpy.ops.object.light_add(type='AREA', location=(-3, -10, 18))
bpy.context.object.name = 'Soft meadow daylight'
bpy.context.object.data.energy = 2200
bpy.context.object.data.size = 10
bpy.ops.object.camera_add(location=(16, -27, 16))
camera = bpy.context.object
camera.name = 'Meadow exterior orthographic camera'
camera.rotation_euler = (Vector((7.1, 1.2, 4)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 17.8
scene.camera = camera
scene.render.filepath = str(OUTPUT / 'meadow-data-center.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/blender/meadow-data-center.blend'))
bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'meadow-data-center.glb'), export_format='GLB', use_selection=True, export_cameras=False, export_lights=False)
print('Reference meadow building: editable Blender scene, transparent render and GLB saved.')
