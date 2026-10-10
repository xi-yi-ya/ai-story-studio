"""Resolve Windows file drops in the desktop host, never browser fake paths."""
import json
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QWidget


class NativeFileDrop(QObject):
    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def eventFilter(self, watched, event):
        if not isinstance(watched, QWidget) or not (watched is self.view or self.view.isAncestorOf(watched)):
            return False
        if event.type() == QEvent.DragLeave:
            self.view.page().runJavaScript("document.querySelectorAll('.drop-active').forEach(e=>e.classList.remove('drop-active'))")
            return False
        if event.type() not in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop): return False
        urls = event.mimeData().urls()
        if not urls or not all(url.isLocalFile() for url in urls): return False
        position = self.view.mapFrom(watched, event.position().toPoint()) if watched is not self.view else event.position().toPoint()
        zoom = self.view.zoomFactor()
        detail = {'x':position.x()/zoom, 'y':position.y()/zoom}
        if event.type() == QEvent.Drop:
            detail['paths'] = [url.toLocalFile() for url in urls]
            code = "window.dispatchEvent(new CustomEvent('xy-files-dropped',{detail:"+json.dumps(detail)+"}));document.querySelectorAll('.drop-active').forEach(e=>e.classList.remove('drop-active'))"
        else:
            code = "document.querySelectorAll('.drop-active').forEach(e=>e.classList.remove('drop-active'));document.elementFromPoint("+str(detail['x'])+","+str(detail['y'])+")?.closest('[data-media-drop]')?.classList.add('drop-active')"
        self.view.page().runJavaScript(code)
        event.acceptProposedAction()
        return True
