"""Build editable voxel unicorns matching the campus materials and geometry.

blender --background --python assets/blender/create_unicorn_npcs.py
"""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'frontend/public/models'
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
blue = material('Blue equipment panels', 'B3D4E4')
ink = material('Soft charcoal eyes', '554C65')
gold = material('Matte golden horn', 'E5BD70')
blush = material('Muzzle blush', 'D8A1A7')
palettes = [material(name + ' mane', color) for name, color in
            [('Rose', 'D8A1A7'), ('Lavender', '9580D4'), ('Mint', '91B7A1'), ('Peach', 'DDB49A')]]


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def box(name, location, size, mat, parent):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


roots = []
for index, mane in enumerate(palettes):
    root = empty(f'Unicorn_{index}', location=((index - 1.5) * 2.15, 0, 0))
    roots.append(root)
    box('Block body', (0, .03, .78), (.54, .92, .53), cream, root)
    box('Lavender belly', (0, .03, .55), (.46, .78, .12), lavender, root)
    box('Raised neck', (0, -.36, 1.02), (.4, .36, .64), cream, root)
    box('Square head', (0, -.48, 1.32), (.48, .49, .44), cream, root)
    box('Stepped muzzle', (0, -.76, 1.22), (.43, .22, .26), lavender, root)
    box('Soft nose', (0, -.88, 1.23), (.33, .025, .15), blush, root)
    for side in (-1, 1):
        box('Upright ear', (side * .17, -.35, 1.59), (.13, .16, .23), cream, root)
        box('Ear inset', (side * .17, -.435, 1.6), (.07, .015, .12), blush, root)
        box('Square eye', (side * .247, -.59, 1.37), (.018, .09, .10), ink, root)
        box('Eye glint', (side * .26, -.61, 1.395), (.012, .03, .03), cream, root)
    # A four-sided horn and stepped cuboids echo the building's voxel details.
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=.115, radius2=0, depth=.38)
    horn = bpy.context.object
    horn.name = 'Golden pyramid horn'
    horn.parent = root
    horn.location = (0, -.59, 1.69)
    horn.data.materials.append(gold)
    box('Forelock', (0, -.46, 1.55), (.23, .29, .14), mane, root)
    for step in range(4):
        box('Stepped mane', (0, -.18 + step * .055, 1.43 - step * .17),
            (.24, .22, .21), mane if step % 2 == 0 else blue, root)
    tail = empty('Tail', root, (0, .51, .91))
    for step in range(3):
        box('Tail pixel', (0, step * .12, -step * .13), (.23, .21, .22),
            mane if step != 1 else blue, tail)
    for side, x in [('L', -.18), ('R', .18)]:
        for end, y in [('Front', -.30), ('Back', .34)]:
            leg = empty(f'Leg_{end}_{side}', root, (x, y, .57))
            box('Leg', (0, 0, -.23), (.18, .20, .46), cream, leg)
            box('Pastel hoof', (0, -.025, -.50), (.21, .25, .14), mane, leg)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.render.resolution_x = 1200
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .8, .9, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
bpy.ops.object.light_add(type='AREA', location=(-3, -4, 8))
bpy.context.object.data.energy = 650
bpy.context.object.data.size = 7
bpy.ops.object.camera_add(location=(4, -8, 5))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, .8)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 9.6
scene.camera = camera
scene.render.filepath = str(OUTPUT / 'unicorn-npcs-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/blender/unicorn-npcs.blend'))
bpy.ops.render.render(write_still=True)

# Merge only meshes sharing a parent and material for the web; retain leg
# pivots and tail pivots for animation, and keep the .blend fully editable.
groups = {}
for obj in list(scene.objects):
    if obj.type == 'MESH':
        groups.setdefault((obj.parent, obj.data.materials[0]), []).append(obj)
for (parent, mat), objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    bpy.context.object.name = parent.name + '_' + mat.name
bpy.ops.object.select_all(action='DESELECT')
for root in roots:
    root.select_set(True)
    for obj in root.children_recursive:
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'unicorn-npcs.glb'), export_format='GLB',
                          use_selection=True, export_cameras=False, export_lights=False, export_yup=True)
print('Voxel unicorns: editable Blender source, preview and animated-part GLB exported.')
