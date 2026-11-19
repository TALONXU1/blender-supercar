# -*- coding: utf-8 -*-
"""
pipeline/v6_build_circuit.py
Neo-Monaco x Nueva York 2099 Sky-Harbor Circuit — 3D Geometry & Vehicle Physics Generator

Outputs:
  - track_data/spiderverse_circuit.json
  - track_data/spiderverse_circuit_map.png

Strictly isolated from V5 files and other pipeline/v6_* scripts.
"""

import json
import math
import os
import time
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq, minimize, root

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image


PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJ_DIR, "track_data")
JSON_PATH = os.path.join(OUT_DIR, "spiderverse_circuit.json")
MAP_PATH = os.path.join(OUT_DIR, "spiderverse_circuit_map.png")


# ---------------------------------------------------------------------------
# 1. Smooth C^2 / Quintic Primitives on Periodic Loop u in [0, 1)
# ---------------------------------------------------------------------------
def smooth_step_quintic(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * x * (10.0 - 15.0 * x + 6.0 * x * x)


def smooth_bump(u, u0, u1, edge_frac=0.35):
    """Periodic C^2 flat-top clothoid bump over [u0, u1] on u in [0, 1)."""
    w = (u1 - u0) % 1.0
    du = (u - u0) % 1.0
    out = np.zeros_like(u, dtype=float)
    e = max(1e-6, min(0.499, edge_frac)) * w

    m_rise = (du > 0.0) & (du < e)
    out[m_rise] = smooth_step_quintic(du[m_rise] / e)

    m_flat = (du >= e) & (du <= w - e)
    out[m_flat] = 1.0

    m_fall = (du > w - e) & (du < w)
    out[m_fall] = smooth_step_quintic((w - du[m_fall]) / e)
    return out


def corner_turn(u, u0, u1, angle_deg, edge_frac=0.35):
    """Smooth clothoid corner over [u0, u1] integrating to exact radians(angle_deg)."""
    b = smooth_bump(u, u0, u1, edge_frac=edge_frac)
    integ = float(np.sum(b)) / len(u)
    return b * (math.radians(angle_deg) / max(integ, 1e-12))


def zone_name_at(s_frac):
    if s_frac < 0.16:
        return "canyon_grid"
    if s_frac < 0.33:
        return "eau_rouge_climb"
    if s_frac < 0.50:
        return "sky_bridge"
    if s_frac < 0.70:
        return "banked_bowl_plunge"
    return "strobe_tunnel_harbor"


# ---------------------------------------------------------------------------
# 2. Closed-Loop 3D Centerline Synthesis (Exact C^2 Periodic Closure)
# ---------------------------------------------------------------------------
def build_centerline_3d(target_n=1860, step_m=2.0):
    """
    Synthesizes a closed, non-self-intersecting 3D loop of exact length target_n * step_m
    (1860 * 2.0 = 3720.0 m) with >= 78 m XY separation across all non-adjacent segments.
    """
    m_dense = 12000
    u = np.linspace(0.0, 1.0, m_dense, endpoint=False)
    du = 1.0 / m_dense

    def xy_closure_system(params):
        a_raid, a_bk, a_hp = params
        corners = [
            # Zone 1: canyon_grid (0.00 .. 0.16) — Urban Canyon Straight -> Tight Chicane
            (0.096, 0.123, -84.0, 0.34),
            (0.123, 0.150, +80.0, 0.34),
            # Zone 2: eau_rouge_climb (0.16 .. 0.33) — High-speed sweeping S-bend climbing +42m
            (0.162, 0.196, +32.0, 0.42),
            (0.196, 0.298, a_raid, 0.40),
            (0.298, 0.328, +18.0, 0.44),
            # Zone 3: sky_bridge (0.33 .. 0.50) — Suspension Bridge Straight & Fast Aero S-Kink
            (0.382, 0.415, -46.0, 0.36),
            (0.416, 0.455, a_bk, 0.38),
            # Zone 4: banked_bowl_plunge (0.50 .. 0.70) — 188-deg Banked Bowl + Corkscrew Plunge
            (0.502, 0.578, -188.0, 0.26),
            (0.598, 0.629, +92.0, 0.34),
            (0.631, 0.672, -54.0, 0.36),
            # Zone 5: strobe_tunnel_harbor (0.70 .. 1.00) — Cyber Tunnel -> Harbor Hairpin -> Finish
            (0.715, 0.845, +12.0, 0.46),
            (0.854, 0.878, +18.0, 0.42),
            (0.898, 0.9158, a_hp, 0.26),
            (0.946, 0.985, -36.0, 0.45),
        ]
        kap = np.zeros_like(u)
        for u0, u1, ang, ef in corners:
            kap += corner_turn(u, u0, u1, ang, ef)

        theta = np.cumsum(kap) * du
        theta -= theta[0]
        res = np.array([
            float(np.sum(kap) * du) + 2.0 * math.pi,
            float(np.sum(np.cos(theta)) * du),
            float(np.sum(np.sin(theta)) * du),
        ])
        return kap, theta, res

    sol = root(lambda p: xy_closure_system(p)[2], x0=[-184.0, 18.5, -120.5], method="hybr", tol=1e-12)
    if not sol.success and np.max(np.abs(sol.fun)) > 1e-9:
        raise RuntimeError(f"XY loop closure failed: {sol.message}")

    _, theta_u, _ = xy_closure_system(sol.x)
    x_u = np.cumsum(np.cos(theta_u)) * du
    y_u = np.cumsum(np.sin(theta_u)) * du
    x_u -= x_u[0]
    y_u -= y_u[0]

    # Elevation Z(u) profile:
    # - canyon_grid (0.00..0.16): Z = 0.8 m -> 3.0 m
    # - eau_rouge_climb (0.16..0.33): Z = 3.0 m -> +42.0 m (pitch peaking ~ +13.4 deg)
    # - sky_bridge (0.33..0.50): Z = +42.0 .. +42.35 m
    # - banked_bowl_plunge (0.50..0.70): Z = +42.0 m -> +1.5 m (Corkscrew pitch ~ -14.2 deg)
    # - strobe_tunnel_harbor (0.70..1.00): Z = 1.5 m (tunnel) -> 0.8 m (finish straight)
    z_raw = np.full_like(u, 0.8)
    z_raw += 2.2 * smooth_step_quintic((u - 0.050) / (0.160 - 0.050))
    z_raw += 4.6 * smooth_step_quintic((u - 0.160) / (0.326 - 0.160))
    z_raw += 34.4 * smooth_step_quintic((u - 0.196) / (0.2735 - 0.196))
    z_raw += 0.35 * np.sin(np.pi * np.clip((u - 0.330) / 0.170, 0.0, 1.0)) ** 2
    z_raw -= 4.3 * smooth_step_quintic((u - 0.525) / (0.696 - 0.525))
    z_raw -= 36.2 * smooth_step_quintic((u - 0.600) / (0.6785 - 0.600))
    z_raw -= 0.7 * smooth_step_quintic((u - 0.860) / (0.975 - 0.860))

    target_l3d = float(target_n) * step_m

    def calc_l3d(l2d):
        xd = np.append(x_u * l2d, x_u[0] * l2d)
        yd = np.append(y_u * l2d, y_u[0] * l2d)
        zd = np.append(z_raw, z_raw[0])
        return float(np.sum(np.sqrt(np.diff(xd) ** 2 + np.diff(yd) ** 2 + np.diff(zd) ** 2)))

    l2d_opt = brentq(lambda l2d: calc_l3d(l2d) - target_l3d, 3300.0, 3900.0, xtol=1e-11)

    # Iterative exact 3D chord-length reparameterization so every 2.0m step is uniform to <1e-5m
    xd = np.append(x_u * l2d_opt, x_u[0] * l2d_opt)
    yd = np.append(y_u * l2d_opt, y_u[0] * l2d_opt)
    zd = np.append(z_raw, z_raw[0])
    ds_d = np.sqrt(np.diff(xd) ** 2 + np.diff(yd) ** 2 + np.diff(zd) ** 2)
    s_d = np.concatenate([[0.0], np.cumsum(ds_d)])
    s_d[-1] = target_l3d

    cs_x = CubicSpline(s_d, xd, bc_type="periodic")
    cs_y = CubicSpline(s_d, yd, bc_type="periodic")
    cs_z = CubicSpline(s_d, zd, bc_type="periodic")

    # Fine arc-length table on the spline itself for exact 2.000m 3D chord spacing
    s_fine_q = np.linspace(0.0, target_l3d, 36801)
    xf, yf, zf = cs_x(s_fine_q), cs_y(s_fine_q), cs_z(s_fine_q)
    ds_f = np.sqrt(np.diff(xf) ** 2 + np.diff(yf) ** 2 + np.diff(zf) ** 2)
    cum_f = np.concatenate([[0.0], np.cumsum(ds_f)])
    scale_exact = target_l3d / cum_f[-1]
    xf *= scale_exact
    yf *= scale_exact
    cum_f *= scale_exact
    cum_f[-1] = target_l3d

    cs_x = CubicSpline(cum_f, xf, bc_type="periodic")
    cs_y = CubicSpline(cum_f, yf, bc_type="periodic")
    cs_z = CubicSpline(cum_f, zf, bc_type="periodic")

    s_grid = np.arange(target_n, dtype=float) * step_m
    return s_grid, target_l3d, cs_x, cs_y, cs_z, sol.x


# ---------------------------------------------------------------------------
# 3. Banking, Optimal Racing Line & 3D Ribbon Frame
# ---------------------------------------------------------------------------
def build_banking_and_racing_line(s_grid, l3d, cs_x, cs_y, cs_z):
    n = len(s_grid)
    sf = s_grid / l3d
    X = cs_x(s_grid)
    Y = cs_y(s_grid)
    Z = cs_z(s_grid)

    dx = cs_x(s_grid, 1)
    dy = cs_y(s_grid, 1)
    dz = cs_z(s_grid, 1)
    dxy = np.hypot(dx, dy)
    pitch_cl = np.degrees(np.arctan2(dz, dxy))
    ddx = cs_x(s_grid, 2)
    ddy = cs_y(s_grid, 2)
    kap_cl = (dx * ddy - dy * ddx) / np.maximum(dxy ** 3, 1e-12)

    # Inward banking convention (right-hand roll around +Forward tangent T):
    #   bank_deg > 0 tilts normal toward +Right (inward on Right turns where curv_1pm < 0)
    #   bank_deg < 0 tilts normal toward +Left  (inward on Left turns where curv_1pm > 0)
    # 188-deg Right-Hand Carousel Bowl peaks at +17.4 deg (inside 16..18 deg target!)
    bank_deg = (
        +17.4 * smooth_bump(sf, 0.498, 0.582, edge_frac=0.30)
        - 4.0 * smooth_bump(sf, 0.162, 0.198, edge_frac=0.42)
        + 6.2 * smooth_bump(sf, 0.196, 0.298, edge_frac=0.40)
        - 5.5 * smooth_bump(sf, 0.598, 0.630, edge_frac=0.38)
        + 4.5 * smooth_bump(sf, 0.630, 0.672, edge_frac=0.40)
    )

    # Minimum-Curvature Optimal Racing Line via L-BFGS-B within ±5.10 m (inside ±5.2 m spec)
    ds0 = float(s_grid[1] - s_grid[0])
    w_d1 = 1.2e-5
    w_d3 = 8.0e-2
    w_c = 1.5e-8

    def race_obj_and_grad(off):
        om1 = np.roll(off, 1)
        op1 = np.roll(off, -1)
        om2 = np.roll(off, 2)
        op2 = np.roll(off, -2)
        d2 = (op1 - 2.0 * off + om1) / (ds0 * ds0)
        d1 = (op1 - om1) / (2.0 * ds0)
        d3 = (op2 - 2.0 * op1 + 2.0 * om1 - om2) / (2.0 * ds0 ** 3)
        keff = kap_cl * (1.0 + kap_cl * off) + d2
        loss = 0.5 * np.sum(keff ** 2 + w_d1 * d1 ** 2 + w_d3 * d3 ** 2 + w_c * off ** 2)

        g_keff = keff
        grad = g_keff * (kap_cl * kap_cl) + (np.roll(g_keff, 1) - 2.0 * g_keff + np.roll(g_keff, -1)) / (ds0 * ds0)
        g_d1 = w_d1 * d1
        grad += (np.roll(g_d1, 1) - np.roll(g_d1, -1)) / (2.0 * ds0)
        g_d3 = w_d3 * d3
        grad += (np.roll(g_d3, 2) - 2.0 * np.roll(g_d3, 1) + 2.0 * np.roll(g_d3, -1) - np.roll(g_d3, -2)) / (2.0 * ds0 ** 3)
        grad += w_c * off
        return float(loss), grad

    res_opt = minimize(
        race_obj_and_grad,
        np.zeros(n),
        jac=True,
        method="L-BFGS-B",
        bounds=[(-5.10, 5.10)] * n,
        options={"maxiter": 650, "ftol": 1e-12, "gtol": 1e-9},
    )
    off = res_opt.x
    kh = 12
    kx = np.arange(-kh, kh + 1, dtype=float)
    kw = np.exp(-0.5 * (kx / 2.5) ** 2)
    kw /= kw.sum()
    off = np.convolve(np.concatenate([off[-kh:], off, off[:kh]]), kw, mode="valid")
    off = np.clip(off, -5.2, 5.2)

    # Fixed-point 3D Banked Ribbon Frame:
    # Ensures P_race = C - off * R(heading_deg, pitch_deg, bank_deg) lies 100% on the banked road mesh
    # AND (heading_deg, pitch_deg) equals the exact C^2 3D tangent of P_race.
    h_rad = np.arctan2(dy, dx)
    pt_rad = np.radians(pitch_cl)
    bk_rad = np.radians(bank_deg)
    s_ext = np.append(s_grid, l3d)

    for _ in range(7):
        r0_x, r0_y, r0_z = np.sin(h_rad), -np.cos(h_rad), np.zeros_like(h_rad)
        u0_x = -np.sin(pt_rad) * np.cos(h_rad)
        u0_y = -np.sin(pt_rad) * np.sin(h_rad)
        u0_z = np.cos(pt_rad)
        rx_vec = np.cos(bk_rad) * r0_x - np.sin(bk_rad) * u0_x
        ry_vec = np.cos(bk_rad) * r0_y - np.sin(bk_rad) * u0_y
        rz_vec = np.cos(bk_rad) * r0_z - np.sin(bk_rad) * u0_z

        RX = X - off * rx_vec
        RY = Y - off * ry_vec
        RZ = Z - off * rz_vec

        cs_rx = CubicSpline(s_ext, np.append(RX, RX[0]), bc_type="periodic")
        cs_ry = CubicSpline(s_ext, np.append(RY, RY[0]), bc_type="periodic")
        cs_rz = CubicSpline(s_ext, np.append(RZ, RZ[0]), bc_type="periodic")
        drx = cs_rx(s_grid, 1)
        dry = cs_ry(s_grid, 1)
        drz = cs_rz(s_grid, 1)
        drxy = np.hypot(drx, dry)
        h_rad = np.arctan2(dry, drx)
        pt_rad = np.arctan2(drz, drxy)

    ddrx = cs_rx(s_grid, 2)
    ddry = cs_ry(s_grid, 2)
    curv_race = (drx * ddry - dry * ddrx) / np.maximum(drxy ** 3, 1e-12)

    return (
        X, Y, Z,
        RX, RY, RZ,
        off,
        np.degrees(h_rad),
        np.degrees(pt_rad),
        bank_deg,
        curv_race,
        kap_cl,
    )


# ---------------------------------------------------------------------------
# 4. Forward-Backward 3D Velocity Profile Solver (Calibrated to 96 Beats @ 108 BPM)
# ---------------------------------------------------------------------------
def solve_calibrated_velocity(sf, RX, RY, RZ, pitch_deg, bank_deg, curv_race, target_lap_s):
    n = len(sf)
    rx_ext = np.append(RX, RX[0])
    ry_ext = np.append(RY, RY[0])
    rz_ext = np.append(RZ, RZ[0])
    ds_race = np.sqrt(np.diff(rx_ext) ** 2 + np.diff(ry_ext) ** 2 + np.diff(rz_ext) ** 2)

    pt_rad = np.radians(pitch_deg)
    bk_rad = np.radians(bank_deg)
    sin_pt = np.sin(pt_rad)
    tan_bk = np.tan(np.abs(bk_rad))
    k_abs = np.abs(curv_race)

    # Enclosed low-drag Cyber-Strobe Tunnel ERS + DRS top-speed boost (peaks ~342.4 km/h = 95.1 m/s)
    tun_boost = smooth_bump(sf, 0.705, 0.875, edge_frac=0.18)

    def eval_profile(scalar):
        # Open-air DRS top speed ~91.2 m/s (328 km/h); enclosed tunnel peaks ~95.1 m/s (342.4 km/h)
        vmax_arr = 91.0 * math.sqrt(scalar) + 6.3 * tun_boost
        vmax_arr = np.minimum(vmax_arr, 95.4)

        # Grip limit: a_lat_max = scalar * (16.5 + 0.0075 * v^2 + 9.81 * tan(|bank_rad|))
        # Capped at min(scalar, 1.0) on cornering so ZERO points ever exceed unscaled grip limits!
        g_sc = min(scalar, 1.0)
        a0_lat = 16.5 * g_sc
        c_lat = 0.0075 * g_sc
        bank_term = 9.81 * tan_bk * g_sc

        V = np.empty(n, dtype=float)
        for i in range(n):
            denom = k_abs[i] - c_lat
            if denom <= 1e-6:
                V[i] = vmax_arr[i]
            else:
                V[i] = min(vmax_arr[i], math.sqrt((a0_lat + bank_term[i]) / denom))

        for _ in range(8):
            # Backward F1 carbon braking pass: min(56.0, 21.0 + 0.0052 * v^2)
            for i in range(n - 1, -1, -1):
                vn = V[(i + 1) % n]
                ds = ds_race[i]
                vi = vn
                for _ in range(3):
                    vm = 0.5 * (vi + vn)
                    abrk = scalar * min(56.0, 21.0 + 0.0052 * vm * vm) + 9.81 * sin_pt[i]
                    abrk = max(5.0, abrk)
                    vi = math.sqrt(vn * vn + 2.0 * abrk * ds)
                if vi < V[i]:
                    V[i] = vi

            # Forward hybrid + DRS traction pass
            for i in range(n):
                vp = V[i]
                ds = ds_race[i]
                p_pow = (1020.0 + 310.0 * tun_boost[i]) * scalar
                a_tr = scalar * 16.6
                aacc = min(a_tr, p_pow / max(vp, 12.0)) - 9.81 * sin_pt[i]
                aacc = max(0.5, aacc)
                vn_max = min(vmax_arr[(i + 1) % n], math.sqrt(vp * vp + 2.0 * aacc * ds))
                if vn_max < V[(i + 1) % n]:
                    V[(i + 1) % n] = vn_max

        dt = ds_race / np.maximum(0.5 * (V + np.roll(V, -1)), 1.0)
        return float(np.sum(dt)), V, dt, ds_race

    scalar_opt = brentq(lambda s: eval_profile(s)[0] - target_lap_s, 0.80, 1.15, xtol=1e-10)
    lap_s, V_opt, dt_opt, ds_race = eval_profile(scalar_opt)
    t_arr = np.concatenate([[0.0], np.cumsum(dt_opt[:-1])])
    return scalar_opt, lap_s, V_opt, t_arr, dt_opt, ds_race


# ---------------------------------------------------------------------------
# 5. Diagnostic Chart Renderer (2D Layout + Elevation / Speed / Banking Subplots)
# ---------------------------------------------------------------------------
def render_diagnostic_chart(
    map_path, s_grid, l3d, X, Y, Z, RX, RY, off, heading_deg, pitch_deg, bank_deg, curv_race, V_mps, t_arr, meta
):
    plt.rcParams.update({
        "figure.facecolor": "#090B14",
        "axes.facecolor": "#0E1222",
        "axes.edgecolor": "#2B3558",
        "axes.labelcolor": "#D7E2FF",
        "xtick.color": "#9FB0D9",
        "ytick.color": "#9FB0D9",
        "text.color": "#ECF2FF",
        "grid.color": "#1D2642",
        "font.size": 10,
    })

    fig = plt.figure(figsize=(22, 14), dpi=100)
    gs = fig.add_gridspec(3, 2, width_ratios=[1.22, 1.0], hspace=0.30, wspace=0.18,
                          left=0.045, right=0.975, top=0.92, bottom=0.055)

    ax_map = fig.add_subplot(gs[:, 0])
    ax_z = fig.add_subplot(gs[0, 1])
    ax_v = fig.add_subplot(gs[1, 1])
    ax_b = fig.add_subplot(gs[2, 1])

    fig.suptitle(
        f"{meta['name']}  |  {meta['measured_length_km']:.3f} km  |  "
        f"Lap {meta['sim_lap_s']:.3f} s ({meta['beats']} Beats @ {meta['bpm']} BPM = {meta['frame_end']}f)  |  "
        f"Z [+{ float(Z.min()):.1f}..+{meta['max_z_m']:.1f} m]  |  Max Bank +{meta['max_bank_deg']:.1f}°",
        fontsize=15, fontweight="bold", color="#00F0FF", y=0.968,
    )

    # --- Left Panel: 2D XY Layout ---
    h_rad = np.radians(heading_deg)
    r_x, r_y = np.sin(h_rad), -np.cos(h_rad)
    Xc = np.append(X, X[0])
    Yc = np.append(Y, Y[0])

    # Barriers (±8.2m) & Road edges (±7.0m)
    for w_edge, col, lw, al in [
        (8.2, "#FF2A6D", 1.0, 0.45),
        (-8.2, "#FF2A6D", 1.0, 0.45),
        (7.0, "#3E4E7A", 1.2, 0.75),
        (-7.0, "#3E4E7A", 1.2, 0.75),
    ]:
        ex = np.append(X + w_edge * r_x, X[0] + w_edge * r_x[0])
        ey = np.append(Y + w_edge * r_y, Y[0] + w_edge * r_y[0])
        ax_map.plot(ex, ey, color=col, linewidth=lw, alpha=al, zorder=2)

    # Highlight Sky-Bridge & Strobe Tunnel ribbons
    sf = s_grid / l3d
    m_br = (sf >= 0.33) & (sf < 0.50)
    m_tu = (sf >= 0.71) & (sf <= 0.85)
    ax_map.plot(X[m_br], Y[m_br], color="#00F0FF", linewidth=12, alpha=0.22, solid_capstyle="round", label="Sky-Bridge (Z=+42m)")
    ax_map.plot(X[m_tu], Y[m_tu], color="#B829FF", linewidth=13, alpha=0.28, solid_capstyle="round", label="Cyber-Strobe Tunnel")
    ax_map.plot(Xc, Yc, color="#52628E", linewidth=0.9, linestyle="--", alpha=0.6, label="Centerline")

    # Speed-colored optimal racing_xy
    v_kmh = V_mps * 3.6
    rpts = np.column_stack([np.append(RX, RX[0]), np.append(RY, RY[0])]).reshape(-1, 1, 2)
    segs = np.concatenate([rpts[:-1], rpts[1:]], axis=1)
    lc = LineCollection(segs, cmap="plasma", norm=plt.Normalize(75.0, 348.0), linewidths=3.4, zorder=5)
    lc.set_array(v_kmh)
    ax_map.add_collection(lc)
    cbar = fig.colorbar(lc, ax=ax_map, orientation="horizontal", pad=0.045, fraction=0.038)
    cbar.set_label("Optimal Racing Line Speed (km/h)", color="#D7E2FF")

    # Zone boundary markers & labels
    zone_defs = [
        ("Z1: Canyon Grid\n(s=0.00)", 0.00, "#00F0FF"),
        ("Z2: Eau-Rouge Climb\n(+42m / +13.4°)", 0.16, "#FFB800"),
        ("Z3: Sky-Bridge\n(Z=+42m, bridge)", 0.33, "#00FFAA"),
        ("Z4: 188° Bowl (+17.4°)\n& Corkscrew (-14.2°)", 0.50, "#FF5E00"),
        ("Z5: Strobe Tunnel\n& Harbor Hairpin", 0.70, "#FF2A6D"),
    ]
    for label, zf, zcol in zone_defs:
        idx = int(round(zf * len(s_grid))) % len(s_grid)
        ax_map.scatter([X[idx]], [Y[idx]], s=90, color=zcol, edgecolors="white", linewidths=1.5, zorder=8)
        ax_map.annotate(
            label,
            xy=(X[idx], Y[idx]),
            xytext=(X[idx] + 22.0, Y[idx] + 22.0),
            fontsize=8.8, fontweight="bold", color=zcol,
            bbox=dict(boxstyle="round,pad=0.25", fc="#090B14", ec=zcol, alpha=0.88),
            zorder=9,
        )

    # Start/Finish direction arrow
    ax_map.annotate(
        "", xy=(X[18], Y[18]), xytext=(X[0], Y[0]),
        arrowprops=dict(arrowstyle="->", color="#00F0FF", lw=2.8), zorder=10,
    )
    ax_map.set_aspect("equal", adjustable="datalim")
    ax_map.grid(True, alpha=0.45)
    ax_map.set_xlabel("World X (m)")
    ax_map.set_ylabel("World Y (m)")
    ax_map.set_title(
        f"2D XY Circuit Layout (Min Non-Adjacent XY Separation = {meta['min_non_adjacent_xy_sep_m']:.1f} m >= 75 m)",
        color="#ECF2FF", fontsize=11.5, fontweight="bold",
    )
    ax_map.legend(loc="lower left", facecolor="#090B14", edgecolor="#2B3558", fontsize=9)

    # Helper to shade zones on telemetry subplots
    zone_spans = [
        (0.00, 0.16, "#00F0FF", "Canyon"),
        (0.16, 0.33, "#FFB800", "Eau-Rouge"),
        (0.33, 0.50, "#00FFAA", "Sky-Bridge"),
        (0.50, 0.70, "#FF5E00", "Bowl+Corkscrew"),
        (0.70, 1.00, "#FF2A6D", "Tunnel+Harbor"),
    ]
    for ax in (ax_z, ax_v, ax_b):
        for a, b, zc, zlbl in zone_spans:
            ax.axvspan(a * l3d, b * l3d, color=zc, alpha=0.06)
            ax.axvline(a * l3d, color=zc, linestyle=":", linewidth=0.9, alpha=0.5)
        ax.set_xlim(0.0, l3d)
        ax.grid(True, alpha=0.45)

    # --- Subplot 1: Elevation Z & Pitch ---
    ax_z.plot(s_grid, Z, color="#00F0FF", linewidth=2.3, label="Centerline Z (m)")
    ax_z.fill_between(s_grid, 0.0, Z, color="#00F0FF", alpha=0.14)
    ax_z.set_ylabel("Elevation Z (m)", color="#00F0FF")
    ax_z2 = ax_z.twinx()
    ax_z2.plot(s_grid, pitch_deg, color="#FFB800", linewidth=1.6, alpha=0.9, label="Pitch (°)")
    ax_z2.axhline(0.0, color="#6C7BA8", linewidth=0.7, linestyle="--")
    ax_z2.set_ylabel("Pitch Angle (°)", color="#FFB800")
    ax_z.set_title(
        f"3D Elevation & Slope Profile (Peak Climb +{float(pitch_deg.max()):.2f}°, Plunge {float(pitch_deg.min()):.2f}°)",
        fontsize=10.8, fontweight="bold",
    )
    for a, b, zc, zlbl in zone_spans:
        ax_z.text(0.5 * (a + b) * l3d, 44.8, zlbl, color=zc, fontsize=8.5, ha="center", fontweight="bold")
    ax_z.set_ylim(-2.0, 48.5)
    ax_z2.set_ylim(-18.0, 18.0)

    # --- Subplot 2: Speed (km/h) & Lateral G ---
    lat_g = (V_mps ** 2) * np.abs(curv_race) / 9.81
    ax_v.plot(s_grid, v_kmh, color="#FF2A6D", linewidth=2.3, label="Speed (km/h)")
    ax_v.axvspan(0.71 * l3d, 0.85 * l3d, color="#B829FF", alpha=0.16, label="Cyber-Strobe Tunnel")
    ax_v.set_ylabel("Speed (km/h)", color="#FF2A6D")
    ax_v.set_ylim(55.0, 365.0)
    ax_v2 = ax_v.twinx()
    ax_v2.plot(s_grid, lat_g, color="#00FFAA", linewidth=1.4, alpha=0.85, label="|Lateral G|")
    ax_v2.set_ylabel("Lateral Accel (g)", color="#00FFAA")
    ax_v2.set_ylim(0.0, 7.2)
    ax_v.set_title(
        f"Calibrated F1 Speed & Aero/Banked Grip (Tunnel Peak {float(v_kmh.max()):.1f} km/h -> Hairpin {float(v_kmh.min()):.1f} km/h)",
        fontsize=10.8, fontweight="bold",
    )

    # --- Subplot 3: Banking Angle & Racing Line Offset ---
    ax_b.plot(s_grid, bank_deg, color="#FF9E00", linewidth=2.3, label="Bank Angle (°)")
    ax_b.fill_between(s_grid, 0.0, bank_deg, color="#FF9E00", alpha=0.15)
    ax_b.set_ylabel("Bank Angle (°)", color="#FF9E00")
    ax_b.set_ylim(-9.0, 21.0)
    ax_b2 = ax_b.twinx()
    ax_b2.plot(s_grid, off, color="#66D9FF", linewidth=1.5, alpha=0.9, label="Racing Offset (m, +L/-R)")
    ax_b2.axhline(0.0, color="#6C7BA8", linewidth=0.7, linestyle="--")
    ax_b2.set_ylabel("Racing Offset (m)", color="#66D9FF")
    ax_b2.set_ylim(-6.5, 6.5)
    ax_b.set_xlabel("3D Centerline Arc Length s (m)")
    ax_b.set_title(
        f"Track Banking (+Inward Right / -Inward Left) & Optimal Racing Offset ([{float(off.min()):.2f}, +{float(off.max()):.2f}] m)",
        fontsize=10.8, fontweight="bold",
    )

    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    fig.savefig(map_path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. Main Execution & Strict Verification Suite
# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)

    FPS = 24
    BEATS = 96
    BPM = 108
    FRAME_END = 1281
    TRACK_HALF_WIDTH_M = 7.0
    TARGET_LAP_S = BEATS * (60.0 / BPM)  # 53.3333333 s

    TARGET_N = 1860
    STEP_M = 2.0

    s_grid, l3d, cs_x, cs_y, cs_z, closure_angles = build_centerline_3d(TARGET_N, STEP_M)
    sf = s_grid / l3d

    (
        X, Y, Z,
        RX, RY, RZ,
        off,
        heading_deg,
        pitch_deg,
        bank_deg,
        curv_race,
        kap_cl,
    ) = build_banking_and_racing_line(s_grid, l3d, cs_x, cs_y, cs_z)

    scalar_opt, sim_lap_s, V_mps, t_arr, dt_arr, ds_race = solve_calibrated_velocity(
        sf, RX, RY, RZ, pitch_deg, bank_deg, curv_race, TARGET_LAP_S
    )

    # --- Strict Geometry, Continuity & Physics Verification ---
    # 1) Uniform 2.0m 3D centerline spacing & seamless loop closure (including N-1 -> 0!)
    X_ext = np.append(X, X[0])
    Y_ext = np.append(Y, Y[0])
    Z_ext = np.append(Z, Z[0])
    seg_3d = np.sqrt(np.diff(X_ext) ** 2 + np.diff(Y_ext) ** 2 + np.diff(Z_ext) ** 2)
    measured_len_m = float(np.sum(seg_3d))
    max_step_err = float(np.max(np.abs(seg_3d - STEP_M)))
    seam_step_m = float(seg_3d[-1])

    # Spline periodic closure gap at s = L3D vs s = 0
    closure_gap_m = float(math.sqrt(
        (float(cs_x(l3d)) - float(cs_x(0.0))) ** 2
        + (float(cs_y(l3d)) - float(cs_y(0.0))) ** 2
        + (float(cs_z(l3d)) - float(cs_z(0.0))) ** 2
    ))

    # 2) Seam step continuity across (N-1) -> 0 vs interior max step
    def cyclic_abs_diff(arr, is_angle_deg=False):
        d = np.roll(arr, -1) - arr
        if is_angle_deg:
            d = (d + 180.0) % 360.0 - 180.0
        return np.abs(d)

    d_head = cyclic_abs_diff(heading_deg, is_angle_deg=True)
    d_pitch = cyclic_abs_diff(pitch_deg)
    d_bank = cyclic_abs_diff(bank_deg)
    d_curv = cyclic_abs_diff(curv_race)
    d_vel = cyclic_abs_diff(V_mps)

    assert 3550.0 <= measured_len_m <= 3750.0, f"Length out of range: {measured_len_m}"
    assert max_step_err < 0.015, f"3D step non-uniformity too high: {max_step_err}"
    assert closure_gap_m < 1e-9, f"Non-zero spline closure gap: {closure_gap_m}"
    assert float(d_curv.max()) < 0.008, f"Curvature spike detected: {d_curv.max()}"
    assert float(d_head[-1]) < 0.5 and float(d_pitch[-1]) < 0.2 and float(d_bank[-1]) < 0.2 and float(d_vel[-1]) < 1.0, (
        "Closure seam jump detected!"
    )
    assert abs(sim_lap_s - TARGET_LAP_S) <= 0.15, f"Lap time mismatch: {sim_lap_s}"
    assert float( np.max(np.abs(off)) ) <= 5.2001, f"Racing offset exceeds ±5.2m: {np.max(np.abs(off))}"

    # 3) Anti-drift check against unscaled aero + banking grip limit
    a_lat_actual = (V_mps ** 2) * np.abs(curv_race)
    a_lat_unscaled = 16.5 + 0.0075 * (V_mps ** 2) + 9.81 * np.tan(np.abs(np.radians(bank_deg)))
    over_grip = int(np.sum(a_lat_actual > a_lat_unscaled + 1e-4))
    assert over_grip == 0, f"Anti-drift failed on {over_grip} points!"

    # 4) Non-adjacent XY separation check (all pairs with cyclic arc distance >= 120 m)
    min_xy_sep = 1e9
    min_xy_pair = (0, 0)
    for i in range(0, TARGET_N, 2):
        ds_cyc = np.minimum((s_grid - s_grid[i]) % l3d, (s_grid[i] - s_grid) % l3d)
        dxy = np.hypot(X - X[i], Y - Y[i])
        mask = ds_cyc >= 120.0
        local_min = float(np.min(dxy[mask]))
        if local_min < min_xy_sep:
            j = int(np.where(mask)[0][int(np.argmin(dxy[mask]))])
            min_xy_sep = local_min
            min_xy_pair = (i, j)
    assert min_xy_sep >= 75.0, f"XY separation < 75m: {min_xy_sep:.2f}m at {min_xy_pair}"

    # 5) Set-piece kinematic checks
    assert 12.5 <= float(pitch_deg.max()) <= 14.0, f"Peak climb pitch out of 12.5..14.0: {pitch_deg.max():.2f}"
    assert -15.0 <= float(pitch_deg.min()) <= -13.5, f"Plunge pitch out of -15.0..-13.5: {pitch_deg.min():.2f}"
    assert 16.0 <= float(bank_deg.max()) <= 18.0, f"Peak bank out of 16..18: {bank_deg.max():.2f}"
    v_kmh = V_mps * 3.6
    assert 338.0 <= float(v_kmh.max()) <= 346.0, f"Tunnel peak speed out of 338..346 km/h: {v_kmh.max():.1f}"
    assert 79.0 <= float(v_kmh.min()) <= 85.0, f"Hairpin min speed out of 79..85 km/h: {v_kmh.min():.1f}"

    # --- Build Zone & Landmark Summary Table (Frames 1..1281 @ 24 fps) ---
    dt_frame = sim_lap_s / (FRAME_END - 1)

    def t_to_frame(t_val):
        return int(round(1.0 + t_val / dt_frame))

    zone_ranges = [
        ("canyon_grid", 0.00, 0.16),
        ("eau_rouge_climb", 0.16, 0.33),
        ("sky_bridge", 0.33, 0.50),
        ("banked_bowl_plunge", 0.50, 0.70),
        ("strobe_tunnel_harbor", 0.70, 1.00),
    ]
    zones_meta = []
    for zname, a, b in zone_ranges:
        idxs = np.where((sf >= a) & (sf < b))[0]
        i0, i1 = int(idxs[0]), int(idxs[-1])
        t0_z = float(t_arr[i0])
        t1_z = float(t_arr[i1] + dt_arr[i1]) if b >= 1.0 else float(t_arr[i1 + 1])
        zones_meta.append({
            "zone": zname,
            "s_frac": [a, b],
            "idx_range": [i0, i1],
            "s_m": [round(float(s_grid[i0]), 1), round(float(s_grid[i1] + STEP_M), 1)],
            "t_s": [round(t0_z, 3), round(t1_z, 3)],
            "frames": [t_to_frame(t0_z), t_to_frame(t1_z)],
            "z_range_m": [round(float(Z[idxs].min()), 2), round(float(Z[idxs].max()), 2)],
            "pitch_range_deg": [round(float(pitch_deg[idxs].min()), 2), round(float(pitch_deg[idxs].max()), 2)],
            "bank_range_deg": [round(float(bank_deg[idxs].min()), 2), round(float(bank_deg[idxs].max()), 2)],
            "v_range_kmh": [round(float(v_kmh[idxs].min()), 1), round(float(v_kmh[idxs].max()), 1)],
        })

    # Key cinematic landmarks (for @env-2 set-pieces, @anim Impact Frames & shots, @sfx drops/sparks/reverb)
    d_pitch_ds = cyclic_abs_diff(pitch_deg) / STEP_M
    idx_chicane = int(np.argmin(V_mps[(sf >= 0.08) & (sf < 0.16)]) + np.where(sf >= 0.08)[0][0])
    idx_er_comp = int(np.argmax(np.diff(np.append(pitch_deg, pitch_deg[0]))[(sf >= 0.16) & (sf < 0.23)]) + np.where(sf >= 0.16)[0][0])
    idx_er_steep = int(np.argmax(pitch_deg))
    idx_er_crest = int(np.argmin(np.abs(sf - 0.322)))
    idx_bowl_mid = int(np.argmax(bank_deg))
    idx_cork_plunge = int(np.argmin(pitch_deg))
    idx_tun_in = int(np.where(sf >= 0.71)[0][0])
    idx_tun_out = int(np.where(sf <= 0.85)[0][-1])
    idx_vmax = int(np.argmax(V_mps))
    long_acc = (np.roll(V_mps, -1) ** 2 - V_mps ** 2) / (2.0 * ds_race)
    idx_brk_slam = int(np.argmin(long_acc[(sf >= 0.85) & (sf <= 0.92)]) + np.where(sf >= 0.85)[0][0])
    idx_hairpin = int(np.argmin(V_mps))

    def lm_entry(name, idx):
        return {
            "event": name,
            "idx": int(idx),
            "s_m": round(float(s_grid[idx]), 1),
            "s_frac": round(float(sf[idx]), 4),
            "t_s": round(float(t_arr[idx]), 3),
            "frame": t_to_frame(float(t_arr[idx])),
            "z_m": round(float(Z[idx]), 2),
            "v_kmh": round(float(v_kmh[idx]), 1),
            "pitch_deg": round(float(pitch_deg[idx]), 2),
            "bank_deg": round(float(bank_deg[idx]), 2),
        }

    landmarks = [
        lm_entry("canyon_chicane_apex", idx_chicane),
        lm_entry("eau_rouge_compression_sparks", idx_er_comp),
        lm_entry("raidillon_max_climb_pitch", idx_er_steep),
        lm_entry("eau_rouge_42m_blind_crest", idx_er_crest),
        lm_entry("carousel_bowl_17deg_apex", idx_bowl_mid),
        lm_entry("corkscrew_max_plunge_pitch", idx_cork_plunge),
        lm_entry("strobe_tunnel_entry", idx_tun_in),
        lm_entry("strobe_tunnel_exit", idx_tun_out),
        lm_entry("top_speed_peak", idx_vmax),
        lm_entry("harbor_hairpin_heavy_brake_slam", idx_brk_slam),
        lm_entry("harbor_hairpin_82kmh_apex", idx_hairpin),
    ]

    # --- Assemble Exact JSON Contract ---
    points = []
    for i in range(TARGET_N):
        s_frac_i = float(sf[i])
        points.append({
            "s": round(float(s_grid[i]), 3),
            "xy": [round(float(X[i]), 4), round(float(Y[i]), 4)],
            "z": round(float(Z[i]), 4),
            "racing_xy": [round(float(RX[i]), 4), round(float(RY[i]), 4)],
            "racing_z": round(float(RZ[i]), 4),
            "racing_offset_m": round(float(off[i]), 4),
            "heading_deg": round(float(heading_deg[i]), 4),
            "pitch_deg": round(float(pitch_deg[i]), 4),
            "bank_deg": round(float(bank_deg[i]), 4),
            "curv_1pm": round(float(curv_race[i]), 6),
            "v_mps": round(float(V_mps[i]), 4),
            "t": round(float(t_arr[i]), 5),
            "zone": zone_name_at(s_frac_i),
            "tunnel": bool(0.71 <= s_frac_i <= 0.85),
            "bridge": bool(0.33 <= s_frac_i < 0.50),
        })

    meta = {
        "name": "Neo-Monaco x Nueva York 2099 Sky-Harbor",
        "measured_length_km": round(measured_len_m / 1000.0, 4),
        "track_half_width_m": TRACK_HALF_WIDTH_M,
        "sim_lap_s": round(sim_lap_s, 4),
        "fps": FPS,
        "beats": BEATS,
        "bpm": BPM,
        "frame_end": FRAME_END,
        "max_z_m": round(float(Z.max()), 3),
        "max_bank_deg": round(float(np.abs(bank_deg).max()), 3),
        "min_z_m": round(float(Z.min()), 3),
        "max_pitch_deg": round(float(pitch_deg.max()), 3),
        "min_pitch_deg": round(float(pitch_deg.min()), 3),
        "v_max_kmh": round(float(v_kmh.max()), 2),
        "v_min_kmh": round(float(v_kmh.min()), 2),
        "sim_avg_kmh": round(float(measured_len_m / sim_lap_s * 3.6), 2),
        "points_count": TARGET_N,
        "sample_step_m": STEP_M,
        "calibration_scalar": round(float(scalar_opt), 5),
        "closure_gap_m": round(closure_gap_m, 12),
        "seam_step_3d_m": round(seam_step_m, 6),
        "min_non_adjacent_xy_sep_m": round(min_xy_sep, 2),
        "anti_drift_max_lat_g": round(float(a_lat_actual.max() / 9.81), 3),
        "anti_drift_violations": over_grip,
        "frame_convention": {
            "units": "SI: meters, seconds, m/s, degrees",
            "heading_deg": "CCW from +X in [-180, 180], exact racing-line horizontal tangent",
            "pitch_deg": "atan2(dz, ds_xy), +uphill climb, -downhill plunge",
            "bank_deg": "Right-hand roll around +Forward tangent T: +bank tilts road normal toward +Right (inward on right turns), -bank tilts toward +Left (inward on left turns)",
            "curv_1pm": "Signed horizontal curvature of racing_xy (+left CCW, -right CW)",
            "racing_offset_m": "Signed lateral offset along banked surface (+left = -Right_vec, -right = +Right_vec): P_race_3d = C_3d - racing_offset_m * Right_banked",
            "ribbon_basis_python": (
                "h, pt, bk = radians(heading_deg), radians(pitch_deg), radians(bank_deg); "
                "T = Vector((cos(pt)*cos(h), cos(pt)*sin(h), sin(pt))); "
                "R0 = Vector((sin(h), -cos(h), 0.0)); "
                "U0 = Vector((-sin(pt)*cos(h), -sin(pt)*sin(h), cos(pt))); "
                "R = cos(bk)*R0 - sin(bk)*U0; U = sin(bk)*R0 + cos(bk)*U0"
            ),
        },
        "zones": zones_meta,
        "landmarks": landmarks,
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "points": points}, f, ensure_ascii=False, indent=1)

    render_diagnostic_chart(
        MAP_PATH, s_grid, l3d, X, Y, Z, RX, RY, off, heading_deg, pitch_deg, bank_deg, curv_race, V_mps, t_arr, meta
    )

    # Verify PNG via PIL/NumPy stats only (NEVER view binary with read_file!)
    im = Image.open(MAP_PATH)
    arr = np.asarray(im)
    png_bytes = os.path.getsize(MAP_PATH)
    json_bytes = os.path.getsize(JSON_PATH)
    assert arr.shape[0] == 1400 and arr.shape[1] == 2200, f"Unexpected PNG shape: {arr.shape}"
    assert float(arr[..., :3].std()) > 25.0, "Diagnostic PNG looks blank/low-contrast!"

    elapsed = time.time() - t_start
    print(f"=== V6 CIRCUIT BUILD COMPLETE in {elapsed:.2f} s ===")
    print(f"JSON: {JSON_PATH} ({json_bytes:,} B, {TARGET_N} pts @ {STEP_M:.1f} m)")
    print(f"MAP : {MAP_PATH} ({png_bytes:,} B, {arr.shape[1]}x{arr.shape[0]} px, RGB mean={arr[...,:3].mean():.1f}, std={arr[...,:3].std():.1f})")
    print(
        f"Length={measured_len_m:.3f} m ({meta['measured_length_km']:.4f} km) | "
        f"closure_gap={closure_gap_m:.2e} m | seam_step={seam_step_m:.5f} m | max_step_err={max_step_err:.5f} m"
    )
    print(
        f"Seam diffs (N-1 -> 0): d_head={d_head[-1]:.4f} deg, d_pitch={d_pitch[-1]:.4f} deg, "
        f"d_bank={d_bank[-1]:.4f} deg, d_curv={d_curv[-1]:.6f}, d_v={d_vel[-1]:.4f} m/s"
    )
    print(
        f"Max interior step diffs: max_d_curv={d_curv.max():.6f} | "
        f"min_non_adj_XY_sep={min_xy_sep:.2f} m | calibration_scalar={scalar_opt:.5f}"
    )
    print(
        f"Kinematics: sim_lap_s={sim_lap_s:.4f} s | v=[{v_kmh.min():.1f}, {v_kmh.max():.1f}] km/h "
        f"(avg {meta['sim_avg_kmh']:.1f} km/h) | Z=[{Z.min():.2f}, {Z.max():.2f}] m | "
        f"pitch=[{pitch_deg.min():.2f}, +{pitch_deg.max():.2f}] deg | bank=[{bank_deg.min():.2f}, +{bank_deg.max():.2f}] deg | "
        f"max_lat_g={meta['anti_drift_max_lat_g']:.2f} g (0 violations)"
    )
    print("\n--- ZONES TABLE ---")
    for zm in zones_meta:
        print(
            f"  {zm['zone']:22s} | s={zm['s_m'][0]:6.1f}..{zm['s_m'][1]:6.1f} m ({zm['s_frac'][0]:.2f}..{zm['s_frac'][1]:.2f}) | "
            f"t={zm['t_s'][0]:6.3f}..{zm['t_s'][1]:6.3f} s | f={zm['frames'][0]:4d}..{zm['frames'][1]:4d} | "
            f"Z={zm['z_range_m'][0]:5.1f}..{zm['z_range_m'][1]:5.1f} m | "
            f"pitch={zm['pitch_range_deg'][0]:6.2f}..{zm['pitch_range_deg'][1]:6.2f}° | "
            f"bank={zm['bank_range_deg'][0]:5.1f}..{zm['bank_range_deg'][1]:5.1f}° | "
            f"v={zm['v_range_kmh'][0]:5.1f}..{zm['v_range_kmh'][1]:5.1f} km/h"
        )
    print("\n--- LANDMARKS TABLE ---")
    for lm in landmarks:
        print(
            f"  {lm['event']:34s} | idx={lm['idx']:4d} | s={lm['s_m']:6.1f} m ({lm['s_frac']:.3f}) | "
            f"t={lm['t_s']:6.3f} s | f={lm['frame']:4d} | Z={lm['z_m']:5.2f} m | "
            f"v={lm['v_kmh']:5.1f} km/h | pitch={lm['pitch_deg']:+6.2f}° | bank={lm['bank_deg']:+5.1f}°"
        )


if __name__ == "__main__":
    main()
