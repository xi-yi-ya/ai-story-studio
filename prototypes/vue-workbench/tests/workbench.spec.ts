import { test, expect } from "@playwright/test";
test.beforeEach(async ({ page }) => {
  await page.goto("/");
});
test("AI review queues a version on the same shot and survives reload", async ({
  page,
}) => {
  const shot = page.getByTestId("shot-shot-02");
  await page.getByRole("button", { name: "审阅并生成", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("一把伞的距离");
  await page.getByRole("button", { name: "确认并模拟生成" }).click();
  await expect(shot).toContainText("生成中");
  await expect(shot).toContainText("已完成", { timeout: 10000 });
  await expect(page.locator(".shot-card")).toHaveCount(3);
  await shot.getByRole("button", { name: "历史版本" }).first().click();
  await expect(shot.locator(".history-item")).toHaveCount(3);
  await expect(page.locator(".suggestion-card")).toContainText("已确认");
  await page.reload();
  await expect(page.locator(".shot-card")).toHaveCount(3);
  await page
    .getByTestId("shot-shot-02")
    .getByRole("button", { name: "历史版本" })
    .first()
    .click();
  await expect(
    page.getByTestId("shot-shot-02").locator(".history-item"),
  ).toHaveCount(3);
});
test("timeline selects, unfolds and targets the AI context", async ({
  page,
}) => {
  await page.getByRole("button", { name: "定位镜头3 留一盏灯" }).click();
  await expect(page.getByTestId("shot-shot-03")).toHaveClass(/selected/);
  await expect(page.getByRole("button", { name: "折叠镜头3" })).toBeVisible();
  await expect(page.locator(".context-banner")).toContainText("留一盏灯");
  await page.getByRole("button", { name: "收起 AI 助手" }).click();
  await page.getByRole("button", { name: "展开 AI 助手" }).click();
  await expect(page.locator(".context-banner")).toContainText("留一盏灯");
});
test("asset context menu editing, versions and image enlargement work", async ({
  page,
}) => {
  await page.getByRole("button", { name: "角色资产", exact: true }).click();
  const card = page.getByTestId("asset-char-rain");
  await card.click({ button: "right" });
  await page.getByRole("menuitem", { name: "编辑资料" }).click();
  await page.getByLabel("名称", { exact: true }).fill("小雨 · 新设定");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(card).toContainText("小雨 · 新设定");
  await card.getByRole("button", { name: "小雨 · 新设定历史版本" }).click();
  await page.getByRole("button", { name: "设为当前版本" }).last().click();
  await page.getByRole("button", { name: "关闭弹窗" }).click();
  await card.getByRole("button", { name: "查看小雨 · 新设定大图" }).dblclick();
  await expect(page.getByRole("dialog")).toContainText("素材预览");
  await page.getByRole("button", { name: "放大图片" }).click();
  await expect(page.locator(".preview-toolbar")).toContainText("125%");
});
test("cancelled review does not execute; reject stays rejected", async ({
  page,
}) => {
  await page.getByRole("button", { name: "审阅并生成", exact: true }).click();
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.locator(".suggestion-card")).toContainText("待审阅");
  await page.getByRole("button", { name: "拒绝", exact: true }).click();
  await expect(page.locator(".suggestion-card")).toContainText("已拒绝");
  await page.getByRole("button", { name: "任务与历史", exact: true }).click();
  await expect(page.locator(".task-row")).toHaveCount(1);
});
test("queue pause, cancel and explicit recovery preserve ownership", async ({
  page,
}) => {
  await page.getByRole("button", { name: "任务与历史", exact: true }).click();
  await page.getByRole("button", { name: "暂停模拟队列" }).click();
  await page.getByRole("button", { name: "分镜工作区", exact: true }).click();
  await page
    .getByTestId("shot-shot-01")
    .getByRole("button", { name: "生成视频", exact: true })
    .click();
  await expect(page.getByLabel("生成工作流").locator("option")).toHaveCount(2);
  await page.getByRole("button", { name: "确认并模拟生成" }).click();
  await expect(page.getByTestId("shot-shot-01")).toContainText("等待生成");
  await page.reload();
  await page.getByRole("button", { name: "任务与历史", exact: true }).click();
  await page.getByRole("button", { name: "继续模拟队列" }).click();
  await expect(page.locator(".task-row").first()).toContainText("生成中");
  await page
    .locator(".task-row")
    .first()
    .getByRole("button", { name: "取消", exact: true })
    .click();
  await expect(page.locator(".task-row").first()).toContainText("已取消");
  await expect(page.locator(".task-row")).toHaveCount(2);
});
test("new project empty states, new assets and shot association persist", async ({
  page,
}) => {
  await page.getByRole("button", { name: "项目", exact: true }).click();
  await page.getByRole("button", { name: "新建项目", exact: true }).click();
  await page.getByLabel("项目名称").fill("空故事验证");
  await page.getByRole("button", { name: "创建原型项目" }).click();
  await expect(page.getByText("你的第一个镜头", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "角色资产", exact: true }).click();
  await page.getByRole("button", { name: "创建角色", exact: true }).click();
  await page.getByLabel("名称", { exact: true }).fill("长名称角色".repeat(12));
  await page.getByLabel("描述", { exact: true }).fill("长描述测试".repeat(400));
  await page.getByRole("button", { name: "确认创建" }).click();
  await expect(page.locator(".asset-card")).toHaveCount(1);
  await page.getByRole("button", { name: "分镜工作区", exact: true }).click();
  await page
    .getByRole("button", { name: "添加镜头", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "关联镜头1素材" }).click();
  await page.getByRole("dialog").getByRole("checkbox").check();
  await page.getByRole("button", { name: "保存关联" }).click();
  await expect(page.locator(".linked-item")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".linked-item")).toHaveCount(1);
});
test("chat, model and mock web toggle are usable with no external requests", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:5173")) requests.push(r.url());
  });
  await page.getByLabel("AI 模型").selectOption("DeepSeek Pro");
  await page.getByLabel("模拟联网").check();
  await page
    .getByLabel("给 AI 助手的消息")
    .fill("请只修改这个镜头的动作，保留服装与环境。".repeat(30));
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message.user")).toHaveCount(2);
  await expect(page.locator(".message.assistant")).toHaveCount(3);
  await page.getByRole("button", { name: "展开完整回复" }).click();
  await expect(page.getByRole("button", { name: "收起长回复" })).toBeVisible();
  expect(requests).toEqual([]);
});
for (const size of [
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
  { width: 3840, height: 2160 },
  { width: 1280, height: 720 },
  { width: 900, height: 700 },
  { width: 640, height: 800 },
  { width: 400, height: 700 },
]) {
  test(`layout ${size.width}x${size.height} has no document overflow`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.reload();
    const dimensions = await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
      height: innerHeight,
      body: document.documentElement.scrollHeight,
      workspace: document.querySelector(".workspace-scroll")?.scrollWidth,
      available: document.querySelector(".workspace-scroll")?.clientWidth,
    }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
    expect(dimensions.body).toBeLessThanOrEqual(dimensions.height);
    expect(dimensions.workspace).toBeLessThanOrEqual(dimensions.available!);
    if (size.width >= 1920)
      await expect(
        page.getByRole("heading", { name: "AI 助手", exact: true }),
      ).toBeVisible();
    await page.screenshot({ path: `docs/screenshots/shots-${size.width}.png` });
  });
}
test("120 long-text shots remain usable and are kept in their own cards", async ({
  page,
}) => {
  await page.getByRole("button", { name: "项目", exact: true }).click();
  await page.getByRole("button", { name: "打开 120 镜头示例" }).click();
  await expect(page.locator(".shot-card")).toHaveCount(120);
  await page
    .getByRole("button", { name: "定位镜头120 长项目镜头 120" })
    .click();
  await expect(page.locator(".shot-card").last()).toHaveClass(/selected/);
  await expect(page.getByRole("button", { name: "折叠镜头120" })).toBeVisible();
  await page.getByRole("button", { name: "折叠全部", exact: true }).click();
  await page.getByRole("button", { name: "展开全部", exact: true }).click();
  await expect(page.locator(".shot-body")).toHaveCount(120);
  const width = await page.evaluate(() => [
    innerWidth,
    document.documentElement.scrollWidth,
  ]);
  expect(width[1]).toBeLessThanOrEqual(width[0]!);
});
test("capture asset, scene, tasks and review pages without console errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const [name, file] of [
    ["角色资产", "characters"],
    ["场景资产", "scenes"],
    ["任务与历史", "tasks"],
    ["项目", "projects"],
    ["设置", "settings"],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await page.screenshot({ path: `docs/screenshots/${file}-1920.png` });
  }
  await page.getByRole("button", { name: "分镜工作区", exact: true }).click();
  await page.getByRole("button", { name: "审阅并生成", exact: true }).click();
  await page.screenshot({ path: "docs/screenshots/review-1920.png" });
  expect(errors).toEqual([]);
});

