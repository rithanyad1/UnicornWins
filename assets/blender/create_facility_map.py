"""Generate the pixel facility cutaway and matching clickable room coordinates.

From the repository root:
  blender --background --python assets/blender/create_facility_map.py
"""
import json
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
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
    shader.inputs['Roughness'].default_value = 1
    return mat


cream = material('Meadow cream', 'F4F7EA')
lavender = material('Pale lavender', 'E1D8F0')
trim = material('Lavender trim', 'CDB9DD')
purple = material('Muted purple', '9580D4')
rack_material = material('Server cabinets', '65509C')
rack_front = material('Server drawers', '84769C')
ink = material('Ventilation wells', '554C65')
blue = material('Blue equipment panels', 'B3D4E4')
water = material('Water sensor zone', '91BDCC')
green = material('Normal indicator', 'BCDFA8')
warning = material('Incident indicator', 'D8A1A7')


def box(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def fan(x, y, z, name):
    box(name + ' fan surround', (x, y, z), (.8, .8, .08), trim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.32, depth=.06, location=(x, y, z + .06))
    obj = bpy.context.object
    obj.name = name + ' octagonal intake'
    obj.data.materials.append(ink)
    for rotation in (0, 1.5708):
        blade = box(name + ' blades', (x, y, z + .11), (.48, .09, .025), blue)
        blade.rotation_euler.z = rotation
    box(name + ' hub', (x, y, z + .15), (.13, .13, .08), cream)


def rack(x, y, name, alert=False, height=1.55):
    box(name + ' base', (x, y, .16), (.91, .85, .16), trim)
    box(name + ' cabinet', (x, y, height / 2 + .18), (.76, .7, height), rack_material)
    box(name + ' top', (x, y, height + .21), (.76, .7, .08), lavender)
    for row in range(5):
        z = .4 + row * (height - .25) / 5
        box(name + ' drawer', (x, y - .36, z), (.64, .035, .15), rack_front)
        box(name + ' LED', (x + .22, y - .39, z), (.07, .03, .065), warning if alert else green)
    for side in (-1, 1):
        box(name + ' door rail', (x + side * .34, y - .39, height / 2 + .18), (.045, .04, height), lavender)


# Four distinct operational zones, exposed by low cutaway walls.
box('Foundation', (0, 0, -.2), (12.8, 8.8, .4), trim)
box('Foundation cream lip', (0, 0, -.02), (12.6, 8.6, .12), cream)
for name, x, y, mat in [('A / Server hall', -3, 2.2, lavender), ('B / Server hall', 3, 2.2, cream), ('C / Network operations', -3, -2.2, cream), ('D / Power and cooling', 3, -2.2, lavender)]:
    box(name + ' floor', (x, y, .07), (5.7, 3.35, .08), mat)
# Raised-floor seams are geometry, aligned to a consistent voxel grid.
for x in range(-6, 7):
    box('Raised floor seam X', (x, 0, .12), (.022, 8.1, .012), trim)
for y in range(-4, 5):
    box('Raised floor seam Y', (0, y, .12), (12.1, .022, .012), trim)
box('Back cutaway wall', (0, 4.12, .95), (12.4, .2, 1.8), cream)
box('Back wall cap', (0, 4.12, 1.89), (12.5, .26, .12), trim)
box('Left cutaway wall', (-6.12, 0, .62), (.2, 8.3, 1.15), cream)
box('Left wall cap', (-6.12, 0, 1.23), (.26, 8.3, .12), trim)
box('Right cutaway wall', (6.12, 0, .35), (.2, 8.3, .6), cream)
box('Front cutaway sill', (0, -4.12, .22), (12.4, .2, .35), cream)
box('Server room divider', (0, 2.3, .68), (.18, 3.6, 1.15), cream)
box('Utility room divider', (0, -2.3, .43), (.18, 3.6, .65), cream)
# Door gaps preserve a visible circulation route.
for y in (-.55, .55):
    for x in (-4.6, -.9, .9, 4.6):
        box('Corridor half wall', (x, y, .38), (2.3 if abs(x) > 2 else .75, .15, .52), cream)
box('Central circulation path', (0, 0, .145), (11.8, .72, .025), blue)
for x in (-4, -2, 0, 2, 4):
    box('Corridor route pixels', (x, 0, .17), (.28, .09, .025), cream)

# Two server halls with repeating rows and clearly visible rack fronts.
for hall, xs in [('A', (-5, -3.7, -2.4, -1.1)), ('B', (1.1, 2.4, 3.7, 5))]:
    for row, y in enumerate((1.05, 2.15, 3.25)):
        for col, x in enumerate(xs):
            rack(x, y, f'{hall} rack {row * 4 + col + 1}', alert=hall == 'A' and row == 0 and col == 1)
# Overhead cable trunks along the back walls.
box('Hall A cable trunk', (-3.25, 3.8, 1.25), (5.1, .2, .2), purple)
box('Hall B cable trunk', (3, 3.8, 1.25), (5.1, .2, .2), blue)
for x in (-5.3, -2.8, 2, 4.4):
    box('Cable trunk riser', (x, 3.8, .72), (.15, .2, 1), trim)

# Network operations: shorter switches and a console desk.
for i, x in enumerate((-4.8, -3.5, -2.2)):
    rack(x, -2.9, f'C network cabinet {i + 1}', height=1.15)
box('Network console desk', (-2.5, -1.25, .73), (3.5, .8, .18), trim)
for x in (-3.7, -1.3):
    box('Console desk leg', (x, -1.25, .4), (.16, .5, .65), cream)
for x in (-3.6, -2.5, -1.4):
    box('Console display', (x, -1.18, 1.2), (.8, .12, .57), rack_material)
    box('Console screen', (x, -1.25, 1.2), (.65, .025, .4), blue)
    box('Display stand', (x, -1.18, .91), (.09, .13, .18), purple)
    box('Console keyboard', (x, -1.52, .84), (.52, .2, .04), lavender)
box('Operator stool', (-2.5, -2.1, .46), (.5, .5, .2), purple)
box('Operator stool base', (-2.5, -2.1, .24), (.15, .15, .4), trim)

# Power cabinets and redundant cooling: fans, vents, and visible pipework.
for x in (1.15, 2.35):
    box('UPS enclosure', (x, -1.6, .88), (.87, .9, 1.5), cream)
    box('UPS front panel', (x, -2.07, .95), (.65, .04, .85), lavender)
    box('UPS status display', (x, -2.1, 1.15), (.38, .025, .2), blue)
    for z in (.48, .61, .74):
        box('UPS ventilation', (x, -2.11, z), (.52, .03, .045), purple)
for y in (-1.45, -2.85):
    box('Cooling housing', (4.65, y, .66), (1.25, 1.15, 1.05), blue)
    fan(4.65, y, 1.23, 'Redundant cooling')
    for z in (.35, .5, .65, .8):
        box('Cooling intake grille', (4.65, y - .59, z), (.94, .035, .055), rack_material)
box('Cooling supply pipe', (5.65, -2.2, .5), (.14, 3.4, .14), trim)
box('Cooling return pipe', (5.9, -2.2, .7), (.14, 3.4, .14), purple)
for y in (-1.45, -2.85):
    box('Cooling branch', (5.35, y, .5), (.6, .13, .13), trim)
# Pixel-shaped water coverage patch and a small sensor tile.
for x, y, width, depth in [(2.9, -3.25, 1.6, .65), (3.2, -2.9, 1, .4), (2.4, -3.55, .6, .3)]:
    box('Water sensor coverage / illustrative', (x, y, .15), (width, depth, .025), water)
box('Water sensor', (3.7, -3.65, .23), (.28, .28, .15), cream)
box('Water sensor light', (3.7, -3.65, .32), (.12, .12, .04), warning)

# An adjoining operations and security wing gives the facility a campus footprint.
box('Operations annex foundation', (-7.8, -1.7, -.2), (3.4, 4.8, .4), trim)
box('Operations annex floor', (-7.8, -1.7, .06), (3.3, 4.65, .12), cream)
box('Operations annex west wall', (-9.5, -1.7, .65), (.18, 4.8, 1.3), cream)
box('Operations annex north wall', (-7.8, .7, .7), (3.4, .18, 1.4), cream)
box('Operations annex front sill', (-7.8, -4.1, .22), (3.4, .18, .4), cream)
# Replace the solid west wall with a doorway into the network room.
for obj in list(bpy.data.objects):
    if obj.name in ('Left cutaway wall', 'Left wall cap'):
        bpy.data.objects.remove(obj, do_unlink=True)
box('West wall rear section', (-6.12, 1.7, .62), (.2, 4.8, 1.15), cream)
box('West wall front section', (-6.12, -3.6, .62), (.2, 1.0, 1.15), cream)
for y in (-2.7, -.6):
    box('Operations workbench', (-8.1, y, .75), (1.7, .7, .16), lavender)
    box('Operations desk pedestal', (-8.1, y, .4), (.7, .5, .65), cream)
    box('Operations monitor surround', (-8.1, y + .1, 1.15), (.8, .12, .52), rack_material)
    box('Operations monitor', (-8.1, y + .03, 1.15), (.65, .025, .38), blue)
    box('Operations keyboard', (-8.1, y - .2, .86), (.5, .18, .04), purple)
    box('Operations chair seat', (-8.1, y - .65, .43), (.48, .48, .14), blue)
    box('Operations chair back', (-8.1, y - .85, .7), (.48, .12, .5), blue)
    box('Operations chair base', (-8.1, y - .65, .22), (.15, .15, .35), trim)
box('Operations glass partition frame', (-7.8, -1.7, .8), (3.2, .07, .08), purple)
for x in (-9.3, -7.8, -6.3):
    box('Operations partition upright', (x, -1.7, .8), (.06, .08, 1.4), blue)
# Enlarge the building as actual geometry while preserving editable objects.
BUILDING_SCALE = 1.8
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.location *= BUILDING_SCALE
        obj.scale *= BUILDING_SCALE
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)

