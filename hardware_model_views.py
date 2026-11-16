"""Orthographic hidden-line SVGs from the actual solid mesh.

Uses a triangle depth buffer to determine visibility of vector edges.
There is no OpenGL, browser, Blender or display-server dependency.
"""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from numba import njit
import trimesh

VIEWS = {
    'isometric': (1, -1, 1),
    'front': (0, -1, 0), 'back': (0, 1, 0),
    'left': (-1, 0, 0), 'right': (1, 0, 0),
    'top': (0, 0, 1), 'bottom': (0, 0, -1),
}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def camera_basis(view):
    eye = np.asarray(VIEWS[view], dtype=float)
    eye /= np.linalg.norm(eye)
    up = np.array([0., 0., 1.]) if abs(eye[2]) < .99 else np.array([0., 1., 0.])
    right = np.cross(up, eye)
    right /= np.linalg.norm(right)
    up = np.cross(eye, right)
    return np.stack((right, -up, eye), axis=1)


@njit(cache=True)
def _raster(vertices, faces, colours, size):
    depth = np.full((size, size), -np.inf, dtype=np.float64)
    rgb = np.full((size, size, 3), 250., dtype=np.float64)
    for face in faces:
        a, b, c = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        area = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(area) < 1e-10:
            continue
        xmin = max(0, int(math.floor(min(a[0], b[0], c[0]))))
        xmax = min(size-1, int(math.ceil(max(a[0], b[0], c[0]))))
        ymin = max(0, int(math.floor(min(a[1], b[1], c[1]))))
        ymax = min(size-1, int(math.ceil(max(a[1], b[1], c[1]))))
        for y in range(ymin, ymax+1):
            for x in range(xmin, xmax+1):
                px, py = x+.5, y+.5
                wa = ((b[1]-c[1])*(px-c[0])+(c[0]-b[0])*(py-c[1]))/area
                wb = ((c[1]-a[1])*(px-c[0])+(a[0]-c[0])*(py-c[1]))/area
                wc = 1-wa-wb
                if min(wa, wb, wc) >= -1e-9:
                    z = wa*a[2]+wb*b[2]+wc*c[2]
                    if z > depth[y, x]:
                        depth[y, x] = z
                        for channel in range(3):
                            rgb[y, x, channel] = (wa*colours[face[0], channel]+
                                wb*colours[face[1], channel]+wc*colours[face[2], channel])
    return depth, rgb


def project(mesh, view, size, margin=.075):
    basis = camera_basis(view)
    projected = mesh.vertices @ basis
    bounds = np.array([projected[:, :2].min(axis=0), projected[:, :2].max(axis=0)])
    scale = size*(1-2*margin)/max(np.ptp(bounds, axis=0))
    offset = size/2-bounds.mean(axis=0)*scale
    pixels = projected.copy()
    pixels[:, :2] = projected[:, :2]*scale+offset
    return basis, bounds, scale, offset, pixels


def _feature_lines(mesh, p, view, basis, variant):
    """Silhouette edges, sharp boundaries and analytic helical crest boundaries."""
    adjacent = mesh.face_adjacency
    facing = mesh.face_normals @ basis[:, 2]
    front0 = facing[adjacent[:, 0]] > 1e-8
    front1 = facing[adjacent[:, 1]] > 1e-8
    silhouette = front0 != front1
    sharp = mesh.face_adjacency_angles > math.radians(35)
    sharp &= front0 | front1
    edges = mesh.face_adjacency_edges
    # Thread crease positions are analytic; avoid tessellation diagonals at crests.
    if variant == 'full' and p['family'] in {'bolt', 'rod'}:
        points = mesh.vertices[edges]
        threaded = ((points[:, :, 2] < p['thread_end_z_mm']-p['thread_runout_mm']).all(axis=1) &
                    (np.linalg.norm(points[:, :, :2], axis=2) > p['nominal_diameter_mm']*.4).all(axis=1))
        sharp &= ~threaded
    segments = mesh.vertices[edges[silhouette | sharp]]
    if variant == 'full' and p['family'] in {'bolt', 'rod'}:
        pitch, end = p['pitch_mm'], p['thread_end_z_mm']-p['thread_runout_mm']
        if p['family'] == 'rod':
            end -= p['tip_chamfer_mm']
        for phase in [-1/16, 1/16]:
            theta = np.linspace(-2*math.pi, (end/pitch+1)*2*math.pi,
                                max(2, math.ceil((end/pitch+2)*192)))
            z = pitch*(theta/(2*math.pi)+phase)
            keep = (z >= p['tip_chamfer_mm']) & (z <= end)
            theta, z = theta[keep], z[keep]
            r = p['nominal_diameter_mm']/2
            helix = np.column_stack((r*np.cos(theta), r*np.sin(theta), z))
            segments = np.concatenate((segments, np.stack((helix[:-1], helix[1:]), axis=1)))
    return segments


