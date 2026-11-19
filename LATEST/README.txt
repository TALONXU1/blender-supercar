LATEST — 最新工程
=================

v5_stage_anim.blend       完整交付工程：赛车模型 + 骨架 + 银石增强环境 + 2161 帧遥测动画 + 26 机位（含广播级 DOF）+ 渲染设置
v5_stage_env.blend        纯环境与材质基线（无动画）：改赛道建筑/贴图/光照时改 pipeline/v5_env.py 重跑生成
v5_stage_anim_clay.blend  白模工程：同一套动画、26 机位、DOF 与运动模糊，替换为中性雕塑灰模（Standard 视图防过曝曲线）

打开 v5_stage_anim.blend 后：

  1. Outliner 里按集合找东西（根 Scene Collection 保持 0 散落对象）：
       SCIFI_F1_2035   F1 赛车骨架 RIG_F1_Race 与全部 244 个车身/底盘/方向盘/轮组/贴花部件
       V5_01_Road      路面（含离线橡胶碎屑色差）/ 赛车线 / 重刹胎痕带 / 边线 / 红白路肩 / 香肠路肩 / pit lane
       V5_02_Terrain   地面 / 割草条纹草地 / 砾石坑 / 外围灌篱环 / 平滑大气渐变黄昏穹顶 V5_SkyDome
       V5_03_Barriers  护栏基座 / 金属护栏 / 顶沿灯带 / 防护网立柱
       V5_04_Stands    6 座看台（Empty 组件父级 + 分块观众席/顶棚/钢桁架/旗帜）
       V5_05_Pit       维修墙 / 指挥台大屏 / 维修区出口绿灯信号柱 / 6 车位循环车库楼 / 楼顶看台
       V5_06_Props     广告板 / 刹车距离牌 / DRS 提示牌 / 弯心防撞柱 / 大屏 / 人行天桥 / 裁判点 / 机库 / 起跑龙门架
       V5_07_Lighting  太阳主光 + 天空冷补光 + 3 盏随车柔光（Light Linking 绑定 V5_CarLightReceivers 全部赛车网格）
       V5_08_Cameras   26 台分镜摄影机（Cam_S01..Cam_S25）+ 全程锁定赛车的景深焦点 V5_CamFocus

  2. 每个看台/天桥/大屏/刹车牌组/裁判点/龙门架都有组件 Empty 父物体，选中 Empty 按 G / R 即可整体移动旋转；
     独立环境网格原点均位于自身几何中心。只有"路面本身"按中心线整体生成，改赛道几何请改 track_data 的 json 重跑。

  3. 时间轴 1–2161 帧（24 fps / 90.04 s / 162 拍 @ 108 BPM），机位切换由 timeline markers 自动驱动。

  4. 视口流畅度切换（仅改 hide_viewport / MESH display_type，不影响 F12 或命令行渲染）：
       blender -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- fast
       blender -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- normal
     或在 UI 里按 Z -> Solid、关掉 V5_04_Stands / V5_06_Props 眼睛、选中对象按 Numpad / 进局部视图。

.blend1 是 Blender 自动备份，可安全删除。
