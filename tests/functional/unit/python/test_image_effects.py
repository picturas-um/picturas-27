"""Exercise the real image implementations against the video frame equivalents."""
import importlib.util
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Tools/video_effects'))
import effects
from utils.img_handler import Img_Handler

CASES = [
    ('brightness', 'Brightness', 'adjust_brightness', [0.5], {'brightness': 0.5}, (16, 12)),
    ('contrast', 'Contrast', 'contrast_image', [1.5], {'contrastFactor': 1.5}, (16, 12)),
    ('saturation', 'Saturation', 'saturation_image', [0], {'saturationFactor': 0}, (16, 12)),
    ('resize', 'Resize', 'resize_image', [(8, 6)], {'width': 8, 'height': 6}, (8, 6)),
    ('rotate', 'Rotate', 'rotate_image', [90], {'degrees': 90}, (12, 16)),
    ('cut', 'Cut', 'cut_image', [(0, 0, 8, 6)], {'left': 0, 'top': 0, 'right': 8, 'bottom': 6}, (8, 6)),
    ('border', 'Border', 'add_border', [(255, 0, 0), 2], {'borderWidth': 2, 'r': 255, 'g': 0, 'b': 0}, (20, 16)),
    ('binarization', 'Binarization', 'add_binarization', [100], {'threshold': 100}, (16, 12)),
]

@pytest.mark.parametrize('tool,cls,method,args,params,size', CASES, ids=[f'IMG-02-{x[0]}' for x in CASES])
def test_real_image_worker_matches_video_frame(tmp_path, monkeypatch, tool, cls, method, args, params, size):
    monkeypatch.syspath_prepend(str(ROOT / 'Tools' / tool))
    spec = importlib.util.spec_from_file_location('image_' + tool, ROOT / 'Tools' / tool / f'{tool}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    worker = getattr(module, cls).__new__(getattr(module, cls))
    worker._img_handler = Img_Handler()
    source, output = tmp_path / 'source.png', tmp_path / 'output.png'
    image = Image.new('RGB', (16, 12), (70, 100, 140))
    image.putpixel((0, 0), (250, 200, 30))
    image.save(source)
    original = source.read_bytes()
    getattr(worker, method)(str(source), str(output), *args)
    actual = Image.open(output).convert('RGB')
    expected = effects.apply_frame_effects(image, [{'procedure': tool, 'params': params}])
    assert actual.size == size
    assert actual.tobytes() == expected.tobytes()
    assert source.read_bytes() == original
    assert actual.tobytes() != image.tobytes()


def test_invalid_resize_has_no_output(tmp_path):
    image = Image.new('RGB', (16, 12))
    with pytest.raises(ValueError):
        effects.apply_frame_effects(image, [{'procedure': 'resize', 'params': {'width': 0, 'height': 6}}])