def svg_lines(mesh, p, variant, view, path, visibility_size=1024):
    basis, bounds, scale, offset, pixels = project(mesh, view, visibility_size)
    raster_faces = mesh.faces
    if p['family'] == 'rod' and view in {'top', 'bottom'}:
        # A solid, constant-pitch rod's nearest complete thread turns cover
        # every radial ray. All more distant turns are occluded in an axial
        # view. Keep two pitches beyond the end chamfer, including crossing
        # triangles, rather than rasterizing hundreds of identical layers.
        band = p['tip_chamfer_mm']+2*p['pitch_mm']
        z = mesh.vertices[:, 2]
        near = z >= p['length_mm']-band if view == 'top' else z <= band
        raster_faces = mesh.faces[near[mesh.faces].any(axis=1)]
    depth, _ = _raster(pixels, raster_faces, np.zeros_like(mesh.vertices), visibility_size)
    segments = _feature_lines(mesh, p, view, basis, variant) @ basis
    # Sample each segment, splitting partial occlusions instead of drawing through a solid.
    lengths = np.linalg.norm(segments[:, 1, :2]-segments[:, 0, :2], axis=1)*scale
    fragments = []
    # Sub-pixel thread segments need only their two endpoints. Batch those
    # identical visibility tests instead of doing thousands of NumPy calls
    # for every thread turn on long stock.
    short = lengths <= 2
    endpoints = segments[short].copy()
    endpoints[:, 1] = endpoints[:, 0]+(endpoints[:, 1]-endpoints[:, 0])
    index = np.clip(np.floor(endpoints[:, :, :2]*scale+offset).astype(int), 0, visibility_size-1)
    nearby_min = np.full(index.shape[:2], np.inf)
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            nearby_min = np.minimum(nearby_min, depth[
                np.clip(index[:, :, 1]+dy, 0, visibility_size-1),
                np.clip(index[:, :, 0]+dx, 0, visibility_size-1)])
    visible = (endpoints[:, :, 2] >= nearby_min-1/scale).all(axis=1)
    fragments.extend(endpoints[visible, :, :2])
    # End-on views of metre stock contain many equal-length helix segments.
    # Batch equal sample counts while retaining the exact visibility and
    # contiguous-fragment rules; cap temporary arrays at 65536 sample points.
    long_segments = segments[~short]
    counts = np.ceil(lengths[~short]/2).astype(int)+1
    for count in np.unique(counts):
        group = long_segments[counts == count]
        batch_size = max(1, 65536//int(count))
        fractions = np.linspace(0, 1, count)[None, :, None]
        for start in range(0, len(group), batch_size):
            batch = group[start:start+batch_size]
            samples = batch[:, 0, None, :]+fractions*(batch[:, 1, None, :]-batch[:, 0, None, :])
            index = np.clip(np.floor(samples[:, :, :2]*scale+offset).astype(int), 0, visibility_size-1)
            nearby_min = np.full(index.shape[:2], np.inf)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    nearby_min = np.minimum(nearby_min, depth[
                        np.clip(index[:, :, 1]+dy, 0, visibility_size-1),
                        np.clip(index[:, :, 0]+dx, 0, visibility_size-1)])
            visible = samples[:, :, 2] >= nearby_min-1/scale
            mask = visible[:, :-1] & visible[:, 1:]
            begins = np.nonzero(mask & ~np.pad(mask[:, :-1], ((0,0),(1,0))))
            ends = np.nonzero(mask & ~np.pad(mask[:, 1:], ((0,0),(0,1))))
            fragments.extend(zip(samples[begins[0], begins[1], :2], samples[ends[0], ends[1]+1, :2]))
    pad = max(.25, p['characteristic_dimension_mm']*.08)
    lower, upper = bounds[0]-pad, bounds[1]+pad
    width, height = upper-lower
    root = ET.Element(f'{{{NS}}}svg', width=f'{width:.5f}mm', height=f'{height:.5f}mm',
        viewBox=f'{lower[0]:.5f} {lower[1]:.5f} {width:.5f} {height:.5f}')
    ET.SubElement(root, f'{{{NS}}}title').text = f'{p["identity"]} | {p["specification"]} | {variant} {view}'
    ET.SubElement(root, f'{{{NS}}}metadata').text = json.dumps(dict(units='mm', projection='orthographic',
        view=view, variant=variant, source='model mesh', hidden_edges='removed by depth buffer',
        parameters=p, camera_eye=VIEWS[view]), sort_keys=True)
    group = ET.SubElement(root, f'{{{NS}}}g', id='hardware-model', fill='none', stroke='#161a20',
        attrib={'stroke-width': f'{max(.02, p["characteristic_dimension_mm"]*.01):.5f}',
                'stroke-linecap': 'round', 'stroke-linejoin': 'round'})
    commands = ' '.join(f'M{a[0]:.5f},{a[1]:.5f}L{b[0]:.5f},{b[1]:.5f}' for a,b in fragments)
    ET.SubElement(group, f'{{{NS}}}path', d=commands)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def export_views(mesh, p, variant, output):
    directory = Path(output)/variant
    directory.mkdir(parents=True, exist_ok=True)
    for view in VIEWS:
        svg_lines(mesh, p, variant, view, directory/f'{view}.svg')
