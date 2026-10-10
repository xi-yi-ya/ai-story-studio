/** Requires a real XY Studio --debug-port 9225. There is no mock browser server. */
import {test,expect,chromium, type Browser,type Page} from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs/promises';
let browser:Browser,page:Page,root:string,original:string;
let actor:string,scene:string,shot:string;
test.describe.configure({mode:'serial'});
async function rpc(command:string,payload:Record<string,unknown>={}){
 return page.evaluate(async([command,payload])=>await (document.querySelector('#app') as any).__vue_app__.config.globalProperties.$pinia._s.get('studio').api(command,payload),[command,payload] as const);
}
async function state(){return rpc('bootstrap') as Promise<any>}
test.beforeAll(async()=>{
 browser=await chromium.connectOverCDP(process.env.XY_CDP || 'http://127.0.0.1:9225',{noDefaults:true});
 page=browser.contexts()[0]!.pages()[0]!;
 await expect(page.getByRole('button',{name:/保存项目/})).toBeVisible();
 original=(await state()).project.root;
 root=path.resolve('../local-data','v030-ui-'+Date.now());
 await rpc('project.new',{path:root,title:'Vue 真实桌面验收'});
});
test.afterAll(async()=>{if(original)await rpc('project.open',{path:original});await browser?.close()});
test('new empty project, role and scene edit/import are persisted',async()=>{
 await page.getByRole('button',{name:'角色资产',exact:true}).click();
 await page.getByRole('button',{name:'创建角色',exact:true}).click();
 await page.getByLabel('名称',{exact:true}).fill('Vue 测试角色');
 await page.getByLabel('描述',{exact:true}).fill('测试角色描述');
 await page.getByRole('button',{name:'确认创建',exact:true}).click();
 actor=(await state()).project.assets[0].id;
 await page.getByRole('button',{name:'场景资产',exact:true}).click();
 await page.getByRole('button',{name:'创建场景',exact:true}).click();
 await page.getByLabel('名称',{exact:true}).fill('Vue 测试场景');
 await page.getByLabel('描述',{exact:true}).fill('测试场景描述');
 await page.getByRole('button',{name:'确认创建',exact:true}).click();
 scene=(await state()).project.assets.find((a:any)=>a.kind==='scenes').id;
 const reference=path.resolve('../local-data/XY-Studio-v030-compat/assets/b1463e53334345328a91dc047816aec3.png');
 await rpc('asset.import',{id:actor,paths:[reference]});await rpc('asset.import',{id:scene,paths:[reference]});
 expect(JSON.parse(await fs.readFile(path.join(root,'project.json'),'utf8')).schema).toBe(1);
 await page.getByRole('button',{name:'角色资产',exact:true}).click();
 const card=page.getByTestId('asset-'+actor);await card.click({button:'right'});
 await page.getByRole('menuitem',{name:'编辑资料'}).click();
 await page.getByLabel('名称',{exact:true}).fill('Vue 角色改名');await page.getByLabel('描述',{exact:true}).fill('长描述。'.repeat(120));
 await page.getByRole('button',{name:'保存修改',exact:true}).click();
 expect((await state()).project.assets.find((a:any)=>a.id===actor).name).toBe('Vue 角色改名');
});
test('double click image, zoom, history and right-click context',async()=>{
 const card=page.getByTestId('asset-'+actor);
 await card.locator('.asset-image').dblclick();await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('button',{name:'放大图片',exact:true}).click();await expect(page.locator('.preview-toolbar')).toContainText('125%');
 await page.keyboard.press('Escape');
 await card.getByRole('button',{name:/历史版本/}).click();await expect(page.locator('.version-card')).toHaveCount(1);
 await page.getByRole('button',{name:'设为当前版本',exact:true}).click();await page.keyboard.press('Escape');
 await card.click({button:'right'});await page.getByRole('menuitem',{name:'发送给 AI'}).click();
 await expect(page.locator('.context-banner')).toContainText('Vue 角色改名');
 expect((await state()).contextIds).toContain(actor);
});
test('shot numbering, real associations, timeline, folding and media mode boundaries',async()=>{
 await page.getByRole('button',{name:'分镜工作区',exact:true}).click();
 await page.getByRole('button',{name:'添加镜头',exact:true}).first().click();
 shot=(await state()).project.shots[0].id;
 await expect(page.getByTestId('shot-'+shot)).toContainText('分镜 1');
 await page.getByRole('button',{name:'关联镜头1素材',exact:true}).click();
 await page.locator('.link-option').first().click();await page.locator('.link-option').nth(1).click();
 await page.getByRole('button',{name:'保存关联',exact:true}).click();
 expect((await state()).project.shots[0].assetIds).toEqual([actor,scene]);
 await page.getByRole('button',{name:'折叠镜头1',exact:true}).click();await expect(page.getByTestId('shot-'+shot).locator('.shot-body')).toHaveCount(0);
 await page.getByRole('button',{name:/定位镜头1/}).click();await expect(page.getByTestId('shot-'+shot).locator('.shot-body')).toBeVisible();
 await page.getByTestId('shot-'+shot).getByRole('button',{name:'生成图片',exact:true}).click();
 const imageModes=await page.getByLabel('生成工作流').locator('option').evaluateAll(o=>o.map(v=>(v as HTMLOptionElement).value));
 expect(imageModes).toContain('upscale');expect(imageModes.every(v=>!v.startsWith('h3'))).toBeTruthy();
 await page.getByLabel('生成工作流').selectOption('upscale');await expect(page.getByLabel('放大倍数')).toBeVisible();await expect(page.getByLabel('H3 时长')).toHaveCount(0);
 await page.getByRole('button',{name:'取消生成',exact:true}).click();
 await page.getByTestId('shot-'+shot).getByRole('button',{name:'生成视频',exact:true}).click();
 const videoModes=await page.getByLabel('生成工作流').locator('option').evaluateAll(o=>o.map(v=>(v as HTMLOptionElement).value));
 expect(videoModes).toHaveLength(4);expect(videoModes.every(v=>v.startsWith('h3'))).toBeTruthy();
 await expect(page.getByLabel('H3 时长')).toBeVisible();await expect(page.getByLabel('放大倍数')).toHaveCount(0);
 await page.getByRole('button',{name:'取消生成',exact:true}).click();
});
test('queue parameters and cancellation persist, last prompt restored, no fake progress',async()=>{
 await rpc('queue.toggle');
 await page.getByTestId('shot-'+shot).getByRole('button',{name:'生成图片',exact:true}).click();
 await page.getByLabel('生成提示词').fill('界面测试提示词，实际加入暂停队列');await page.getByLabel('种子').fill('9223372036854775807');
 await page.getByRole('button',{name:'加入生成队列',exact:true}).click();
 let s=await state();expect(s.project.tasks[0].status).toBe('new');expect(s.project.tasks[0].progress).toBeNull();expect(s.project.tasks[0].generation.seed).toBe('9223372036854775807');
 await page.getByRole('button',{name:'任务与历史',exact:true}).click();await expect(page.locator('.mini-progress')).toHaveCount(0);
 await page.getByRole('button',{name:'取消',exact:true}).click();expect((await state()).project.tasks[0].status).toBe('cancelled');
 await page.getByRole('button',{name:'分镜工作区',exact:true}).click();await page.getByTestId('shot-'+shot).getByRole('button',{name:'生成图片',exact:true}).click();
 await expect(page.getByLabel('生成提示词')).toHaveValue('界面测试提示词，实际加入暂停队列');await page.getByRole('button',{name:'取消生成',exact:true}).click();
 await page.getByRole('button',{name:/保存项目/}).click();
 await rpc('project.open',{path:original});await rpc('project.open',{path:root});
 s=await state();expect(s.project.assets).toHaveLength(2);expect(s.project.shots[0].assetIds).toEqual([actor,scene]);expect(s.project.tasks[0].status).toBe('cancelled');
});
test('old real H3 video plays, seeks and retains history in its original shot',async()=>{
 await rpc('project.open',{path:path.resolve('../local-data/XY-Studio-v030-compat')});
 await page.getByRole('button',{name:'分镜工作区',exact:true}).click();
 const video=page.locator('video').first();await expect(video).toBeVisible();
 await page.waitForFunction(()=>document.querySelector('video')!.readyState>=2);
 const before=(await state()).project.shots.length;
 await page.locator('.big-play').first().click();await page.waitForFunction(()=>document.querySelector('video')!.currentTime>.2);
 await page.getByRole('button',{name:'暂停视频',exact:true}).first().click();
 await page.getByLabel('视频进度',{exact:true}).first().fill('1');
 expect(await video.evaluate(v=>v.currentTime)).toBeGreaterThan(.9);
 expect(await video.evaluate(v=>v.error)).toBeNull();
 await page.getByTestId('shot-'+(await state()).project.shots[0].id).getByRole('button',{name:/历史版本/}).nth(1).click();
 expect((await state()).project.shots.length).toBe(before);await expect(page.locator('.inline-history')).toBeVisible();
});
test('Agent import review and retry use real reactive parameter data without cloning errors',async()=>{
 await rpc('project.open',{path:root});
 const s=await state();
 const bundle=path.join(root,'agent-review.json');
 await fs.writeFile(bundle,JSON.stringify({project_id:s.project.id,provider:'integration fixture',message:{role:'assistant',content:'生成参数待审阅',tool_calls:[{id:'ui-approve',type:'function',function:{name:'generate',arguments:JSON.stringify({target:shot,mode:'qwen',prompt:'审阅用提示词',references:[]})}}]}}));
 await rpc('agent.import',{path:bundle});
 await page.getByRole('button',{name:'审阅操作',exact:true}).click();
 await expect(page.getByLabel('生成提示词')).toHaveValue('审阅用提示词');
 await page.getByRole('button',{name:'取消生成',exact:true}).click();
 expect((await state()).review).toBeNull();
 await page.getByRole('button',{name:'任务与历史',exact:true}).click();await page.getByRole('button',{name:'再次生成',exact:true}).click();
 await expect(page.getByLabel('生成提示词')).toHaveValue('界面测试提示词，实际加入暂停队列');
 await page.getByRole('button',{name:'取消生成',exact:true}).click();
});
test('1920/2K/4K and browser zoom keep media, chat and navigation usable',async()=>{
 await rpc('project.open',{path:path.resolve('../local-data/XY-Studio-v030-compat')});
 await page.getByRole('button',{name:'分镜工作区',exact:true}).click();
 for(const [width,height] of [[1920,1080],[2560,1440],[3840,2160],[1024,768]]){
  await page.setViewportSize({width:width!,height:height!});
  await expect(page.getByRole('button',{name:'分镜工作区',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 }
 await page.setViewportSize({width:1600,height:950});
 await page.evaluate(()=>document.documentElement.style.zoom='1.25');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.evaluate(()=>document.documentElement.style.zoom='1');
 await page.screenshot({path:process.env.XY_SCREENSHOT || '../docs/screenshots/v030-storyboard.png'});
});
test('many real shot cards and empty search do not break the workbench',async()=>{
 await rpc('project.open',{path:root});
 for(let i=0;i<40;i++)await rpc('asset.add',{kind:'shots',description:'较长的镜头描述。'.repeat(25)});
 await page.getByRole('button',{name:'分镜工作区',exact:true}).click();await expect(page.locator('.shot-card')).toHaveCount(41);
 await page.getByLabel('搜索镜头').fill('完全不存在的名称');await expect(page.locator('.shot-card')).toHaveCount(0);await expect(page.getByText('没有找到这个镜头',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'清除搜索',exact:true}).click();await expect(page.locator('.shot-card')).toHaveCount(41);
 await page.getByRole('button',{name:'折叠全部',exact:true}).click();await expect(page.locator('.shot-body')).toHaveCount(0);
 await page.getByRole('button',{name:/定位镜头41/}).click();await expect(page.locator('.shot-body')).toHaveCount(1);
});