# Surround the open building with green land, landscaping and service paths.
grass = material('Campus meadow green', 'B7CF9B')
grass_light = material('Campus grass light', 'C4D8A9')
grass_shade = material('Campus grass shade', 'A7C18E')
foliage = material('Trees sage foliage', '91B7A1')
foliage_light = material('Trees light foliage', 'A8CE8A')
bark = material('Trees lavender trunks', '84769C')
box('Green land island', (-1.5, 0, -.85), (43, 31, .8), grass)
box('Green island edge', (-1.5, 0, -1.33), (43.3, 31.3, .2), grass_shade)
for x, y, w, d, mat in [(-17,7,5,5,grass_light), (14,9,7,6,grass_shade), (-16,-10,7,4,grass_shade), (8,-12,9,3,grass_light), (3,11,8,3,grass_light), (-18,-2,4,6,grass_light)]:
    box('Meadow patch', (x,y,-.43), (w,d,.025), mat)
# A pale path loops around the facility with an entrance walk and loading apron.
for x,y,w,d in [(-1.5,-10,34,1.5),(-1.5,10,34,1.5),(-19,0,1.5,21),(16,0,1.5,21),(0,-8.6,2.6,3.2)]:
    box('Campus walkway', (x,y,-.39), (w,d,.07), cream)
