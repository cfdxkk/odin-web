# ODIN MONOGRAPH — 雷霆，有形。

以现有奥丁三维模型为核心的互动设定集。纸色、石墨蚀刻和钴蓝排版构成四个独立画面：舰影、武备、舰内与图像档案。首页仅使用实时 3D，不放官方概念图。Nuxt 4 + Vue 3 + Three.js。

v0.26.0 使用原有静态几何和机械关节，重新设计渲染材质、取景与页面。原始 Blender 文件、版本化建模文件与 GLB 不变；GLB 含零动画片段。

## 运行与验证

使用 Node.js 24.11+ 或 Node 22.19+。

```bash
npm install
npm run dev
npm test
npm run verify:asset
npm run generate
```

开发地址为 http://127.0.0.1:3000；静态部署目录为 `.output/public`。字体、解码器、贴图与模型均本地提供，无 CDN 依赖。必须通过 HTTP 访问。

## 体验

- 四个可直接切换的设定集画面，以遮罩、排版错拍和镜头移动衔接。左右方向键翻页。
- 首页实时 3D：蚀刻、线稿、素模三种表现，柔和切换；有界缓转和指针视差。拖动旋转，滚轮缩放，右键平移。
- 武备篇自动展开机械；主炮、单联副炮、双联炮群、舰桥四联炮与推进系统共五个近观视角。钴蓝标记对应当前炮组，滑条控制完整收展行程。
- 显式暂停跨章节、材质、模式、页面可见性和滑条操作保持。拖动滑条仅临时暂停自动转动。空格切换缓转，支持系统减少动态效果及明确开启。
- 推进器在所有武备完全收拢后才点亮；舰桥护甲保持固定。可复位视角并保存 PNG 设定稿。
- 舰内四处空间、11 张精选图像；支持全幅查看、键盘切图、Esc 关闭、来源链接与概念配置索引。官方图仅在二级章节出现。
- 非官方粉丝作品。舰船与内部空间仍为概念资料，以 RSI 最终发布为准。

## 当前源码

- `app/app.vue`：四个画面、导航、暂停意图、控件与原生图像对话框。
- `app/assets/folio.css`：纸色与钴蓝的桌面、移动排版和转场。
- `app/components/FolioScene.client.vue`：三维组件加载、取消与生命周期。
- `app/lib/folio-scene.ts`：材质、镜头、炮组高亮、关节、资源回收与 PNG 导出。
- `app/lib/folio-effects.ts`：深度/法线轮廓、阴影点蚀与三态切换。
- `app/lib/folio-content.ts`：官方图像、裁切建议与事实来源。
- `app/lib/odin-rig.ts`：全部机械关节与动作顺序，沿用既有验证结果。

验证记录见 `docs/review/v0.26.0/`。旧版渲染和导览库保留，便于历史验证；以下为既有资产的制作记录。
## 模型处理

源文件：`../Odin 建模/odin.blend`，未覆盖。

当前待审核模型：[`assets/blender/odin_articulated_v0.11.16.blend`](assets/blender/odin_articulated_v0.11.16.blend)。舰艏和舰艉单联装炮塔各有七块装甲：从已完成的侧舷装甲复制并贴合的左右六块翻板，以及一块前盖。舰艏七个装甲关节已随原始炮管槽的刚性位移向前、向上对齐；装甲网格和炮管动作不变。打开 `/?review=secondary` 可查看两端炮塔的收起、展开和中间姿态。编辑源文件和复现命令见 [Blender 资产说明](assets/blender/README.md)。

每座主炮井保留五块独立护甲。两块长板先微量脱开齿口，再沿短导轨向外、向下平移，停留在船壳外侧；后段两块三角补片沿斜置铰链外翻约 130°；前端短盖沿原船壳的锯齿轮廓贴合，微抬后向船艏滑动。内侧使用深红色，外侧保留原灰色材质。v0.10.0 保持十片护甲的外表面和边界不变，向内加厚至原来的 2.1 倍，并让隐藏的固定接收面为厚边让位。

三根主炮管均从原始几何中分离，沿各自实测炮轴同步伸缩，中心炮管也在收拢状态缩入套筒。五块护甲完成让位后，主炮才调平、升起并伸出炮管；收拢严格反向执行。v0.10.0 恢复并动画化每座单联装原有的左右各三片盖板及独立前盖，以原位置作为展开终点，炮管以重新定位的后耳轴俯仰；四联装增加独立船壳小盖板并修整后支架，后四座双联装收得更深。舰桥护甲及其动画已取消，保留茶金色玻璃，在前塔纵向凹槽新增与下方船壳共面的矩形玻璃；天线沿前后方向布置并使用环绕红带贴图，小雷达的短桁架接在支柱后上方凸台，大雷达桁架斜向后外方。

v0.11.0 仅重做左右舷 1、3 共四座竖向侧舷炮塔：第一组为两端斜率不同的梯形平顶装甲，先抬起再向前滑动；其余三对沿实测内侧铰链翻合，格栅留在内面，外面为连续船壳涂装。收拢时，炮管、后耳轴、完整原炮座外壳、托槽和第三、第四组装甲作为同一组件先抬升再前移，让第二、第三组沿斜边对接。仅填补标出的局部三角缺口及对称位置；后方第一组按要求允许停入船体。

