# v0.10.0 — 七片护罩、后耳轴与舰桥细节

本地审核：<http://127.0.0.1:4173/?review=secondary>。使用部位菜单逐座检查，支持斜视、侧视、俯视和手动进度；本轮不部署公网。

## 本轮修改

- 十一座单联装均使用原模型已有的七片盖板：左右各三片，加一个前盖，共 77 片。保留原盖板的格栅、外形和厚度，删除先前新增的替代板；根部盖板开始和完成开合更早。展开终点采用原模型姿态，不继续向船体内下翻。
- 原前盖位置是展开位置。收起时前盖向炮槽后方移动、抬到闭合接合处；展开时先移离六片侧盖，再回落到原位置。舰艏、舰艉、舰腹使用各自炮槽基准。炮管与随动炮罩后移、上抬，重新校准后耳轴，只作俯仰；舰艏炮的远端长度另按其较短炮槽及前盖扫掠范围调整。
- 删除新增舰桥装甲和相关动画，保留茶金色玻璃。新增下层玻璃是四角矩形，放在用户指出的纵向开口中，外表面与下方原船壳共面。
- 舰桥顶部圆顶移向两端；四个板式天线沿舰船前后方向布置，红色带由一张连续 UV 贴图环绕表面，不使用额外条带网格。后部球形雷达采用 320 个三角面；两侧大胶囊雷达的桁架斜向后外方。
- 桥下两个小胶囊雷达的短桁架接在支柱后上方的原有凸台。根部实际取自该凸台表面（模型 Y=-52、Z=123.1），桁架长度约 5.66 模型单位，比上一草稿缩短约三分之二。
- 两座四联装的实际船壳小护甲独立运动，收起时微量向内、向下平移；缩短并调整炮架后支撑，修复根部与开口边的相交。后四座双联装进一步缩入炮井，船壳前盖先下降后出炮。
- 上下主炮各五片装甲保持外轮廓不变，向内加厚到上一版的 2.1 倍。隐藏接收面及上主炮最初的脱离行程同时调整，避免厚边扫过固定船壳。

## 检查证据

- `npm test`：29 项通过；`npm run verify:asset`、`npm run generate` 通过。
- 两个导出 GLB 均为 167 个合批网格、178 个静态关节、19 个材质和 12 张内嵌贴图；动画片段为 0。
- [几何核对](geometry-audit.json)：77 片原单联装盖板；10 片主炮外表面顶点变化为 0；矩形下层玻璃共面误差小于 `0.000002` 模型单位。报告同时记录左右小雷达的凸台连接坐标和天线贴图。
- [运动核对](mechanics-audit.json)：从导出 GLB 的静态层级调用实际 JS 动画，以 1% 间隔检查 101 个姿态。单联装炮管与各自活动护罩、四联装与船壳及小盖、后四座双联装与前盖、主炮护甲与固定船壳，在此检测范围内均为 0 相交事件。
- [主炮全行程复核](hull-sweep.json)：上下共 10 片护甲、101 个姿态，含源文件、GLB、JS 及姿态文件校验值。
- 原始固定炮座、轴承和船壳包含相互嵌入的模型表面。单联装与这些固定表面的接触计数另列于运动报告中，不计入“炮管与活动护罩零相交”，也不据此声称整船所有网格互不相交。

网页检查使用导出后的模型和实际网页动画；下列图片为 localhost 实际截图。

| 部位 | 截图 |
| --- | --- |
| 单联装收起，侧视 / 俯视 | [侧视](single-side.png) · [俯视](single-top.png) |
| 单联装展开与错时动作 | [展开](single-open.png) · [17% 中间姿态](single-mid.png) |
| 舰艏独立炮槽 | [收起](bow-nav.png) · [展开](bow-open.png) |
| 四联装与船壳小盖 | [收起](quad-nav.png) · [展开](quad-open.png) |
| 下层共面玻璃 | [近景](lower-glass.png) |
| 舰桥雷达和桁架 | [整体](radars.png) · [俯视](radars-top.png) |
| 后方双联装炮井 | [收起](twin-nav.png) |
| 主炮接缝 | [侧视](main-side.png) · [俯视](main-top.png) |

## 编辑来源与复现

可编辑资产为 [`odin_articulated_v0.10.0.blend`](../../../assets/blender/odin_articulated_v0.10.0.blend)，从 v0.9.0 副本修改。复现顺序是 `revise_mechanics_v0100.py`、`recover_source_covers_v0100.py`、`seat_source_covers_v0100.py`、`finish_bridge_v0100.py`，最后运行 `export_articulated_asset.py`。恢复工具只读原始模型，将已有盖板分离到静态关节上；运动仍由 `app/lib/odin-rig.ts` 计算。

原始 `../Odin 建模/odin.blend` 未覆盖，其 SHA-256 为 `9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`。

```sh
node tools/review_secondary_poses.mjs 0.10.0 --exported
blender -b assets/blender/odin_articulated_v0.10.0.blend --python-exit-code 1 --python tools/check_mechanics_v0100.py
blender -b assets/blender/odin_articulated_v0.10.0.blend --python-exit-code 1 --python tools/audit_geometry_v0100.py
```
