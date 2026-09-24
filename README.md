# ODIN — Nuxt 粉丝艺术展示站

以提供的 `odin.blend` 为基础制作的奥丁外观展示。Nuxt 4 + Vue 3 + Three.js。所有镜头、环绕、炮塔升降、舱盖运动与推进器效果都在浏览器中计算；GLB 不含 Blender 动画、相机或灯光。

## 运行

使用 Node.js 24.11+（本机随 Codex 附带的 Node 24.19 可用），或 Node 22.19+。

```bash
npm install
npm run dev
```

打开 http://127.0.0.1:3000 。Windows 可运行 `启动预览.ps1`，脚本会优先使用本机可用的兼容 Node。

```bash
npm test
npm run verify:asset
npm run generate
```

静态部署目录为 `.output/public`。字体、Draco 解码器、贴图与模型均在本地，不依赖 CDN；无需 Blender 即可运行网站。不能直接以 `file://` 打开，需通过 HTTP 服务访问。

## 交互

- 60 秒镜头序列：飞船外观、SCM/战斗、NAV/航行。镜头有距离、高度和观察点的变化，经过主炮、舰桥及后方。展开和收起各 6.5 秒；38.5 秒起渐亮尾焰，41–58 秒保持航行推力。主炮和单联炮不巡转；完全展开后，双联、四联副炮缓慢转动。
- 按住时间轴暂停，松开恢复此前的播放意图。主动暂停后，拖动、切换模式或浏览器标签均不会恢复播放；空格暂停，电影视角下 R 回到开场。
- 自由探索：左键旋转、右键平移、滚轮或双指缩放，可切换 SCM/战斗和 NAV/航行；NAV 收起武备后也会点火，切回 SCM 先熄火再展开。没有复位按钮，R 也不会复位自由视角。
- PC 高画质优先：2K PBR 贴图、真实倒角、环境遮蔽、4K 阴影及抗锯齿。灰色、炭灰与橙色涂装使用修正后的贴图，尾焰独立发光；取消全屏泛光，避免船体亮点放大。流畅模式关闭阴影与环境遮蔽；窄屏和软件渲染器使用轻量模型。
- 尊重系统“减少动态效果”设置，初始暂停自动播放。

## 模型处理

源文件：`../Odin 建模/odin.blend`，未覆盖。

当前可编辑补完模型：[`assets/blender/odin_articulated_v0.7.0.blend`](assets/blender/odin_articulated_v0.7.0.blend)。每座主炮井有五块护甲：两块前段长板、炮罩下缘两块后段补片，以及微抬后向船艏滑动的前端短盖板。v0.7 从 v0.5 恢复完整 `holo.001` / `holo.013` 船壳，后段补片独立填入旋转炮罩下缘与固定船壳内唇之间的空缺，不再切下船壳充当活动板。主板后缘按闭合炮罩的实际轮廓仿形，外缘贴合原有内唇，并保留背部的锯齿拼缝。

主板总侧移/下沉行程缩短为背部 10.5/17.6、腹部 10/16.1 个模型源坐标单位；此前对应为 16.4/23.2 和 16.4/23。左右外炮管沿各自炮轴增加至 16 单位的完整伸缩行程，收拢端深入套筒，SCM 完全展开端的位置保持不变。护甲让位后再升起三联炮和炮座，收起时先回收炮管与炮座，再闭合护甲。单联炮护罩、舰桥装甲与原始尾舱门沿用独立关节。早期模型仍保留。

甄别保留当前可见奥丁组件与炮塔集合实例，排除 `perseus`、隐藏旧版、原场景灯光、相机和 VFX。补充缺失的右侧对称外壳、主炮舱盖倒角、推进器内芯及喷口环、舰桥窗、导航灯和舰体编号。沿用原始材质分区和内嵌磨损贴图，将游戏节点材质转换为 glTF PBR。

这是面向外观展示的粉丝艺术补完，不是完整可游览内装，也不是官方生产级资产。

