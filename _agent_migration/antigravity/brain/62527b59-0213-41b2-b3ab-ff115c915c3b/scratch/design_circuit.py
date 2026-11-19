# -*- coding: utf-8 -*-
import math, time
import numpy as np
from scipy.optimize import root, brentq, minimize
from scipy.interpolate import CubicSpline

def smooth_bump(u, u0, u1, edge_frac=0.35):
    w = (u1 - u0) % 1.0
    du = (u - u0) % 1.0
    out = np.zeros_like(u, dtype=float)
    e = max(1e-6, min(0.499, edge_frac)) * w
    m_rise = (du > 0.0) & (du < e)
    x = du[m_rise] / e
    out[m_rise] = x**3 * (10.0 - 15.0 * x + 6.0 * x * x)
    m_flat = (du >= e) & (du <= w - e)
    out[m_flat] = 1.0
    m_fall = (du > w - e) & (du < w)
    x = (w - du[m_fall]) / e
    out[m_fall] = x**3 * (10.0 - 15.0 * x + 6.0 * x * x)
    return out

def smooth_step_quintic(x):
    x = np.clip(x, 0.0, 1.0)
    return x**3 * (10.0 - 15.0 * x + 6.0 * x * x)

def corner_turn(u, u0, u1, angle_deg, edge_frac=0.35):
    b = smooth_bump(u, u0, u1, edge_frac=edge_frac)
    integ = np.sum(b) / len(u)
    return b * (math.radians(angle_deg) / max(integ, 1e-12))

M = 12000
u = np.linspace(0.0, 1.0, M, endpoint=False)
du = 1.0 / M

def build_xy_unit(params):
    a_raid, a_bk, a_hp = params
    corners = [
        # Zone 1: canyon_grid (0.00 .. 0.16)
        (0.098, 0.123, -80.0, 0.34),   # Tight Canyon Chicane Right
        (0.123, 0.149, +76.0, 0.34),   # Tight Canyon Chicane Left
        # Zone 2: eau_rouge_climb (0.16 .. 0.33)
        (0.164, 0.198, +42.0, 0.40),   # Eau-Rouge bottom compression Left
        (0.198, 0.284, a_raid, 0.38),  # Raidillon sweeping uphill Right
        (0.286, 0.326, +46.0, 0.38),   # Blind crest Left sweep onto Sky-Bridge (~260 km/h -> accelerates on bridge!)
        # Zone 3: sky_bridge (0.33 .. 0.50)
        (0.395, 0.442, a_bk,  0.40),   # Fast Sky-Bridge aero kink
        # Zone 4: banked_bowl_plunge (0.50 .. 0.70)
        (0.502, 0.576, -188.0, 0.26),  # Sweeping 188-deg Right-Hand Carousel Bowl!
        (0.598, 0.629, +88.0, 0.34),   # Laguna-Seca Corkscrew tight blind Left drop!
        (0.631, 0.670, -52.0, 0.36),   # Corkscrew Right sweep toward tunnel!
        # Zone 5: strobe_tunnel_harbor (0.70 .. 1.00)
        (0.715, 0.845, +12.0, 0.46),   # Gentle flat-out Cyber-Strobe Tunnel curve
        (0.854, 0.878, +18.0, 0.42),   # Blinding exit cliffside sweep before heavy braking
        (0.898, 0.9162, a_hp, 0.26),   # Heavy-Braking Cliffside Harbor Hairpin (82 km/h!)
        (0.946, 0.985, -36.0, 0.45),   # Fast Harbor Waterfront bend onto Finish Straight
    ]
    kap = np.zeros_like(u)
    for u0, u1, ang, ef in corners:
        kap += corner_turn(u, u0, u1, ang, ef)

    theta = np.cumsum(kap) * du
    theta -= theta[0]
    total_dtheta = np.sum(kap) * du
    cx = np.sum(np.cos(theta)) * du
    cy = np.sum(np.sin(theta)) * du
    return kap, theta, np.array([total_dtheta + 2.0 * math.pi, cx, cy])

sol = root(lambda p: build_xy_unit(p)[2], x0=[-185.0, 25.0, -118.0], method='hybr', tol=1e-12)
print("Solver success:", sol.success, "params (deg):", sol.x)