for (const scale of [1.25, 1.5, 2]) {
  test(`equivalent ${scale * 100}% desktop zoom remains usable`, async ({
    browser,
  }) => {
    const context = await browser.newContext({
      viewport: {
        width: Math.floor(1920 / scale),
        height: Math.floor(1080 / scale),
      },
      deviceScaleFactor: scale,
    });
    const page = await context.newPage();
    try {
      await page.goto("http://127.0.0.1:5173");
      const dimensions = await page.evaluate(() => ({
        document: document.documentElement.scrollWidth,
        viewport: innerWidth,
        content: document.querySelector(".workspace-scroll")!.scrollWidth,
        available: document.querySelector(".workspace-scroll")!.clientWidth,
      }));
      expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
      expect(dimensions.content).toBeLessThanOrEqual(dimensions.available);
      await page.getByRole("button", { name: "角色资产", exact: true }).click();
      await expect(page.getByTestId("asset-char-rain")).toBeVisible();
      await page.screenshot({
        path: `docs/screenshots/zoom-${scale * 100}.png`,
      });
    } finally {
      await context.close();
    }
  });
}

test("all pages retain their controls in narrow layouts", async ({ page }) => {
  for (const size of [
    { width: 900, height: 700 },
    { width: 640, height: 800 },
    { width: 400, height: 700 },
  ]) {
    await page.setViewportSize(size);
    await page.reload();
    for (const name of [
      "项目",
      "角色资产",
      "场景资产",
      "分镜工作区",
      "任务与历史",
      "设置",
    ]) {
      await page.getByRole("button", { name, exact: true }).click();
      const size = await page
        .locator(".workspace-scroll")
        .evaluate((el) => [el.scrollWidth, el.clientWidth]);
      expect(size[0]).toBeLessThanOrEqual(size[1]!);
    }
    await page.getByRole("button", { name: "AI 助手", exact: true }).click();
    await expect(page.getByLabel("给 AI 助手的消息")).toBeVisible();
    await page.getByRole("button", { name: "收起 AI 助手" }).click();
  }
});

test("mock video playback and scrubbing controls are functional", async ({
  page,
}) => {
  const player = page.getByTestId("shot-shot-01").locator(".video-preview");
  await player.getByRole("button", { name: "播放模拟预览" }).click();
  await expect(player.getByRole("button", { name: "暂停预览" })).toBeVisible();
  await expect
    .poll(async () => Number(await player.getByLabel("预览进度").inputValue()))
    .toBeGreaterThan(0);
  await player.getByRole("button", { name: "暂停预览" }).click();
  await player.getByLabel("预览进度").press("ArrowRight");
  await expect(
    player.getByRole("button", { name: "播放预览", exact: true }),
  ).toBeVisible();
});
