import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from studio.ui import GenerationDialog
from studio.storage import Project
from studio.workflows import Generation

app=QApplication.instance() or QApplication([])

def test_video_controls_match_actual_graph(tmp_path):
    p=Project(tmp_path/'p',True)
    d=GenerationDialog(p,Generation(mode='h3_i2v',megapixels=.2,seconds=2))
    assert '608 × 352' in d.summary.text() and '56 帧' in d.summary.text()
    assert d.cinema.isEnabled() and not d.quad.isEnabled() and not d.scale.isEnabled()
    d.deleteLater()

def test_qwen_geometry_and_upscale_controls(tmp_path):
    p=Project(tmp_path/'p',True)
    d=GenerationDialog(p,Generation(mode='qwen',megapixels=.2))
    assert '608 × 352' in d.summary.text()
    assert not d.seconds.isEnabled() and d.int8.isEnabled()
    d.mode.setCurrentIndex(d.mode.findData('upscale'))
    assert d.scale.isEnabled() and not d.mp.isEnabled()
    d.deleteLater()
