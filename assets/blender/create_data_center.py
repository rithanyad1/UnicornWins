"""Create SENTINEL's editable voxel data center and transparent pixel render.

Run from the repository root:
  blender --background --python assets/blender/create_data_center.py
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "frontend/public/models"
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, glow=0):
    rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    # Convert design hex values from sRGB to Blender's linear color space.
    linear = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Roughness"].default_value = .85
    if glow:
        shader.inputs["Emission Color"].default_value = (*linear, 1)
        shader.inputs["Emission Strength"].default_value = glow
    return mat


cream = material("Cream / meadow clouds", "F4F7EA")
lavender = material("Lavender / facade", "CDB9DD")
light_lavender = material("Pale lavender / trim", "E1D8F0")
purple = material("Sentinel purple", "65509C")
dark = material("Server charcoal", "353047")
sky = material("Sky blue glazing", "B3D4E4")
blue = material("Blue glass shade", "7EADBF")
mint = material("Status green", "BCDFA8", .2)
green = material("Meadow green", "91B7A1")
leaf = material("Voxel foliage", "A8CE8A")
roof = material("Muted purple roof", "84769C")


def box(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def roof_edge(name, x, y, z, width, depth):
    box(name + " roof", (x, y, z), (width, depth, .16), roof)
    for side in (-1, 1):
        box(name + " parapet front back", (x, y + side * (depth / 2 - .09), z + .16), (width, .18, .34), cream)
        box(name + " parapet side", (x + side * (width / 2 - .09), y, z + .16), (.18, depth, .34), cream)


def hvac(x, y, z, name):
    box(name + " plinth", (x, y, z + .12), (1.22, .95, .24), purple)
    box(name + " housing", (x, y, z + .42), (1.13, .86, .48), sky)
    cylinder(name + " fan well", (x, y, z + .68), .32, .045, dark)
    cylinder(name + " fan center", (x, y, z + .72), .075, .07, light_lavender)
    for angle in (0, math.pi / 2):
        blade = box(name + " fan blades", (x, y, z + .71), (.48, .09, .035), lavender)
        blade.rotation_euler.z = angle + .4
    for i in range(4):
        box(name + " intake grille", (x - .36 + i * .24, y - .435, z + .4), (.09, .025, .28), purple)


# One compact campus, not a city: server hall, taller control wing and cooling yard.
box("Foundation / cream slab", (0, 0, .05), (10.5, 7.1, .3), cream)
box("Foundation / lavender edge", (0, 0, -.12), (10.65, 7.25, .15), lavender)
box("Main server hall", (-.9, 0, 1.64), (6.6, 4.6, 2.9), cream)
box("Server hall lower band", (-.9, -.01, .42), (6.7, 4.65, .4), lavender)
roof_edge("Server hall", -.9, 0, 3.15, 6.85, 4.85)

box("Control wing", (2.8, .5, 2.45), (2.5, 3.6, 4.5), light_lavender)
box("Control wing lower band", (2.8, .5, .46), (2.58, 3.65, .4), purple)
roof_edge("Control wing", 2.8, .5, 4.76, 2.75, 3.85)

# Repeating facade bays frame clearly visible server cabinets.
for index, x in enumerate((-3.55, -2.35, -1.15, .05)):
    box("Server hall glass bay", (x, -2.312, 1.73), (.92, .06, 1.8), blue)
    box("Server rack", (x, -2.36, 1.58), (.56, .05, 1.35), dark)
    for row in range(5):
        box("Rack drawer", (x, -2.395, 1.08 + row * .24), (.47, .03, .13), roof)
        box("Rack activity LED", (x + .15, -2.418, 1.08 + row * .24), (.055, .025, .055), mint)
    box("Facade mullion", (x - .56, -2.39, 1.8), (.12, .16, 2.45), cream)
box("Server hall lintel", (-1.77, -2.4, 2.84), (5.2, .15, .2), lavender)

# Front entrance and an illuminated blue door.
box("Entry surround", (1.02, -2.49, 1.26), (1.16, .35, 2.1), purple)
box("Entry glass", (1.02, -2.68, 1.18), (.85, .06, 1.7), sky)
box("Door mullion", (1.02, -2.73, 1.18), (.055, .06, 1.7), cream)
box("Door transom", (1.02, -2.73, 1.61), (.85, .06, .065), cream)
box("Door handles", (1.02, -2.77, 1.08), (.22, .045, .08), purple)
box("Entry canopy", (.95, -2.8, 2.45), (1.7, 1.05, .16), light_lavender)
for step in range(3):
    box("Entrance steps", (1, -3.05 - step * .19, .31 - step * .055), (1.75, .65, .12), cream)

# Control wing: glass panels, panel dividers and narrow side windows.
for z in (1.35, 3.15):
    box("Control wing front glazing", (2.8, -1.315, z), (1.96, .055, 1.2), sky)
    for x in (2.25, 2.8, 3.35):
        box("Wing window mullion", (x, -1.37, z), (.07, .09, 1.25), cream)
    box("Wing glass reflection", (3.55, -1.38, z), (.14, .04, .85), cream)
for y in (-.6, .15, .9, 1.65):
    box("Wing side window", (4.06, y, 2.65), (.06, .43, 3.2), blue)
    box("Wing side window inset", (4.10, y, 2.65), (.03, .19, 2.7), purple)
box("Wing mid-floor band", (2.8, -1.37, 2.28), (2.5, .14, .18), cream)

# Cooling hardware makes the silhouette read as a data center.
for x in (-2.75, -.85):
    for y in (-.65, .85):
        hvac(x, y, 3.28, "Rooftop cooling unit")
hvac(2.8, .5, 4.86, "Control wing cooling unit")
box("Roof duct", (-.85, 1.85, 3.47), (3.8, .32, .28), light_lavender)
box("Roof duct riser", (1.15, 1.85, 3.74), (.3, .32, .78), light_lavender)

box("Cooling yard pad", (3.15, -2.42, .3), (2.65, 1.4, .16), lavender)
for x in (2.35, 3.35):
    box("Outdoor chiller", (x, -2.3, .92), (.8, .85, 1.12), cream)
    cylinder("Chiller exhaust", (x, -2.3, 1.51), .29, .045, purple)
    for row in range(5):
        box("Chiller grille", (x, -2.735, .6 + .16 * row), (.6, .025, .055), roof)

# A pixel-built SENTINEL sign; no font dependencies or external textures.
glyphs = {
    "S": ["111", "100", "111", "001", "111"],
    "E": ["111", "100", "110", "100", "111"],
    "N": ["101", "111", "111", "111", "101"],
    "T": ["111", "010", "010", "010", "010"],
    "I": ["111", "010", "010", "010", "111"],
    "L": ["100", "100", "100", "100", "111"],
}
box("SENTINEL signage backing", (-1.5, -2.45, 2.95), (3.25, .15, .56), purple)
pixel = .078
for index, character in enumerate("SENTINEL"):
    for row, cells in enumerate(glyphs[character]):
        for col, cell in enumerate(cells):
            if cell == "1":
                box("Sign / " + character, (-2.71 + index * pixel * 4 + col * pixel, -2.54, 3.1 - row * pixel), (pixel * .88, .035, pixel * .88), cream)

# A little voxel planting softens the service campus into the meadow.
for x, y in [(-4.65, -2.7), (-4.65, 2.5), (4.62, 2.5)]:
    box("Planter", (x, y, .35), (.65, .65, .34), light_lavender)
    box("Shrub base", (x, y, .65), (.65, .62, .4), green)
    box("Shrub crown", (x - .05, y, .95), (.5, .48, .35), leaf)
    box("Shrub top", (x + .05, y, 1.17), (.28, .3, .2), leaf)

# Antenna, beacon and entrance status indicator.
box("Antenna footing", (3.45, 1.55, 4.99), (.4, .4, .15), purple)
box("Antenna mast", (3.45, 1.55, 5.48), (.075, .075, .95), cream)
box("Antenna beacon", (3.45, 1.55, 5.99), (.15, .15, .15), mint)
box("Healthy entrance indicator", (1.65, -2.39, 1.65), (.12, .1, .3), mint)

# Orthographic, nearest-neighbor presentation with flat faces and soft daylight.
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 256
scene.render.resolution_y = 224
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.filter_size = .1
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "Medium High Contrast"
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.72, .81, .9, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = .65

bpy.ops.object.light_add(type="AREA", location=(-4, -6, 12))
key = bpy.context.object
key.name = "Large soft daylight"
key.data.energy = 1700
key.data.shape = "DISK"
key.data.size = 7

bpy.ops.object.camera_add(location=(11, -15, 11))
camera = bpy.context.object
camera.name = "Isometric pixel camera"
target = Vector((0, 0, 2.0))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 15.5
scene.camera = camera

scene.render.filepath = str(OUTPUT / "sentinel-data-center.png")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "assets/blender/sentinel-data-center.blend"))
bpy.ops.render.render(write_still=True)
print("SENTINEL: editable Blender scene and transparent pixel render complete.")
