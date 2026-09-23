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
npm run verify:asset
npm run generate
```

静态部署目录为 `.output/public`。字体、Draco 解码器、贴图与模型均在本地，不依赖 CDN；无需 Blender 即可运行网站。不能直接以 `file://` 打开，需通过 HTTP 服务访问。

## 交互

- 40 秒四段镜头循环：初见、武备、推进、远航。
- 暂停、时间轴拖动、章节跳转；空格暂停，R 回到开场。
- 自由探索：拖动旋转，滚轮或双指缩放，可独立展开/收拢武备。
- 流畅模式关闭实时阴影与泛光。窄屏与软件渲染器使用轻量模型。
- 尊重系统“减少动态效果”设置，初始暂停自动播放。

## 模型处理

源文件：`../Odin 建模/odin.blend`，未覆盖。

补完模型：`../Odin 建模/odin_web_completed.blend`。

甄别保留当前可见奥丁组件与炮塔集合实例，排除 `perseus`、隐藏旧版、原场景灯光、相机和 VFX。补充缺失的右侧对称外壳、主炮舱盖倒角、推进器内芯及喷口环、舰桥窗、导航灯和舰体编号。沿用原始材质分区和内嵌磨损贴图，将游戏节点材质转换为 glTF PBR。

这是面向外观展示的粉丝艺术补完，不是完整可游览内装，也不是官方生产级资产。

完整外观模型约 75.4 万三角面；网页将静态几何合批为 18 个网格。轻量版约 25.6 万三角面。两版均有 14 个材质、7 张内嵌贴图，动画片段数为 0。明细见 `public/models/asset-manifest.json`。

## 主要源码

- `app/app.vue`：Nuxt 页面、控件、创作说明与来源。
- `app/lib/odin-scene.ts`：摄像机轨迹、实时动画、WebGL 渲染及资源释放。
- `app/components/OdinScene.client.vue`：浏览器组件生命周期。
- `app/assets/main.css`：桌面、移动端视觉布局。
- `tools/inspect_blend.py`、`audit_model.py`：原文件审计。
- `tools/extract_odin.py`：剥离奥丁并保留集合实例。
- `tools/finish_model.py`：材质转换和外观补完，另存独立 Blender 文件。
- `tools/optimize_model.py`：合批、Draco 压缩和轻量模型导出。
- `tools/verify-asset.mjs`：GLB 结构、动画排除、部件与贴图验证。

模型工具需通过 Blender 5.1 的后台 Python 运行。`work/` 为本地审计和静帧检查中间文件，不属于网站部署内容。`render_completed.py` 仅生成检查静帧；这些静帧不驱动网页动画。

## 来源

- [动画灵感：Space Tech](https://www.youtube.com/watch?v=EKvbJh87rpY)
- [官方模型与开发者展示](https://www.youtube.com/watch?v=CFoQp6wRjPo)
- [RSI Anvil Odin 概念页面](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin)

站点明确标注非官方 Fan Art。Star Citizen、Anvil、Odin 及概念艺术归各自权利人所有；此工程不包含独立的官方资产再授权。