kap_u, theta_u, _ = build_xy_unit(sol.x)
x_u = np.cumsum(np.cos(theta_u)) * du
y_u = np.cumsum(np.sin(theta_u)) * du
x_u -= x_u[0]
y_u -= y_u[0]

def build_z_profile(u):
    z = np.full_like(u, 0.8)
    z += 2.2 * smooth_step_quintic((u - 0.05) / (0.16 - 0.05))
    # Eau-Rouge climb: Z = 3.0 -> +42.0m, pitch_deg peaking ~ +13.3 deg!
    z += 4.6 * smooth_step_quintic((u - 0.160) / (0.326 - 0.160))
    z += 34.4 * smooth_step_quintic((u - 0.196) / (0.2725 - 0.196))
    # Sky-Bridge crown (+42.0 -> +42.35 -> +42.0m)
    z += 0.35 * np.sin(np.pi * np.clip((u - 0.33) / 0.17, 0.0, 1.0))**2
    # Bowl rim + Corkscrew plunge: Z = +42.0 -> +1.5m, pitch_deg reaching ~ -14.3 deg!
    z -= 4.3 * smooth_step_quintic((u - 0.525) / (0.696 - 0.525))
    z -= 36.2 * smooth_step_quintic((u - 0.600) / (0.678 - 0.600))
    # Tunnel (1.5m) -> Finish (0.8m)
    z -= 0.7 * smooth_step_quintic((u - 0.860) / (0.975 - 0.860))
    return z

Z_raw = build_z_profile(u)

TARGET_N = 1825
TARGET_L3D = TARGET_N * 2.0  # 3650.0 m

def calc_l3d(L2D):
    X = np.append(x_u * L2D, x_u[0] * L2D)
    Y = np.append(y_u * L2D, y_u[0] * L2D)
    Z = np.append(Z_raw, Z_raw[0])
    return float(np.sum(np.sqrt(np.diff(X)**2 + np.diff(Y)**2 + np.diff(Z)**2)))

L2D_opt = brentq(lambda L: calc_l3d(L) - TARGET_L3D, 3300.0, 3800.0, xtol=1e-10)
X_dense = np.append(x_u * L2D_opt, x_u[0] * L2D_opt)
Y_dense = np.append(y_u * L2D_opt, y_u[0] * L2D_opt)
Z_dense = np.append(Z_raw, Z_raw[0])
ds_dense = np.sqrt(np.diff(X_dense)**2 + np.diff(Y_dense)**2 + np.diff(Z_dense)**2)
s_dense = np.concatenate([[0.0], np.cumsum(ds_dense)])
s_dense[-1] = TARGET_L3D

cs_x = CubicSpline(s_dense, X_dense, bc_type='periodic')
cs_y = CubicSpline(s_dense, Y_dense, bc_type='periodic')
cs_z = CubicSpline(s_dense, Z_dense, bc_type='periodic')

s_grid = np.arange(TARGET_N, dtype=float) * 2.0
sf = s_grid / TARGET_L3D
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
kap_cl = (dx * ddy - dy * ddx) / np.maximum(dxy**3, 1e-12)

bank_deg = (
    +17.4 * smooth_bump(sf, 0.498, 0.580, edge_frac=0.30)
    - 4.0 * smooth_bump(sf, 0.162, 0.200, edge_frac=0.42)
    + 5.8 * smooth_bump(sf, 0.198, 0.286, edge_frac=0.40)
    - 5.5 * smooth_bump(sf, 0.598, 0.630, edge_frac=0.38)
    + 4.5 * smooth_bump(sf, 0.630, 0.670, edge_frac=0.40)
    + 1.2 * smooth_bump(sf, 0.896, 0.917, edge_frac=0.38)
)

ds0 = 2.0
w_d1 = 1.2e-5
w_d3 = 8.0e-2
w_c  = 1.5e-8

