const type = 'application/x-xy-studio-media';
export function dragMedia(event: DragEvent, file: string | undefined, projectId: string) {
  if (!file || !event.dataTransfer) {
    event.preventDefault();
    return;
  }
  event.dataTransfer.effectAllowed = 'copy';
  event.dataTransfer.setData(type, JSON.stringify({ file, projectId }));
}
export function allowMediaDrop(event: DragEvent) {
  if (event.dataTransfer?.types.includes(type) || event.dataTransfer?.types.includes('Files'))
    event.preventDefault();
}
export function droppedMedia(event: DragEvent, projectId: string): string | null {
  const wire = event.dataTransfer?.getData(type);
  if (!wire) return null;
  event.preventDefault();
  event.stopPropagation();
  const data = JSON.parse(wire);
  if (data.projectId !== projectId) throw new Error('请使用当前项目的素材');
  if (typeof data.file !== 'string') throw new Error('拖入素材无效');
  return data.file;
}
