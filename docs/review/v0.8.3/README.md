# v0.8.3 炮管／护罩同步运动与深红内壁

[播放展开与收起预览](main-battery-preview.mp4) · [十二帧动作序列](main-battery-sequence.png)

本版按[官方机构视频](https://media.robertsspaceindustries.com/ns6umeu6gb7w5/mp4_640.mp4#t=0)修正主炮联动。上一版中炮的独立高度补偿提前结束，造成中途下沉再抬起；炮管与护罩分别使用不同曲线，侧炮会先下降，护罩随后才关闭。

现在每套完整炮管与对应护罩按完全展开时的相对位置连接，共用调平和抬升进度。中炮始终跟随顶部盖板；两侧炮管先与护罩共同回位，护罩停止后才完成最后一小段下沉。展开沿相反顺序执行。腹部源模型的左右护罩名称与物理位置相反，绑定已按实际几何纠正。

为避开腹部固定船壳边缘，六根炮管的同步轴向收纳行程从 16 调整为 20 源单位；完全展开端点保持原状。五块外部装甲板保留此前认可的动画。

主炮座圈鼓壁、炮罩和炮塔装甲内壁补齐深红材质，外侧灰色保持。只改变面材质和静态关节属性，未修改顶点、拓扑、UV 或原始 `odin.blend`。新版可编辑文件为 `assets/blender/odin_articulated_v0.8.3.blend`；GLB 无动画片段，动作仍由 Nuxt/Three.js 计算。

## 预览与复现

预览调用实际 GLB 与 JS rig 生成 101 个姿态，再用 Blender 临时摆放并渲染。视频约 14.6 秒，包含展开和收起；固定机位与基础材质用于看清机构，不代表网页最终光照。来源与输出校验值见 `animation-preview.json`。

```sh
node tools/review_animation_poses.mjs --version 0.8.3
blender -b assets/blender/odin_articulated_v0.8.3.blend --python-exit-code 1 --python tools/render_animation_preview.py -- --version 0.8.3 --width 960 --height 640
python tools/encode_animation_preview.py --version 0.8.3 --ffmpeg /path/to/ffmpeg
python tools/make_animation_sequence.py --version 0.8.3
```

## 验证

- 23 项测试、资产验证和 Nuxt 静态生成通过；高低两份 GLB 均有 140 个静态关节、零动画片段。
- 1001 个采样姿态验证中炮与护罩的相对刚体关系、世界轨迹无反向起伏，以及侧罩停止后的侧炮末段下沉。
- 101 个姿态对比上一版全部外部护甲及其他机构，动作保持；所有主炮完全展开的世界变换保持。
- 材质分面及全场景几何不变记录见 `interior-materials.json`。碰撞检查见 `main-clearance.json`、`hull-sweep.json`、`bore-clearance.json`，内部既有安装接触另见 `bore-audit-notes.md`。

检查是采样三角网格检测，不是连续实体装配证明。原模型罩壳内部的嵌套安装面保留并单独记录；不将它们表述为所有几何零相交。

本版为候选预览，尚未替换正式网站。