def race_obj_and_grad(off):
    om1 = np.roll(off, 1)
    op1 = np.roll(off, -1)
    om2 = np.roll(off, 2)
    op2 = np.roll(off, -2)
    d2 = (op1 - 2.0 * off + om1) / (ds0 * ds0)
    d1 = (op1 - om1) / (2.0 * ds0)
    d3 = (op2 - 2.0 * op1 + 2.0 * om1 - om2) / (2.0 * ds0**3)
    c1 = 1.0 + kap_cl * off
    keff = kap_cl * c1 + d2
    loss = 0.5 * np.sum(keff**2 + w_d1 * d1**2 + w_d3 * d3**2 + w_c * off**2)
    g_keff = keff
    grad = g_keff * (kap_cl * kap_cl) + (np.roll(g_keff, 1) - 2.0 * g_keff + np.roll(g_keff, -1)) / (ds0 * ds0)
    g_d1 = w_d1 * d1
    grad += (np.roll(g_d1, 1) - np.roll(g_d1, -1)) / (2.0 * ds0)
    g_d3 = w_d3 * d3
    grad += (np.roll(g_d3, 2) - 2.0 * np.roll(g_d3, 1) + 2.0 * np.roll(g_d3, -1) - np.roll(g_d3, -2)) / (2.0 * ds0**3)
    grad += w_c * off
    return float(loss), grad

res_opt = minimize(
    race_obj_and_grad,
    np.zeros(TARGET_N),
    jac=True,
    method='L-BFGS-B',
    bounds=[(-5.10, 5.10)] * TARGET_N,
    options={'maxiter': 600, 'ftol': 1e-12, 'gtol': 1e-9}
)
off = res_opt.x
kh = 12
kx = np.arange(-kh, kh + 1, dtype=float)
kw = np.exp(-0.5 * (kx / 2.5)**2)
kw /= kw.sum()
off = np.convolve(np.concatenate([off[-kh:], off, off[:kh]]), kw, mode='valid')
off = np.clip(off, -5.2, 5.2)

cl_h = np.arctan2(dy, dx)
h_rad = cl_h.copy()
pt_rad = np.radians(pitch_cl).copy()
bk_rad = np.radians(bank_deg)
s_ext = np.append(s_grid, TARGET_L3D)

for _ in range(6):
    R0_x, R0_y, R0_z = np.sin(h_rad), -np.cos(h_rad), np.zeros_like(h_rad)
    U0_x = -np.sin(pt_rad) * np.cos(h_rad)
    U0_y = -np.sin(pt_rad) * np.sin(h_rad)
    U0_z = np.cos(pt_rad)
    Rx = np.cos(bk_rad) * R0_x - np.sin(bk_rad) * U0_x
    Ry = np.cos(bk_rad) * R0_y - np.sin(bk_rad) * U0_y
    Rz = np.cos(bk_rad) * R0_z - np.sin(bk_rad) * U0_z
    RX = X - off * Rx
    RY = Y - off * Ry
    RZ = Z - off * Rz
    cs_rx = CubicSpline(s_ext, np.append(RX, RX[0]), bc_type='periodic')
    cs_ry = CubicSpline(s_ext, np.append(RY, RY[0]), bc_type='periodic')
    cs_rz = CubicSpline(s_ext, np.append(RZ, RZ[0]), bc_type='periodic')
    drx = cs_rx(s_grid, 1)
    dry = cs_ry(s_grid, 1)
    drz = cs_rz(s_grid, 1)
    drxy = np.hypot(drx, dry)
    h_rad = np.arctan2(dry, drx)
    pt_rad = np.arctan2(drz, drxy)

ddrx = cs_rx(s_grid, 2)
ddry = cs_ry(s_grid, 2)
curv_race = (drx * ddry - dry * ddrx) / np.maximum(drxy**3, 1e-12)

for thresh in (115.0, 125.0, 140.0):
    min_sep = 1e9
    for i in range(0, TARGET_N, 2):
        ds_cyc = np.minimum((s_grid - s_grid[i]) % TARGET_L3D, (s_grid[i] - s_grid) % TARGET_L3D)
        dist_xy = np.hypot(X - X[i], Y - Y[i])
        m = dist_xy[ds_cyc >= thresh]
        if len(m) and m.min() < min_sep:
            min_sep = float(m.min())
    print(f"Min XY sep (|ds| >= {thresh:.0f}m): {min_sep:.2f} m")

RX_ext = np.append(RX, RX[0])
RY_ext = np.append(RY, RY[0])
RZ_ext = np.append(RZ, RZ[0])
ds_race = np.sqrt(np.diff(RX_ext)**2 + np.diff(RY_ext)**2 + np.diff(RZ_ext)**2)

