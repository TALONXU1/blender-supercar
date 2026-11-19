# 赛道轨迹数据包 · 消费规范

给 agent / Blender 用。目的只有一个：让动画里的车不可能漂移。

## 文件

| 文件 | 用途 |
|---|---|
| `silverstone_track.json` | 主数据。agent 只读这个 |
| `silverstone_path.csv` | 同数据的表格版，方便肉眼核对或喂给 Excel |
| `silverstone_map.png` | 视觉核对图，黄=快 蓝=慢 |
| `build_track.py` | 生成器，换赛道改 3 个参数重跑 |
| `blender_apply.py` | Blender 消费端，读 json 直接出关键帧 |

## 这次交付的实测值

- 赛道：Silverstone（OSM relation 51160，OpenStreetMap ODbL）
- 实测周长 5.834 km，官方 5.891 km，误差 −0.97%
- 仿真单圈 90.34 s，官方杆位 87.0 s，误差 +3.84%
- 平均速度 232.5 km/h，峰值 331 km/h，最低 54 km/h
- 采样点 2933 个，间隔 2 m，闭环
- 几何质检：拼接缺口 0 m，大于 20 m 的断点 0 个
- 防漂移自检：最大横向 6.39 g，超限点 0 个 → PASS

## 坐标与单位

- 单位：米 / 秒 / 米每秒 / 度（从 +X 逆时针）
- 世界系：局部 ENU 平面，原点 = 中心线第一个点，z=0
- 反查经纬度：`lon = lon0 + x / kx`，`lat = lat0 + y / ky`（kx、ky 在 `meta.georef`）
- 你不需要经纬度。要按真实地理位置对齐才用。

## 逐点字段

| 字段 | 含义 |
|---|---|
| `t` | 该点被经过的时刻（s）。**唯一的驱动变量** |
| `s` | 沿中心线的弧长（m） |
| `xy` | 赛道中心线坐标 |
| `racing_xy` | **赛车线坐标。车走这一条** |
| `racing_offset_m` | 赛车线相对中心线的横向偏移，范围 ±5.7 m |
| `heading_deg` | 赛车线切线方向（度） |
| `curv_1pm` | 曲率 1/m。`radius_m` 是倒数 |
| `v_mps` / `v_kmh` | 该点的速度 |
| `lat_g` | 该点横向加速度（g） |

## 五条硬规则

1. **按 `t` 插值位置，不按帧均分。**
   车不是匀速的。按帧均分等于匀速跑，一眼假。
2. **朝向取 `heading_deg`，不要用位移差反推。**
   位移差在采样点稀疏处会跳变，表现为车头一顿一顿。
3. **位置沿 `racing_xy`，不是 `xy`。**
   `xy` 是中心线，走那条等于压着中线跑，弯里看着像轨道车。
4. **关键帧插值用 LINEAR，禁用 Bezier。**
   Bezier 在弯心过冲，冲出去就是漂移。这是最常见的翻车点。
5. **横向加速度上限。**
   `v² · curv_1pm` 不得超过 `15.0 + 0.00714 · v²`（含下压力模型，见 `meta.limits`）。
   任何一帧超了，就是物理上不可能的动作，观众会看出假。

## 机械细节的推导

- 轮子转速（rad/s）= `v_mps / 0.33`（18 寸胎半径 0.33 m）
- 前轮转角（rad）= `curv_1pm × 3.6`（轴距 3.6 m）
- 车不是绕自己中心转，绕后轴中心更准：后轴偏移 −1.8 m 沿车头方向

## 换赛道

```
python build_track.py "Circuit de Monaco" 3.337 71.0 --probe   # 先测数据质量
python build_track.py "Circuit de Monaco" 3.337 71.0           # 正式生成
```

`--probe` 看两件事：`length_error` 要在 ±3% 内，`big_gaps` 要为 0。
不满足说明这条赛道在 OSM 里没连好，换赛道或者手工补路。

已知情况：Silverstone 拓扑干净（缺口 0）。摩纳哥在 OSM 里是断的（缺口 400 m 以上），
不要直接用；要用就从官方赛道图手工描点存 csv。

## licence

数据 OpenStreetMap，ODbL，署名 "© OpenStreetMap contributors"。
生成的 json 属于衍生数据，同样受 ODbL 约束。自己项目内部用不管，公开发布要署名。
