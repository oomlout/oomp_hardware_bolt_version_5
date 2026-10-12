"""Read-only validation of the finite photographic proof set."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import trimesh
import yaml
from generate_three_d_model_proofs import PROOFS
from working_three_d_model import ROOT, _fingerprint


def validate_proof(identity):
    folder=ROOT/'parts'/identity
    output=folder/'three_d_model'
    recipe=yaml.safe_load((folder/'working.yaml').read_text(encoding='utf-8'))['three_d_model_details']
    manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['fingerprint']==_fingerprint(recipe), f'{identity}: stale proof'
    assert len(manifest['artifacts'])==27
    for name,info in manifest['artifacts'].items():
        data=(output/name).read_bytes()
        assert len(data)==info['bytes'] and hashlib.sha256(data).hexdigest()==info['sha256']
    for render in recipe['renders'].values():
        image=Image.open(output/render['file'])
        assert image.size==(render['pixels'],render['pixels'])
        pixels=np.asarray(image)
        # Slender bolts occupy little of a square frame. Whole-image standard
        # deviation must not reject a correctly framed long, thin product.
        assert pixels.std()>2 and int(pixels.max())-int(pixels.min())>30, f'{identity}: blank photograph'
    assert manifest['models']['full']['watertight'] and manifest['models']['display']['watertight']
    assert manifest['models']['display']['triangles']<manifest['models']['full']['triangles']/2
    scene=json.loads((output/'render_scene.json').read_text(encoding='utf-8'))
    assert scene['poses']['isometric']['camera_eye']==[1,-1,1]
    assert scene['poses']['product']['camera_eye']==[-6,-10,6]
    assert scene['poses']['product']['centre_inside_support']
    for support in scene['poses']['product']['variant_supports'].values():
        assert support['centre_inside_support'] and support['stability_margin_mm']>=0
        assert support['contact_vertices']>=3
    for pose in scene['poses'].values():
        assert abs(pose['ground_clearance_mm'])<1e-6
        assert all(abs(clearance)<1e-6 for clearance in pose['variant_ground_clearance_mm'].values())
        assert all(frame['max_frame_fraction']<1 for frame in pose['framing'].values())
    for variant in ['full','display']:
        mesh=trimesh.load(output/f'model_{variant}.stl')
        assert mesh.is_watertight and mesh.body_count==recipe['parameters']['expected_components']
        np.testing.assert_allclose(mesh.extents,manifest['models'][variant]['dimensions_mm'],atol=2e-5)
        web=trimesh.load(output/f'model_{variant}.glb',force='scene')
        np.testing.assert_allclose(web.extents,mesh.extents[[0,2,1]]*.001,atol=2e-8)
    assert not list(output.glob('.build-*'))
    return dict(identity=identity, triangles={key: value['triangles'] for key,value in manifest['models'].items()},
                dimensions_mm=manifest['models']['full']['dimensions_mm'],
                device=scene['device'], render_statistics=scene['render_statistics'])


if __name__=='__main__':
    results=[validate_proof(identity) for identity in PROOFS]
    (ROOT/'three_d_model_proof_validation.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(f'Validated {len(results)} proofs: hashes, dimensions, 512/2048 images, contacts and framing.')
