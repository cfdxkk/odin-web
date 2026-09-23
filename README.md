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

- 40 秒三段镜头循环：飞船外观、SMC/战斗、NAV/航行。外观无尾焰，战斗展开武备和舰桥护甲，航行先收拢武备，再从真实喷口渐亮尾焰；30.8 秒开始点火，33.8–39 秒保持巡航推力。
- 按住时间轴暂停，松开恢复此前的播放意图。主动暂停后，拖动、切换模式或浏览器标签均不会恢复播放；空格暂停，R 回到开场。
- 自由探索：拖动旋转，滚轮或双指缩放，可独立展开/收拢武备。
- PC 高画质优先：2K PBR 贴图、真实倒角、环境遮蔽、4K 阴影及抗锯齿。流畅模式关闭阴影、环境遮蔽与泛光；窄屏和软件渲染器使用轻量模型。
- 尊重系统“减少动态效果”设置，初始暂停自动播放。

## 模型处理

源文件：`../Odin 建模/odin.blend`，未覆盖。

当前可编辑补完模型：[`assets/blender/odin_articulated_v0.2.1.blend`](assets/blender/odin_articulated_v0.2.1.blend)，修复 13 个喷口的局部原点，已另存到此仓库。早期模型仍保留。

甄别保留当前可见奥丁组件与炮塔集合实例，排除 `perseus`、隐藏旧版、原场景灯光、相机和 VFX。补充缺失的右侧对称外壳、主炮舱盖倒角、推进器内芯及喷口环、舰桥窗、导航灯和舰体编号。沿用原始材质分区和内嵌磨损贴图，将游戏节点材质转换为 glTF PBR。

这是面向外观展示的粉丝艺术补完，不是完整可游览内装，也不是官方生产级资产。

高画质模型约 242 万三角面，轻量版约 86 万三角面。保留 119 个静态机械关节，含上下主炮、副炮、防御炮、舰桥四联炮折臂和 45 片舰桥护甲。贴图内嵌，动画片段数为 0。实际尺寸与网格明细见 `public/models/asset-manifest.json`。

## 主要源码

- `app/app.vue`：Nuxt 页面、控件、创作说明与来源。
- `app/lib/odin-scene.ts`：摄像机轨迹、实时动画、WebGL 渲染及资源释放。
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
