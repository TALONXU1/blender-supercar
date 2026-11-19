# 场景卡字段规范

给 `SCENE_OPTIONS.md` 用，也给脚本批量生成用。每个字段都有明确用途，不是装饰。

## 字段表

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✓ | `S1`–`S99`，稳定不变，脚本按这个索引 |
| `name` | string | ✓ | `银石 · 阵雨转晴`，中文，格式 `地点 · 天气` |
| `circuit` | string | ✓ | 官方赛道名 |
| `location` | string | ✓ | 城市/国家 |
| `track_length_km` | number | ✓ | 官方长度 |
| `round_2026` | integer | | 2026 赛历 round，历史赛道填 null |
| `date_window` | string | ✓ | `7/3–5` 或 `历史 1951–1976` |
| `circuit_type` | enum | ✓ | `permanent` / `street` / `semi-street` / `road-course` |
| `weather_primary` | enum | ✓ | `W1`–`W10`，见 `weather_matrix.md` |
| `weather_alt` | enum[] | | 备选预设，最多 2 个 |
| `sun_elevation_deg` | number | ✓ | 太阳高度角，决定阴影长度 |
| `sun_azimuth_note` | string | | `偏西`/`顺直道`/`从海面方向`，写人类可读的方位 |
| `color_temp_k` | integer | ✓ | 主光色温 |
| `cloud_cover_oktas` | string | | `0–1/8`，八分云量 |
| `visibility_m` | number | | 能见度，雾/雨必填 |
| `track_surface` | enum | ✓ | `dry` / `damp` / `wet` / `flooded` |
| `anchors` | string[] | ✓ | 3–5 个"三秒认出这站"的视觉元素 |
| `shots` | object[] | ✓ | 机位列表，每个 `{height_m, lens_mm, movement, subject}` |
| `dynamics` | string[] | ✓ | 画面里必须动的元素（雾流动、水雾、旗、人群） |
| `landing_cost` | enum | ✓ | `low` / `medium` / `high` / `extreme` |
| `landing_notes` | string | ✓ | 要建什么、改什么、哪一步最贵 |
| `track_data` | string \| null | ✓ | `track_data/*.json` 路径，没有就 null |
| `pitfalls` | string[] | | 已知的渲染坑 |
| `prompt_file` | string | | `prompts/0X_*.md` |

## 机位对象

```json
{
  "height_m": 1.1,
  "lens_mm": 50,
  "movement": "static | tracking | pan | crane | aerial | onboard",
  "subject": "car-passes | car-approach | car-depart | wide-track | detail"
}
```

写提示词时这三个值直接转成英文短语，别自己加形容词。

## 校验规则

1. `sun_elevation_deg` 与 `weather_primary` 不能矛盾：W9（夜赛）必须是负数或 null；W4/W8（阴/雾）太阳高度只影响亮度，不产生硬影。
2. `track_surface` 与 `weather_primary` 要对上：W5/W7 → `wet`/`flooded`；W6 → `damp`；W1/W2/W4/W10 → `dry`。
3. `landing_cost = low` 的场景，`track_data` 必须非 null——低成本的唯一来源就是已有数据。
4. `anchors` 少于 3 个的场景直接淘汰，观众认不出来。
5. `shots` 至少 3 个，且至少要有一个 `height_m < 1.5` 的低机位（这是赛车镜头的基本语法）。

## JSON 示例

```json
{
  "id": "S1",
  "name": "银石 · 阵雨转晴",
  "circuit": "Silverstone Circuit",
  "location": "英国 北安普敦郡",
  "track_length_km": 5.891,
  "round_2026": 11,
  "date_window": "7/3–5",
  "circuit_type": "permanent",
  "weather_primary": "W6",
  "weather_alt": ["W5", "W4"],
  "sun_elevation_deg": 30,
  "sun_azimuth_note": "偏西，侧后方打在看台上",
  "color_temp_k": 4800,
  "cloud_cover_oktas": "4/8",
  "visibility_m": 8000,
  "track_surface": "damp",
  "anchors": ["机场跑道直边", "Abbey–Farm–Village 连续弯", "草地缓冲带", "灰色多功能看台"],
  "shots": [
    {"height_m": 1.1, "lens_mm": 50, "movement": "tracking", "subject": "car-passes"},
    {"height_m": 2.0, "lens_mm": 200, "movement": "pan", "subject": "car-approach"},
    {"height_m": 1.4, "lens_mm": 35, "movement": "tracking", "subject": "car-depart"}
  ],
  "dynamics": ["轮后水雾", "蒸发薄雾", "半湿旗面", "雨衣观众", "路面水膜"],
  "landing_cost": "low",
  "landing_notes": "数据与环境已有，只改光照+路面材质+雨雾粒子",
  "track_data": "track_data/silverstone_track.json",
  "pitfalls": ["EEVEE SSR 在接近垂直视角失效", "干湿分界要沿 racing_xy 做 UV 遮罩"],
  "prompt_file": "prompts/01_silverstone_after_rain.md"
}
```