# v0.8.5 后侧装甲分界与闭合舱唇

按用户标注修改后侧小盖板与两侧大装甲的共享分界，保留前端小装甲为独立部件，并沿用它的抬起、前移动作。前端小装甲不会并入两侧大板。

同时修正闭合图中的长红线：v0.8.4 的内壁选择包含了向上暴露的外侧舱唇，这些外表面应恢复原灰色；真正的倾斜内壁仍为深红色。几何贴合与材质分区分别检查。

新版模型另存为 `assets/blender/odin_articulated_v0.8.5.blend`。原始 `odin.blend` 不变，所有动画仍由 Nuxt/Three.js 计算，静态 GLB 不含动画片段。

[动画预览](main-battery-preview.mp4) · [闭合高清近景](closed-seam-detail.png) · [分块示意](armor-parts.png) · [闭合／半开／全开对照](seam-comparison.png) · [十二帧序列](main-battery-sequence.png)

## 机构与验证

- 新后缘下端向前移 4 个源模型单位，后侧小板仍为单一平面，最大平面误差小于 0.000002。只在接合内侧做倒角，闭合外表边线保持贴合。
- 为使延长后的前角翻开时避让大板，四个后侧铰轴做小幅平行重定位，轴方向、130°外翻角度和动画时序保持。详情与闭合形状残差见 `armor-boundaries.json`。
- 前端独立小板、全部主炮和其他机构保留；339 个非本轮装甲对象的几何、UV、变换、层级和关节属性通过独立对比，见 `preserved-parts.json`。固定船壳顶点与拓扑保持，见 `hull-preservation.json`。
- 实际导出层级与 JS 动画生成 101 个姿态，装甲对炮塔、装甲彼此、装甲对固定船壳的采样检查均未检测到相交，见 `main-clearance.json` 和 `hull-sweep.json`。这是采样三角网格检查，不是连续实体装配证明。
- `npm test`（23 项）、`npm run verify:asset`、`npm run generate` 通过；GLB 零动画片段，动画预览完整解码通过。
- 浏览器高画质下检查 SCM 展开、NAV 闭合和外唇颜色；手动暂停保持，无浏览器警告或错误，见 `browser-review.json`。

本版为候选预览，尚未替换正式网站。
