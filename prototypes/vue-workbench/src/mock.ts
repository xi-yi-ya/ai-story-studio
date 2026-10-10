import type { Asset, ProjectState, Version } from "./types";
const version = (
  id: string,
  media: Version["media"],
  kind: Version["kind"] = "image",
  label = "当前版本",
): Version => ({
  id,
  media,
  kind,
  label,
  prompt: "保持角色外观和画面光线，呈现雨夜便利店安静、温暖的氛围。",
  time: "今天 15:24",
});
const assets: Asset[] = [
  {
    id: "char-rain",
    name: "小雨",
    kind: "characters",
    description:
      "17 岁的高中生，安静温柔。穿着黄色雨衣，总在雨天带着一把透明伞。",
    versions: [
      version("rain-v1", "girl"),
      version("rain-v2", "arrival", "image", "雨夜参考"),
    ],
    current: "rain-v1",
    tags: ["主角", "黄色雨衣"],
  },
  {
    id: "char-clerk",
    name: "店员",
    kind: "characters",
    description: "二十多岁的便利店店员，友善、耐心，总是带着微笑。",
    versions: [version("clerk-v1", "clerk")],
    current: "clerk-v1",
    tags: ["配角", "便利店制服"],
  },
  {
    id: "scene-outside",
    name: "便利店外景",
    kind: "scenes",
    description:
      "雨夜的街道，湿润的地面倒映着便利店的灯光，城市在雨中显得安静而温柔。",
    versions: [
      version("outside-v1", "outside"),
      version("outside-v2", "arrival", "image", "人物入画"),
    ],
    current: "outside-v1",
    tags: ["夜景", "雨天"],
  },
  {
    id: "scene-inside",
    name: "便利店内景",
    kind: "scenes",
    description:
      "温暖明亮的便利店内，货架整齐、灯光柔和，是城市中一处小小的避雨所。",
    versions: [version("inside-v1", "inside")],
    current: "inside-v1",
    tags: ["室内", "暖光"],
  },
];
export function demoProject(): ProjectState {
  return {
    id: "project-rain",
    name: "雨夜便利店",
    story:
      "雨夜，一个女孩走进便利店，与店员分享一把伞。一次平凡的相遇，让漫长的雨夜多了一点温暖。",
    updated: "今天 15:24",
    assets: structuredClone(assets),
    shots: [
      {
        id: "shot-01",
        name: "雨中的相遇",
        description:
          "雨夜，小雨撑着透明伞走向便利店。暖色灯光映在她的脸上，她放慢脚步，望向店内。",
        duration: 5,
        assetIds: ["char-rain", "scene-outside"],
        versions: [
          version("shot1-img1", "arrival"),
          version("shot1-img0", "outside", "image", "初稿"),
          version("shot1-vid1", "arrival", "video"),
        ],
        imageVersion: "shot1-img1",
        videoVersion: "shot1-vid1",
        collapsed: false,
      },
      {
        id: "shot-02",
        name: "一把伞的距离",
        description:
          "女孩走进店内，与店员交谈。她将伞轻轻放在门边，雨声隔着玻璃渐渐远去。",
        duration: 5,
        assetIds: ["char-rain", "char-clerk", "scene-inside"],
        versions: [
          version("shot2-img1", "conversation"),
          version("shot2-img0", "girl", "image", "构图探索"),
          version("shot2-vid1", "conversation", "video"),
        ],
        imageVersion: "shot2-img1",
        videoVersion: "shot2-vid1",
        collapsed: false,
      },
      {
        id: "shot-03",
        name: "留一盏灯",
        description:
          "两人一同望向窗外。便利店的灯光照亮积水，小雨把伞留给店员，微笑着推开门。",
        duration: 4,
        assetIds: ["char-rain", "scene-outside"],
        versions: [],
        imageVersion: null,
        videoVersion: null,
        collapsed: true,
      },
    ],
    tasks: [
      {
        id: "task-demo",
        targetId: "shot-02",
        targetName: "一把伞的距离",
        kind: "video",
        status: "done",
        progress: 100,
        prompt: "女孩与店员在温暖的便利店内交谈。",
        time: "15:24",
      },
    ],
    chat: [
      {
        id: "welcome",
        role: "assistant",
        text: "你好，我们继续这个雨夜的故事吧。选中一个镜头或素材，我会围绕它整理修改建议。",
        time: "15:25",
      },
      {
        id: "user-demo",
        role: "user",
        text: "把第二镜改成近景，保留衣服和光线。",
        time: "15:26",
        targetName: "一把伞的距离",
      },
      {
        id: "assistant-demo",
        role: "assistant",
        text: "好的，让我们把注意力放在小雨的表情上。保留黄色雨衣、温暖的室内灯光，以及窗外的蓝色雨夜。",
        time: "15:26",
        suggestion: {
          id: "suggest-demo",
          targetId: "shot-02",
          targetName: "一把伞的距离",
          prompt:
            "近景，女孩与店员轻声交谈。保留黄色雨衣与暖色室内光线，蓝色雨夜透过身后的玻璃，镜头缓缓推近。",
          status: "pending",
        },
      },
    ],
  };
}
export const mediaCrops: Record<string, [number, number, number, number]> = {
  arrival: [385, 219, 349, 122],
  conversation: [384, 429, 350, 120],
  girl: [486, 224, 174, 116],
  clerk: [329, 779, 140, 120],
  outside: [794, 778, 295, 135],
  inside: [1123, 778, 337, 135],
};
