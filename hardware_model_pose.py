"""Grounded product poses from the real convex hull and solid centre of mass."""
import math
import numpy as np
import trimesh
from scipy.spatial import ConvexHull


def product_pose(mesh, settings):
    """Choose a physically stable face, preferring a horizontal or vertical bore.

    Stable candidates use the real solid centre of mass, not the hull's mass.
    Roll/yaw is selected after grounding and does not change floor contact.
    """
    hull = mesh.convex_hull
    # Near-coplanar hull triangles can create tiny negative roundoff under a
    # probability square root. Support geometry, not probabilities, is validated below.
    with np.errstate(invalid='ignore'):
        transforms, probabilities = hull.compute_stable_poses(center_mass=mesh.center_mass,
                                                               sigma=0, n_samples=1, threshold=1e-9)
    probabilities = np.nan_to_num(probabilities, nan=0.)
    if not len(transforms):
        raise ValueError('No stable hull support found')
    side = settings.get('resting_axis') == 'side'
    # A side pose has the principal Z axis close to horizontal. A face pose
    # prefers the original lower face down, keeping the bore/flange visible.
    scores = np.abs(transforms[:, 2, 2]) if side else 1-transforms[:, 2, 2]
    selected = min(range(len(transforms)), key=lambda i: (round(float(scores[i]), 5), -probabilities[i]))
    transform = transforms[selected].copy()
    axis = transform[:3, :3] @ [0, 0, 1]
    alignment = math.pi-math.atan2(axis[1], axis[0]) if side else 0.
    yaw = trimesh.transformations.rotation_matrix(alignment+math.radians(settings.get('yaw_degrees', 0)), [0, 0, 1])
    transform = yaw @ transform
    points = trimesh.transform_points(mesh.vertices, transform)
    transform[2, 3] -= points[:, 2].min()
    points = trimesh.transform_points(mesh.vertices, transform)
    tolerance = max(1e-5, mesh.extents.max()*1e-6)
    contacts = points[points[:, 2] <= tolerance]
    xy = np.unique(np.round(contacts[:, :2], 6), axis=0)
    centre = trimesh.transform_points([mesh.center_mass], transform)[0]
    if len(xy) < 3:
        raise ValueError('Resting support has fewer than three non-collinear contacts')
    support_hull = ConvexHull(xy)
    equations = support_hull.equations
    distances = equations[:, :2] @ centre[:2]+equations[:, 2]
    if distances.max() > tolerance:
        raise ValueError('Solid centre of mass lies outside support polygon')
    return transform, dict(method='stable convex hull using solid centre of mass',
        stable_pose_probability=float(probabilities[selected]),
        support_tolerance_mm=float(tolerance), contact_vertices=len(contacts),
        support_polygon_mm=xy[support_hull.vertices].tolist(),
        centre_of_mass_mm=centre.tolist(), centre_inside_support=True,
        stability_margin_mm=float(-distances.max()),
        principal_axis_world=(transform[:3, :3] @ [0, 0, 1]).tolist(),
        ground_clearance_mm=float(points[:, 2].min()),
        grounded_bounds_mm=[points.min(axis=0).tolist(), points.max(axis=0).tolist()])