v0.11.1 按新的标注把固定槽底和过渡结构从活动炮座中分离；四座炮管重新居中并与槽位平行收起，旋转中心同步校准。局部三角缺口补齐，前端补面延续下层槽口的原有平面，装甲内侧加强筋统一为红色。后两座第一块装甲增加向内、向下的前端收口，闭合时落在图示下层槽口边缘。

甄别保留当前可见奥丁组件与炮塔集合实例，排除 `perseus`、隐藏旧版、原场景灯光、相机和 VFX。补充缺失的右侧对称外壳、主炮舱盖倒角、推进器内芯及喷口环、舰桥窗、导航灯和舰体编号。沿用原始材质分区和内嵌磨损贴图，将游戏节点材质转换为 glTF PBR。

这是面向外观展示的粉丝艺术补完，不是完整可游览内装，也不是官方生产级资产。

保留 186 个静态关节，含上下主炮、副炮、舰桥四联炮滑轨、10 块主炮活动护甲、6 个独立炮管伸缩段、11 座单联炮的 81 片护罩、8 片四联装船壳护甲、4 片舰艉副炮船壳盖板和固定尾舱门。贴图内嵌，动画片段数为 0。实际尺寸与网格明细见 `public/models/asset-manifest.json`。动作静帧和参考说明见 [`docs/review/`](docs/review/README.md)。

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
- `tools/revise_main_battery_v08.py`、`add_center_tubes_v08.py`：中心炮管分件、短平移导轨、后片斜轴翻转、前盖齿形和内侧深红材质，另存 v0.8.0。
- `tools/check_main_hull_sweep_v08.py`：在实际 JS 姿态中检查十块护甲与固定船壳的整个运动行程。
- `tools/review_main_sequence_v08.mjs`、`render_main_sequence_v08.py`、`make_main_sequence_v08.py`：生成同一机位的十二个动画阶段静帧和总览图。
- `tools/check_main_clearance.py`：在 101 个实际 JS 姿态上检测十块主炮护甲与炮管、炮罩、炮座三角网格的相交。
- `tools/review_rig_poses.mjs`、`render_rig_review.py`：用真实 JS 关节变换生成静态检查图，不生成动画片段。
- `tools/verify-asset.mjs`：GLB 结构、动画排除、部件与贴图验证。
- `tools/revise_mechanics_v0100.py`：从 v0.9.0 修整后耳轴、四联装与舰艉副炮，向内加厚十片主炮护甲；随后依次使用 `recover_source_covers_v0100.py`、`seat_source_covers_v0100.py` 恢复原七片盖板并校准静态关节，使用 `finish_bridge_v0100.py` 完成舰桥玻璃、天线和雷达。
- `tools/audit_geometry_v0100.py`、`check_mechanics_v0100.py`：验证盖板数量和厚度、玻璃共面、主炮外轮廓，以及 101 个实际 JS 姿态中的活动部件间隙。

- `tools/revise_side_batteries_v0110.py`、`refine_side_edges_v0110.py`：四座竖向侧舷炮塔的完整炮座联动、原盖板内侧格栅、斜边对接和梯形前盖。
- `tools/check_side_batteries_v0110.py`、`audit_side_surfaces_v0110.py`、`audit_side_scope_v0110.py`：实际 JS 姿态间隙、内外表面和改动范围检查。

模型工具需通过 Blender 5.1 的后台 Python 运行。`work/` 为本地审计和静帧检查中间文件，不属于网站部署内容。`render_completed.py` 仅生成检查静帧；这些静帧不驱动网页动画。

## 来源

- [动画灵感：Space Tech](https://www.youtube.com/watch?v=EKvbJh87rpY)
- [官方模型与开发者展示](https://www.youtube.com/watch?v=CFoQp6wRjPo)
- [RSI Anvil Odin 概念页面](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin)
- [官方 Made by the Community 标识说明](https://support.robertsspaceindustries.com/hc/en-us/articles/360006895793-Star-Citizen-Fankit-and-Fandom-FAQ)

## 版本流程

v0.23.0 提供黑色全屏场景、中英文导览、连续武备巡览和随滚动展开的机械动画。页尾采用统一的 4×4 灰度印刷网格；上一版完整备份及验收证据见 [`docs/review/v0.23.0/`](docs/review/v0.23.0/README.md)。

Vercel 发布配置在 `vercel.json`：安装依赖后执行 `npm run generate`，发布 `.output/public`。先将验证完成的 PR 合并到 `main`，再从该提交运行 `vercel --prod`；本地项目连接保存在忽略提交的 `.vercel/` 中。`.vercelignore` 只排除根目录的编辑资产与检查材料，保留 `app/assets/` 样式和全部运行时媒体。

GitHub 仓库为 `cfdxkk/odin-web`。每次修改均通过独立分支和 PR，开放审核版本打不可移动的 `vX.Y.Z-rc.N` 标签；`main` 保留已审核版本。网站私有预览可用于查看 PR 候选版本。

站点明确标注非官方 Fan Art。Star Citizen、Anvil、Odin 及概念艺术归各自权利人所有；此工程不包含独立的官方资产再授权。
