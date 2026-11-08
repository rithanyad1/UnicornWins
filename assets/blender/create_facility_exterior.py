"""Render the map's actual campus with its roof and exterior walls intact.

Run from the repository root with Blender --background --python this_file.py.
The cutaway scene and web model remain unchanged.
"""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/blender/facility-map-pixel.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene

# Reuse the campus geometry, palette, and lighting.
cream = bpy.data.materials['Meadow cream']
trim = bpy.data.materials['Lavender trim']
lavender = bpy.data.materials['Pale lavender']
blue = bpy.data.materials['Blue equipment panels']
purple = bpy.data.materials['Muted purple']
ink = bpy.data.materials['Ventilation wells']

# The home meadow supplies the land; keep the render's background transparent.
landscape = ('Green land', 'Green island', 'Meadow patch', 'Campus walkway',
             'Utility service apron', 'Service apron marking', 'Tree trunk',
             'Faceted cypress', 'Voxel tree', 'Pathway')
for obj in scene.objects:
    if obj.name.startswith(landscape):
        obj.hide_render = True


def box(name, location, dimensions, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    return obj


# Close the same rectangular server building and adjoining operations annex.
box('Exterior front wall', (0, -7.42, 1.8), (22.5, .38, 3.6), cream)
box('Exterior east wall', (11.02, 0, 1.8), (.38, 15, 3.6), cream)
box('Exterior back wall', (0, 7.42, 1.8), (22.5, .38, 3.6), cream)
box('Exterior west wall', (-11.02, 0, 1.8), (.38, 15, 3.6), cream)
box('Main roof fascia', (0, 0, 3.85), (23, 15.65, .4), trim)
box('Main roof surface', (0, 0, 4.09), (22.5, 15.15, .12), lavender)
box('Annex front exterior', (-14.04, -7.42, 1.5), (6.3, .38, 3), cream)
box('Annex west exterior', (-17.1, -3.06, 1.5), (.38, 8.8, 3), cream)
box('Annex back exterior', (-14.04, 1.26, 1.5), (6.3, .38, 3), cream)
box('Annex roof fascia', (-14.04, -3.06, 3.23), (6.7, 9.25, .35), trim)
box('Annex roof surface', (-14.04, -3.06, 3.45), (6.3, 8.85, .1), lavender)

# Glazing and an entrance identify the covered rooms without exposing the racks.
for x in (-9, -6, -3, 3, 6, 9):
    box('Front window frame', (x, -7.65, 2), (1.9, .12, 1.3), purple)
    box('Front window glass', (x, -7.73, 2), (1.65, .04, 1.05), blue)
    box('Front window mullion', (x, -7.77, 2), (.06, .03, 1.05), cream)
box('Main entrance frame', (0, -7.68, 1.25), (2, .18, 2.5), trim)
box('Main entrance glazing', (0, -7.8, 1.2), (1.65, .06, 2.25), blue)
box('Main entrance divider', (0, -7.85, 1.2), (.09, .03, 2.25), cream)
for y in (-5.5, -2.5, .1):
    box('Annex window frame', (-17.33, y, 1.65), (.12, 1.65, 1.2), trim)
    box('Annex window glass', (-17.41, y, 1.65), (.04, 1.4, .95), blue)

# Rooftop cooling uses the same cuboids and octagonal fans as the cutaway.
for x in (-6, 0, 6):
    box('Roof cooling unit', (x, 2.5, 4.55), (3.2, 2.7, .8), blue)
    box('Roof cooling cap', (x, 2.5, 5), (3.35, 2.85, .12), trim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.9, depth=.08, location=(x, 2.5, 5.12))
    bpy.context.object.name = 'Roof octagonal intake'
    bpy.context.object.data.materials.append(ink)
    for angle in (0, 1.5708):
        blade = box('Roof fan blade', (x, 2.5, 5.19), (1.4, .25, .06), cream)
        blade.rotation_euler.z = angle
    box('Roof fan hub', (x, 2.5, 5.26), (.35, .35, .14), purple)

camera = scene.camera
camera.location = (-3, -46, 17)
camera.rotation_euler = (Vector((-3, 0, 1.7)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.ortho_scale = 42
scene.render.resolution_x = 600
scene.render.resolution_y = 420
scene.render.resolution_percentage = 100
scene.cycles.samples = 32
scene.render.film_transparent = True
scene.render.filepath = str(ROOT / 'frontend/public/models/facility-exterior.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/blender/facility-exterior.blend'))
bpy.ops.render.render(write_still=True)
