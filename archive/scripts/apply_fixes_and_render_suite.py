import bpy
import bmesh
import math
import os
import shutil
from mathutils import Vector, Euler

def fix_decals_and_tcams():
    print("=== EXECUTING DECAL NORMAL FIX, BACKFACE CULLING & T-CAM ENHANCEMENT ===")

    # 1. 打开主工程
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # ---------------------------------------------------------
    # 1. 修复所有贴花网格法线 (Flip Normals Outward)
    # ---------------------------------------------------------
    decal_normal_targets = {
        'DEC_Sidepod_Oracle_L': (-1.0, 0.0, 0.0), # 朝左外侧
        'DEC_Sidepod_Oracle_R': (1.0, 0.0, 0.0),  # 朝右外侧
        'DEC_Engine_RedBull_L': (-1.0, 0.0, 0.0), # 朝左外侧
        'DEC_Engine_RedBull_R': (1.0, 0.0, 0.0),  # 朝右外侧
        'DEC_Endplate_Front_L': (-1.0, 0.0, 0.0), # 朝左外侧
        'DEC_Endplate_Front_R': (1.0, 0.0, 0.0),  # 朝右外侧
        'DEC_Endplate_Rear_L': (-1.0, 0.0, 0.0),  # 朝左外侧
        'DEC_Endplate_Rear_R': (1.0, 0.0, 0.0),   # 朝右外侧
        'DEC_RearWing_Front_Oracle': (0.0, 1.0, 0.0), # 朝前
        'DEC_RearWing_Back_RedBull': (0.0, -1.0, 0.0), # 朝后
    }

    for obj_name, target_dir in decal_normal_targets.items():
        obj = bpy.data.objects.get(obj_name)
        if obj and obj.type == 'MESH':
            # 检查当前平均法线
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            if len(bm.faces) > 0:
                face = bm.faces[0]
                norm = face.normal
                # 点乘判断是否反向
                dot = norm.x * target_dir[0] + norm.y * target_dir[1] + norm.z * target_dir[2]
                if dot < 0:
                    print(f"Flipping normal for {obj_name} (dot={dot:.2f})")
                    bmesh.ops.reverse_faces(bm, faces=bm.faces)
                    bm.to_mesh(mesh)
                    mesh.update()
            bm.free()

    # ---------------------------------------------------------
    # 2. 为所有贴花着色器注入 Backface Culling (背面100%隐形消隐)
    # ---------------------------------------------------------
    decal_mats = [
        'Mat_DEC_Sidepod_Oracle',
        'Mat_DEC_Engine_RedBull',
        'Mat_DEC_Halo_Oracle',
        'Mat_DEC_RearWing_Front',
        'Mat_DEC_RearWing_Back',
        'Mat_DEC_RearWing_Bybit',
        'Mat_DEC_Endplate_Mobil1',
        'Mat_DEC_Nose_Livery',
        'Mat_PZero_Pirelli_Sidewall'
    ]

    for mat_name in decal_mats:
        mat = bpy.data.materials.get(mat_name)
        if not mat or not mat.node_tree:
            continue
        
        tree = mat.node_tree
        nodes = tree.nodes
        links = tree.links

        # 开启视口背面消隐
        if hasattr(mat, 'use_backface_culling'):
            mat.use_backface_culling = True

        out_node = None
        for n in nodes:
            if n.type == 'OUTPUT_MATERIAL':
                out_node = n
                break
        
        if not out_node:
            continue

        # 找到当前连到 Surface 的节点
        surface_source = None
        for l in links:
            if l.to_node == out_node and l.to_socket.name == 'Surface':
                surface_source = l.from_socket
                break

        if not surface_source:
            continue

        # 如果已经是 Mix Shader 且包含 Backfacing 则跳过
        if surface_source.node.type == 'MIX_SHADER' and nodes.get("BF_Geometry"):
            continue

        # 创建 Geometry, Transparent BSDF, Mix Shader
        geo_node = nodes.get("BF_Geometry") or nodes.new('ShaderNodeNewGeometry')
        geo_node.name = "BF_Geometry"
        geo_node.location = (out_node.location.x - 300, out_node.location.y + 150)

        trans_node = nodes.get("BF_Transparent") or nodes.new('ShaderNodeBsdfTransparent')
        trans_node.name = "BF_Transparent"
        trans_node.location = (out_node.location.x - 300, out_node.location.y - 150)

        mix_node = nodes.get("BF_MixShader") or nodes.new('ShaderNodeMixShader')
        mix_node.name = "BF_MixShader"
        mix_node.location = (out_node.location.x - 120, out_node.location.y)

        # 连线: Backfacing -> Fac; Front BSDF -> Shader 1; Transparent BSDF -> Shader 2
        # 注意: 当 Backfacing 为 1 时(背面)，使用第二输入(Transparent)
        links.new(geo_node.outputs['Backfacing'], mix_node.inputs['Factor'])
        links.new(surface_source, mix_node.inputs[1])
        links.new(trans_node.outputs['BSDF'], mix_node.inputs[2])
        links.new(mix_node.outputs['Shader'], out_node.inputs['Surface'])
        print(f"Applied Backface Culling Shader to {mat_name}")

    # ---------------------------------------------------------
    # 3. 规范化 FIA T-Cam 摄影机支架与双向高解析度机芯
    # ---------------------------------------------------------
    col_cowl = bpy.data.collections.get("03_Sidepods_EngineCowl") or bpy.data.collections.get("SCIFI_F1_2035")
    mat_carbon = bpy.data.materials.get("Mat_Carbon_Fiber") or bpy.data.materials.get("Mat_Forged_Carbon")
    mat_yellow = bpy.data.materials.get("Mat_RedBull_SolarYellow")
    mat_titanium = bpy.data.materials.get("Mat_Titanium_Hardware")

    # 检查现存 TCam
    tcam_obj = bpy.data.objects.get("GEO_F1_Overhead_TCam")
    if tcam_obj:
        # 重构 TCam 为流线型真实 FIA 双目外壳
        # 基座气动立柱 Pylon (从 z=1.05 到 z=1.14)
        mesh_pylon = bpy.data.meshes.new("GEO_F1_TCam_Pylon_Mesh")
        bm_p = bmesh.new()
        bmesh.ops.create_cube(bm_p, size=1.0)
        # 缩放成立柱厚度 x=0.016, y=0.10, z=0.09
        bmesh.ops.scale(bm_p, vec=(0.016, 0.10, 0.09), verts=bm_p.verts)
        bmesh.ops.translate(bm_p, vec=(0.0, -0.28, 1.09), verts=bm_p.verts)
        bm_p.to_mesh(mesh_pylon)
        bm_p.free()

        obj_pylon = bpy.data.objects.get("GEO_F1_TCam_Pylon")
        if not obj_pylon:
            obj_pylon = bpy.data.objects.new("GEO_F1_TCam_Pylon", mesh_pylon)
            col_cowl.objects.link(obj_pylon)
        else:
            obj_pylon.data = mesh_pylon
        if mat_carbon:
            obj_pylon.data.materials.clear()
            obj_pylon.data.materials.append(mat_carbon)

        # 顶部 T 型双目摄像机舱 (Forward 4K + Aft 4K)
        mesh_pod = bpy.data.meshes.new("GEO_F1_Overhead_TCam_Mesh")
        bm_pod = bmesh.new()
        bmesh.ops.create_cube(bm_pod, size=1.0)
        # x=0.05, y=0.14, z=0.035
        bmesh.ops.scale(bm_pod, vec=(0.052, 0.14, 0.036), verts=bm_pod.verts)
        bmesh.ops.translate(bm_pod, vec=(0.0, -0.28, 1.145), verts=bm_pod.verts)
        bm_pod.to_mesh(mesh_pod)
        bm_pod.free()
        tcam_obj.data = mesh_pod
        if mat_yellow: # 经典 FIA 一号车高饱和荧光黄 T-Cam
            tcam_obj.data.materials.clear()
            tcam_obj.data.materials.append(mat_yellow)

        # 前后光学镜头
        for i, (y_off, rot_y) in enumerate([(0.075, 0.0), (-0.075, math.pi)]):
            lens_name = f"GEO_F1_TCam_Lens_{'Fwd' if i==0 else 'Aft'}"
            mesh_l = bpy.data.meshes.new(f"{lens_name}_Mesh")
            bm_l = bmesh.new()
            bmesh.ops.create_cone(bm_l, cap_ends=True, cap_tris=False, segments=16, radius1=0.009, radius2=0.009, depth=0.012)
            bmesh.ops.rotate(bm_l, cent=(0,0,0), matrix=Euler((math.pi/2, 0, 0)).to_matrix(), verts=bm_l.verts)
            bmesh.ops.translate(bm_l, vec=(0.0, -0.28 + y_off, 1.145), verts=bm_l.verts)
            bm_l.to_mesh(mesh_l)
            bm_l.free()
            obj_l = bpy.data.objects.get(lens_name)
            if not obj_l:
                obj_l = bpy.data.objects.new(lens_name, mesh_l)
                col_cowl.objects.link(obj_l)
            else:
                obj_l.data = mesh_l
            if mat_titanium:
                obj_l.data.materials.clear()
                obj_l.data.materials.append(mat_titanium)

    # ---------------------------------------------------------
    # 4. 微调宏观机位与构图，确保全车完整容纳与气势拉满
    # ---------------------------------------------------------
    # Hero 3/4 机位调整：使整车 5.5m 完美居中且带极具张力的透视
    hero_cam = bpy.data.objects.get("Cam_F1_Hero_Trackside34")
    if hero_cam:
        hero_cam.location = Vector((3.40, 4.20, 0.52))
        hero_cam.data.lens = 58.0 # 58mm 极佳的人文黄金透视，无畸变且层次分明
        hero_cam.data.dof.use_dof = True
        hero_cam.data.dof.focus_distance = 5.2
        hero_cam.data.dof.aperture_fstop = 5.6 # 深景深保证全车锐利

    # 车轮微距微调
    wheel_cam = bpy.data.objects.get("Cam_F1_Aero_Wheel_Macro")
    if wheel_cam:
        wheel_cam.location = Vector((1.75, 1.65, 0.38))
        wheel_cam.data.lens = 85.0
        wheel_cam.data.dof.use_dof = True
        wheel_cam.data.dof.focus_distance = 1.6
        wheel_cam.data.dof.aperture_fstop = 4.0

    # 侧视图保证完整 5.5 米车身
    side_cam = bpy.data.objects.get("Cam_F1_Side_Profile_Tele")
    if side_cam:
        side_cam.location = Vector((9.20, -0.10, 0.45))
        side_cam.data.lens = 95.0
        side_cam.data.dof.use_dof = False

    # 尾部扩散器特写
    rear_cam = bpy.data.objects.get("Cam_F1_Rear_Diffuser_Low")
    if rear_cam:
        rear_cam.location = Vector((-2.60, -4.50, 0.42))
        rear_cam.data.lens = 60.0
        rear_cam.data.dof.use_dof = True
        rear_cam.data.dof.focus_distance = 4.8
        rear_cam.data.dof.aperture_fstop = 5.6

    # 俯视气动全景
    top_cam = bpy.data.objects.get("Cam_F1_Top_Aero_Down")
    if top_cam:
        top_cam.location = Vector((0.0, -0.15, 9.80))
        top_cam.data.lens = 52.0

    # 驾驶舱第一人称视角
    cockpit_cam = bpy.data.objects.get("Cam_F1_Onboard_DriverPOV")
    if cockpit_cam:
        cockpit_cam.location = Vector((0.0, -0.04, 0.81))
        cockpit_cam.rotation_euler = Euler((math.radians(82.0), 0.0, math.radians(180.0)))
        cockpit_cam.data.lens = 38.0
        cockpit_cam.data.dof.use_dof = True
        cockpit_cam.data.dof.focus_distance = 0.65
        cockpit_cam.data.dof.aperture_fstop = 3.5

    # 保存主工程
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("=== SCENE OPTIMIZED & SAVED SUCCESSFULLY ===")

if __name__ == '__main__':
    fix_decals_and_tcams()
