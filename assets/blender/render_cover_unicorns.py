"""Render cover walking/grazing atlases from the campus unicorn models.

blender --background --python assets/blender/render_cover_unicorns.py
Reuses unicorn-npcs.blend; each atlas is rendered directly as a 4x4 grid.
"""
from pathlib import Path
from math import sin, pi
import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'frontend/public/models'


def duplicate_tree(source, parent=None):
    clone = source.copy()
    bpy.context.collection.objects.link(clone)
    clone.parent = parent
    for child in source.children:
        duplicate_tree(child, clone)
    return clone


for action in ('walk', 'graze'):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/blender/unicorn-npcs.blend'))
    scene = bpy.context.scene
    originals = [bpy.data.objects[f'Unicorn_{i}'] for i in range(4)]
    camera = scene.camera
    camera.location = (-4, -7, 3.2)
    target = Vector((0, 0, .86))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 10.4
    rotation = camera.rotation_euler.to_quaternion()
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    for row, source in enumerate(originals):
        for col in range(4):
            model = duplicate_tree(source)
            model.location = right * ((col - 1.5) * 2.6) + up * ((1.5 - row) * 2.6)
            phase = [0, pi / 2, pi, pi * 1.5][col]
            for part in model.children:
                if part.name.startswith('Leg_'):
                    diagonal = part.name.startswith(('Leg_Front_L', 'Leg_Back_R'))
                    part.rotation_euler.x = sin(phase + (0 if diagonal else pi)) * .32 if action == 'walk' else 0
                if part.name.startswith('Tail'):
                    part.rotation_euler.z = sin(phase) * .12
            if action == 'graze':
                # Rotate the neck, face, ears, eyes, mane and horn together
                # around the shoulders, leaving the four feet planted.
                pivot = Vector((0, -.22, .95))
                tilt = Matrix.Translation(pivot) @ Matrix.Rotation(.95 + sin(phase) * .06, 4, 'X') @ Matrix.Translation(-pivot)
                head_parts = ('Raised neck', 'Square head', 'Stepped muzzle', 'Soft nose', 'Upright ear', 'Ear inset', 'Square eye', 'Eye glint', 'Golden pyramid horn', 'Forelock', 'Stepped mane')
                for part in model.children:
                    if part.name.startswith(head_parts):
                        part.matrix_basis = tilt @ part.matrix_basis
    for source in originals:
        for part in [source, *source.children_recursive]:
            bpy.data.objects.remove(part, do_unlink=True)
    for light in [obj for obj in scene.objects if obj.type == 'LIGHT']:
        light.location = (-5, -12, 16)
        light.data.energy = 1800
        light.data.size = 20
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.filter_size = .5
    scene.render.filepath = str(OUTPUT / f'unicorn-voxel-{action}-atlas.png')
    bpy.ops.render.render(write_still=True)
print('Cover unicorn atlases rendered from the campus Blender models.')
