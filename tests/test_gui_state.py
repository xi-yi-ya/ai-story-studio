import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from studio.ui import GenerationDialog
from studio.storage import Project
from studio.workflows import Generation
from studio.ui import Studio
from PySide6.QtWidgets import QPushButton

app=QApplication.instance() or QApplication([])

def test_video_controls_match_actual_graph(tmp_path):
    p=Project(tmp_path/'p',True)
    d=GenerationDialog(p,Generation(mode='h3_i2v',megapixels=.2,seconds=2))
    assert '608 × 352' in d.summary.text() and '56 帧' in d.summary.text()
    assert d.cinema.isEnabled() and not d.quad.isEnabled() and not d.scale.isEnabled()
    d.deleteLater()

def test_visible_history_and_delete_on_all_cards(tmp_path):
    p=Project(tmp_path/'cards',True)
    for kind in ('characters','scenes','shots'):p.add(kind,kind)
    window=Studio(p.root)
    labels=[b.text() for b in window.findChildren(QPushButton)]
    assert labels.count('生成历史')==3
    assert {'删除角色','删除场景','删除分镜'}<=set(labels)
    window.close()

def test_qwen_geometry_and_upscale_controls(tmp_path):
    p=Project(tmp_path/'p',True)
    d=GenerationDialog(p,Generation(mode='qwen',megapixels=.2))
    assert '608 × 352' in d.summary.text()
    assert not d.seconds.isEnabled() and d.int8.isEnabled()
    d.mode.setCurrentIndex(d.mode.findData('upscale'))
    assert d.scale.isEnabled() and not d.mp.isEnabled()
    d.deleteLater()
