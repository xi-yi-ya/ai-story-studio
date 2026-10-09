"""Decode an actual first video frame; cache independently of project metadata."""
import hashlib
from pathlib import Path
import av

def video_poster(project,relative):
    source=project.file(relative)
    stat=source.stat()
    key=hashlib.sha256(f'{relative}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()
    target=project.file('previews/'+key+'.png')
    if not target.exists():
        target.parent.mkdir(exist_ok=True)
        with av.open(str(source)) as container:
            frame=next(container.decode(video=0),None)
            if frame is None:raise ValueError('视频没有可解码帧')
            img=frame.to_image();img.thumbnail((480,270));img.save(target)
    return target.relative_to(project.root).as_posix()