box('Utility service apron', (12,-3,-.38), (5.2,8,.1), lavender)
for y in (-5,-3,-1):
    box('Service apron marking', (14,y,-.32), (.12,1.1,.02), cream)
# Flat-faceted trees echo the geometric landscape reference.
for i, (x,y) in enumerate([(-20.4,10),(-15,12.7),(-8,12.7),(0,12.8),(8,12.7),(17.8,11),(-20.5,3),(-20.5,-6),(-17.2,-12.8),(-10,-12.7),(6,-12.7),(17.8,-9),(18,2)]):
    height=2.5+(i%3)*.4
    box('Tree trunk', (x,y,height*.28-.4), (.18,.18,height*.6), bark)
    if i%2:
        bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=.85, radius2=.05, depth=height, location=(x,y,height*.6))
        bpy.context.object.name='Faceted cypress'
        bpy.context.object.data.materials.append(foliage)
    else:
        box('Voxel tree lower crown', (x,y,height*.65), (1.5,1.5,1.5), foliage)
        box('Voxel tree upper crown', (x-.1,y,height*.65+.9), (1.1,1.1,.65), foliage_light)
for x in (-14,-10,-6,2,6,10):
    box('Pathway bollard', (x,-9.1,.05), (.16,.16,.8), trim)
    box('Pathway light', (x,-9.1,.5), (.24,.24,.15), cream)

# Orthographic view and a deliberately small image create the pixel finish.
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 480
scene.render.resolution_y = 336
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.filter_size = .1
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .8, .9, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
bpy.ops.object.light_add(type='AREA', location=(-14, -18, 30))
bpy.context.object.data.energy = 4500
bpy.context.object.data.size = 18
bpy.context.object.name = 'Soft meadow daylight'
bpy.ops.object.camera_add(location=(36, -46, 48))
camera = bpy.context.object
camera.name = 'Orthographic cutaway camera'
camera.rotation_euler = (Vector((-1.5, 0, .3)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 57
scene.camera = camera
bpy.context.view_layer.update()

# UI hotspots use the actual camera projection, keeping room selection aligned.
anchors = {'A': (-3.3, 2.1, 2.05), 'B': (2.75, 2.1, 2.05), 'C': (-4.0, -2.3, 1.4), 'D': (3.0, -3.1, 1.4)}
layout = {}
for room, point in anchors.items():
    world_point = Vector(point) * BUILDING_SCALE
    projected = world_to_camera_view(scene, camera, world_point)
    layout[room] = {'left': round(projected.x * 100, 3), 'top': round((1 - projected.y) * 100, 3), 'position': [world_point.x, world_point.z, -world_point.y]}
(ROOT / 'frontend/src/lib/facility-map-layout.json').write_text(json.dumps(layout, indent=2) + '\n')
scene.render.filepath = str(OUTPUT / 'facility-map-pixel.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/blender/facility-map-pixel.blend'))
bpy.ops.render.render(write_still=True)
# Keep the .blend fully editable; merge only the web export to reduce draw calls.
material_groups = {}
for obj in list(scene.objects):
    if obj.type == 'MESH' and obj.data.materials:
        material_groups.setdefault(obj.data.materials[0].name, []).append(obj)
for name, objects in material_groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects)>1:
        bpy.ops.object.join()
    bpy.context.object.name = 'Campus / ' + name
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'facility-campus.glb'), export_format='GLB', use_selection=True, export_cameras=False, export_lights=False, export_yup=True)
print('Expanded pixel campus, editable Blender source and optimized web model saved.')
