# v0.8.8 · 主装甲连续斜面与后缘接缝

本候选重建两侧主板和独立前盖的连续斜面，收紧主板与炮塔护罩的后缘接合。正式网站尚未更新，等待用户根据动画预览决定是否采用。

- [完整展开／收拢视频](main-battery-preview.mp4)：1280 × 720，14.57 秒，固定机位。
- [12 张动作序列](main-battery-sequence.png)
- [闭合近景](closed-official-direction.png) · [展开近景](open-official-direction.png)
- [可播放的预览页](index.html)

## 造型与动作

两侧主板和前盖沿同一组连续侧斜面、窄顶面构建，保持独立部件；薄壳厚度为 0.055 源单位，28 条加强筋为直线。斜面使用实际闭合炮塔护罩的内侧、外侧接点及前方船体接点约束，不再仅用较低的船体边缘决定倾角。

后缘按壳体完整厚度和相邻采样位置避让护罩。船体只在前方开口承接带局部切分长面并调整高度，后盖板扫掠范围内恢复原位置。两片主板开始移动时提前释放一小段纵向间隙，再沿外侧导轨运动；炮管与各自护罩的同步机构保持不变。

五片装甲仍分别运动；前盖独立抬起、向前移动，后方两片平面装甲仍绕船体斜轴外翻 130°。内侧深红色、现有外部配色保持。

参考：[RSI 官方主炮动画](https://media.robertsspaceindustries.com/ns6umeu6gb7w5/mp4_640.mp4)、[奥丁官网](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin)。

## 核验

- `npm test`：23 / 23 通过；更新了主板缩短抬升、提前脱开接缝的预期，其余机构仍与原有参考动作比较。
- `npm run verify:asset`：高／低精度 GLB 均通过，动画片段均为 0。
- `npm run generate`：通过。
- [主炮与相邻装甲检查](main-clearance.json)：101 个实际 JS 姿态、每姿态 30 组，0 个碰撞姿态。
- [全部主炮装甲与船体检查](hull-sweep.json)：上下两组共 10 片装甲、101 个姿态，0 个碰撞姿态。
- [范围检查](preserved-parts.json)：376 个范围外对象完全一致，包括全部炮管／护罩、后盖板、腹部装甲、副炮、PDC、舰桥装甲和尾门；原始 `odin.blend` 的 SHA256 未变。
- [加强筋形状检查](rib-shape.json)：28 条直筋平面、边线与三角面法线均通过。
- [浏览器核验](browser-review.json)：本地 Nuxt 页高画质、战斗／航行两端与用户暂停保持；无浏览器错误或警告。预览 MP4 已完整解码并在浏览器播放，437 帧。

[后缘图像检查](rear-seam-pixels.json)使用用户此前圈定区域和同一相机：红色像素从 98 降为 8，剩余为分散单像素的细小接合间隙；不将此数值表述为所有视角下完全无缝。最终外观请以视频和可放大的近景判断。

## 可编辑文件与复现

模型：`assets/blender/odin_articulated_v0.8.8.blend`。建模脚本读取仓库中的 v0.8.6 副本和闭合参考姿态，保存新版本，不修改用户原始文件。所有动作仍在 `app/lib/odin-rig.ts` 中执行。

```text
blender -b assets/blender/odin_articulated_v0.8.6.blend --python-exit-code 1 --python tools/revise_main_battery_v088.py
blender -b assets/blender/odin_articulated_v0.8.8.blend --python-exit-code 1 --python tools/export_articulated_asset.py
node tools/review_rig_poses.mjs
node tools/review_animation_poses.mjs --version 0.8.8
blender -b assets/blender/odin_articulated_v0.8.8.blend --python-exit-code 1 --python tools/render_animation_preview.py -- --version 0.8.8 --width 1280 --height 720 --view official
python tools/encode_animation_preview.py --version 0.8.8 --ffmpeg <ffmpeg executable>
python tools/make_animation_sequence.py --version 0.8.8
```

完整源文件、姿态、图片和视频哈希见 [animation-preview.json](animation-preview.json)；局部网格调整记录见 [geometry-build.json](geometry-build.json)。