def solve_lap(scalar):
    tun_boost = smooth_bump(sf, 0.705, 0.875, edge_frac=0.18)
    # Tunnel vmax peaks right at 95.1 m/s (342.4 km/h), open air DRS vmax = 92.5 m/s (333.0 km/h)
    vmax_arr = 92.5 * math.sqrt(scalar) + 3.6 * tun_boost

    a0_lat = 16.5 * scalar
    c_lat = 0.0075 * scalar
    bank_term = 9.81 * np.tan(np.abs(bk_rad)) * scalar

    k_abs = np.abs(curv_race)
    V = np.empty(TARGET_N)
    for i in range(TARGET_N):
        denom = k_abs[i] - c_lat
        if denom <= 1e-6:
            V[i] = vmax_arr[i]
        else:
            V[i] = min(vmax_arr[i], math.sqrt((a0_lat + bank_term[i]) / denom))

    sin_pt = np.sin(pt_rad)
    for _ in range(8):
        for i in range(TARGET_N - 1, -1, -1):
            vn = V[(i + 1) % TARGET_N]
            ds = ds_race[i]
            vi = vn
            for _ in range(3):
                vm = 0.5 * (vi + vn)
                abrk = scalar * min(56.0, 21.0 + 0.0052 * vm * vm) + 9.81 * sin_pt[i]
                abrk = max(5.0, abrk)
                vi = math.sqrt(vn * vn + 2.0 * abrk * ds)
            if vi < V[i]:
                V[i] = vi
        for i in range(TARGET_N):
            vp = V[i]
            ds = ds_race[i]
            p_pow = (990.0 + 260.0 * tun_boost[i]) * scalar
            a_tr = scalar * 16.4
            aacc = min(a_tr, p_pow / max(vp, 12.0)) - 9.81 * sin_pt[i]
            aacc = max(0.5, aacc)
            vn_max = min(vmax_arr[(i + 1) % TARGET_N], math.sqrt(vp * vp + 2.0 * aacc * ds))
            if vn_max < V[(i + 1) % TARGET_N]:
                V[(i + 1) % TARGET_N] = vn_max

    dt = ds_race / np.maximum(0.5 * (V + np.roll(V, -1)), 1.0)
    return float(np.sum(dt)), V, dt

TARGET_LAP_S = 96.0 * 60.0 / 108.0  # 53.333333 s
sc_opt = brentq(lambda s: solve_lap(s)[0] - TARGET_LAP_S, 0.70, 1.30, xtol=1e-9)
t_lap, V_opt, dt_opt = solve_lap(sc_opt)
print(f"Calibrated scalar = {sc_opt:.5f} -> sim_lap_s = {t_lap:.6f} s")
print(f"Speed range: [{V_opt.min()*3.6:.1f}, {V_opt.max()*3.6:.1f}] km/h ({V_opt.min():.2f} .. {V_opt.max():.2f} m/s)")
print(f"Bowl speed (sf 0.51..0.57): [{V_opt[(sf>=0.51)&(sf<=0.57)].min()*3.6:.1f}, {V_opt[(sf>=0.51)&(sf<=0.57)].max()*3.6:.1f}] km/h")
print(f"Tunnel speed (sf 0.71..0.85): [{V_opt[(sf>=0.71)&(sf<=0.85)].min()*3.6:.1f}, {V_opt[(sf>=0.71)&(sf<=0.85)].max()*3.6:.1f}] km/h")
for zname, a, b in [
    ("canyon_grid", 0.00, 0.16),
    ("eau_rouge_climb", 0.16, 0.33),
    ("sky_bridge", 0.33, 0.50),
    ("banked_bowl_plunge", 0.50, 0.70),
    ("strobe_tunnel_harbor", 0.70, 1.00),
]:
    m = (sf >= a) & (sf < b)
    print(f"  {zname:22s}: v=[{V_opt[m].min()*3.6:5.1f}, {V_opt[m].max()*3.6:5.1f}] km/h, Z=[{Z[m].min():5.1f}, {Z[m].max():5.1f}] m, pitch=[{np.degrees(pt_rad[m]).min():6.2f}, {np.degrees(pt_rad[m]).max():6.2f}], bank=[{bank_deg[m].min():5.1f}, {bank_deg[m].max():5.1f}]")