高画质模型约 240 万三角面，轻量版约 88 万三角面。保留 132 个静态关节，含上下主炮、副炮、防御炮、舰桥四联炮滑轨、10 块主炮平移护甲、4 个外炮管伸缩段、6 组单联炮护罩、45 片舰桥护甲和固定尾舱门。贴图内嵌，动画片段数为 0。实际尺寸与网格明细见 `public/models/asset-manifest.json`。动作静帧和参考说明见 [`docs/review/`](docs/review/README.md)。

## 主要源码

- `app/app.vue`：Nuxt 页面、控件、创作说明与来源。
- `app/lib/odin-scene.ts`：摄像机轨迹、实时动画、WebGL 渲染及资源释放。
- `app/lib/odin-camera.ts`：连续的镜头距离、高度、方位及观察点轨迹。
- `app/lib/odin-rig.ts`：所有机械关节的程序动画与动作顺序。
- `app/lib/odin-motion.ts`：模式时间轴、尾焰联锁和暂停意图。
- `app/components/OdinScene.client.vue`：浏览器组件生命周期。
- `app/assets/main.css`：桌面、移动端视觉布局。
- `tools/inspect_blend.py`、`audit_model.py`：原文件审计。
- `tools/extract_odin.py`：剥离奥丁并保留集合实例。
- `tools/finish_model.py`：材质转换和外观补完，另存独立 Blender 文件。
- `tools/optimize_model.py`：合批、Draco 压缩和轻量模型导出。
- `tools/build_articulated_asset.py`、`export_articulated_asset.py`：新版静态关节重建、贴图补完及无动画导出。
- `tools/repair_engine_origins.py`：保持网格位置不变，恢复 13 个喷口的局部原点，另存新版 Blender 文件。
- `tools/revise_mechanisms_v03.py`：在 v0.2.1 副本中重建侧翻盖、四联炮支架、尾舱门和涂装，另存 v0.3.0。
- `tools/revise_mechanisms_v04.py`：在 v0.3.0 副本中恢复原始护罩、舰桥装甲、尾舱门并修正炮塔关节，另存 v0.4.0；读取 `inspect_articulation.py` 生成的原模型审计结果。
- `tools/revise_main_battery_v05.py`：从原模型舱盖轮廓重建整片平移护甲，另存 v0.5.0；不覆盖早期版本。
- `tools/revise_main_battery_v06.py`：在 v0.5.0 副本上制作多边形侧板、前端短楔形盖板、原船体后段窄板和外侧避让导轨，另存 v0.6.0。
- `tools/revise_main_battery_v07.py`、`main_armor_v07_boundaries.json`：从完整 v0.5.0 副本及实测边界重建贴合接缝的五块护甲和独立后补片，缩短主板导轨并加深外炮管收拢行程，另存 v0.7.0；不切割固定船壳。
- `tools/check_main_clearance.py`：在 101 个实际 JS 姿态上检测十块主炮护甲与炮管、炮罩、炮座三角网格的相交。
- `tools/review_rig_poses.mjs`、`render_rig_review.py`：用真实 JS 关节变换生成静态检查图，不生成动画片段。
- `tools/verify-asset.mjs`：GLB 结构、动画排除、部件与贴图验证。

模型工具需通过 Blender 5.1 的后台 Python 运行。`work/` 为本地审计和静帧检查中间文件，不属于网站部署内容。`render_completed.py` 仅生成检查静帧；这些静帧不驱动网页动画。

## 来源

- [动画灵感：Space Tech](https://www.youtube.com/watch?v=EKvbJh87rpY)
- [官方模型与开发者展示](https://www.youtube.com/watch?v=CFoQp6wRjPo)
- [RSI Anvil Odin 概念页面](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin)
- [官方 Made by the Community 标识说明](https://support.robertsspaceindustries.com/hc/en-us/articles/360006895793-Star-Citizen-Fankit-and-Fandom-FAQ)

## 版本流程

GitHub 仓库为 `cfdxkk/odin-web`。每次修改均通过独立分支和 PR，开放审核版本打不可移动的 `vX.Y.Z-rc.N` 标签；`main` 保留已审核版本。网站私有预览可用于查看 PR 候选版本。

站点明确标注非官方 Fan Art。Star Citizen、Anvil、Odin 及概念艺术归各自权利人所有；此工程不包含独立的官方资产再授权。
