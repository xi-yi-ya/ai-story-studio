"""Opt-in real Qt host -> Vue -> Python file-drop verification, no API inference.

Run from the repository root after building frontend/dist. Uses a unique local
QA project and the short video from library-flow-live.mjs. Does not touch originals.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.desktop import Desktop
from studio.storage import Project

repo = Path(__file__).resolve().parents[1]
live = json.loads((repo / 'local-data/v120-package-library-live-report.json').read_text(encoding='utf-8'))
video = Path(live['project']) / live['tests'][1]['outputs'][0]
root = repo / 'local-data' / ('v120-native-drop-' + str(time.time_ns()))
Project(root, create=True)
image = root / '原始拖拽图片.png'
Image.new('RGB', (120, 80), 'blue').save(image)
app = QApplication(sys.argv)
window = Desktop(repo / 'frontend/dist', root)
window.show()
window.view.setZoomFactor(1.25)
report = {'passed': False, 'project': str(root), 'zoom': 1.25, 'errors': []}
started = time.monotonic()
sent = False
checking = False


def finish(error=None):
    if error:
        report['errors'].append(str(error))
        report['page'] = window.page.url().toString()
        window.grab().save(str(repo / 'local-data/v120-native-drop-failure.png'))
    else:
        report['passed'] = True
    (repo / 'local-data/v120-native-drop-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    timer.stop()
    window.close()


def inspect_ui(value):
    global checking
    checking = False
    if isinstance(value, str) and value:
        value = json.loads(value)
    if value and value.get('ready'):
        finish()


def drop_at(value):
    global sent, checking
    checking = False
    if isinstance(value, str) and value:
        value = json.loads(value)
    if not value or not value.get('ready'):
        report['lastUiState'] = value
        return
    report.pop('lastUiState', None)
    try:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(image)), QUrl.fromLocalFile(str(video))])
        point = QPoint(round(value['x'] * 1.25), round(value['y'] * 1.25))
        enter = QDragEnterEvent(point, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(window.view, enter)
        event = QDropEvent(QPointF(point), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(window.view, event)
        if not enter.isAccepted() or not event.isAccepted():
            raise AssertionError('Native Qt drag/drop events were not accepted')
        sent = True
        report['nativeEventsAccepted'] = True
    except Exception as error:
        finish(error)


def poll():
    global checking
    if checking:
        return
    if time.monotonic() - started > 45:
        finish('Native host to Vue file-drop timed out')
        return
    if window.service.last_error:
        finish(window.service.last_error)
        return
    checking = True
    if not sent:
        window.page.runJavaScript("""JSON.stringify((()=>{const s=document.querySelector('#app')?.__vue_app__?.config.globalProperties.$pinia._s.get('studio');
            if(!s?.ready)return {ready:false,reason:'bootstrap'};
            s.assistantOpen=true;const e=document.querySelector('[data-media-drop="assistant"]');
            if(!e)return {ready:false,reason:'assistant collapsed',width:window.innerWidth};
            const r=e.getBoundingClientRect();return {ready:true,x:r.x+r.width/2,y:r.y+200};})())""", drop_at)
        return
    context = window.service.media_context
    if len(context) != 2:
        checking = False
        return
    try:
        kinds = [item['kind'] for item in context]
        if kinds != ['image', 'video']:
            raise AssertionError('Mixed file drop did not preserve image/video order')
        for source, item in zip([image, video], context):
            imported = window.service.project.file(item['file'])
            if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(imported.read_bytes()).digest():
                raise AssertionError('Imported media differs from original')
        p = window.service.project.data
        if p['characters'] or p['scenes'] or p['shots'] or p['jobs']:
            raise AssertionError('Drop unexpectedly created a generation task or asset')
        report['originalBytesPreserved'] = True
        report['kinds'] = kinds
        window.page.runJavaScript("""JSON.stringify((()=>{const images=[...document.querySelectorAll('.media-attachment img')];
            return {ready:document.querySelectorAll('.media-attachment').length===2 && images.length===1 && images[0].naturalWidth>0};})())""", inspect_ui)
    except Exception as error:
        checking = False
        finish(error)


timer = QTimer()
timer.timeout.connect(poll)
timer.start(120)
app.exec()
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
