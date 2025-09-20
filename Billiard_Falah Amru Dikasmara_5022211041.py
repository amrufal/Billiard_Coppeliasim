from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import math
import time

# ------------------- KONFIGURASI -------------------
BALL_NAMES = [
    "/Sphere[0]", "/Sphere[1]", "/Sphere[2]",
    "/Sphere[3]", "/Sphere[4]", "/Sphere[5]", "/Sphere[6]"
]
CUE_BALL = "/Sphere[6]"   # bola putih
OFFSET_SAFETY = 0.95      # clamp offset <= 0.95 * radius
# ---------------------------------------------------


# ----------------- UTIL INPUT (dialog) -----------------
def ask_float(prompt, default=None):
    while True:
        if default is not None:
            s = input(f"{prompt} [{default}]: ").strip()
        else:
            s = input(f"{prompt}: ").strip()

        if s == "" and default is not None:
            return float(default)
        try:
            return float(s)
        except ValueError:
            print("⚠️ Masukkan angka.")


def ask_choice(prompt, choices, default=None):
    choices_str = "/".join(choices)
    if default is not None:
        prompt_text = f"{prompt} ({choices_str}) [{default}]: "
    else:
        prompt_text = f"{prompt} ({choices_str}): "

    while True:
        s = input(prompt_text).strip()
        if s == "" and default is not None:
            return default
        if s in choices:
            return s
        print("⚠️ Pilihan tidak valid.")
# -------------------------------------------------------


# ----------------- UTIL VEKTOR & API -------------------
def norm2d(x, y):
    n = math.hypot(x, y)
    if n < 1e-12:
        return 0.0, 0.0, 0.0
    return x / n, y / n, 0.0


def vlen3(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)


def clamp_offset_to_radius(rx, ry, rz, radius, safety=0.95):
    """
    Batasi vektor offset terhadap COM agar |offset| <= safety * radius.
    Jika melebihi, skala turun proporsional.
    """
    r = math.sqrt(rx*rx + ry*ry + rz*rz)
    rmax = safety * radius
    if r < 1e-12:
        return 0.0, 0.0, 0.0, False
    if r <= rmax:
        return rx, ry, rz, False
    scale = rmax / r
    return rx*scale, ry*scale, rz*scale, True


def discover_balls(sim, names):
    balls = {}
    for name in names:
        handle = sim.getObject(name)
        balls[name] = handle
    return balls


def get_mass(sim, h):
    return sim.getShapeMass(h)


def get_diameter_radius(sim, h):
    # sphere primitive: dims[0] = diameter
    _, _, dims = sim.getShapeGeomInfo(h)
    d = float(dims[0])
    return d, 0.5 * d


def reset_body(sim, h, client):
    client.setStepping(True)
    sim.resetDynamicObject(h)
    sim.addForceAndTorque(h, [0, 0, 0], [0, 0, 0])
    client.step()
    client.setStepping(False)


def stop_all_balls(sim, handles, client):
    client.setStepping(True)
    for h in handles:
        sim.resetDynamicObject(h)
        sim.addForceAndTorque(h, [0, 0, 0], [0, 0, 0])
    client.step()
    client.setStepping(False)


def aim_direction(sim, cue_h, all_balls, target_method, target_name):
    """
    Hitung vektor unit arah cue -> target pada bidang XY.
    """
    pc = sim.getObjectPosition(cue_h, -1)

    if target_method == "by_name":
        if target_name not in all_balls:
            raise RuntimeError(f"Target '{target_name}' tidak ada.")
        tgt_h = all_balls[target_name]
    else:
        tgt_h = None
        mind = float('inf')
        for name in all_balls.keys():
            h = all_balls[name]
            if h == cue_h:
                continue
            p = sim.getObjectPosition(h, -1)
            d = math.hypot(p[0] - pc[0], p[1] - pc[1])
            if d < mind:
                mind = d
                tgt_h = h
        if tgt_h is None:
            raise RuntimeError("Tidak ada target lain.")

    pt = sim.getObjectPosition(tgt_h, -1)
    dirX, dirY, _ = norm2d(pt[0] - pc[0], pt[1] - pc[1])
    alias_full = sim.getObjectAlias(tgt_h, 1)
    desc = f"target {alias_full} dir=({dirX:.4f},{dirY:.4f})"
    return (dirX, dirY, 0.0), desc


def fire_once(sim, client, cue_h, hit_mode, dir_unit, v_target, mCue, dt, offset_vec_local=None):
    """
    Impuls 1-step:
      - central: gaya di COM (tanpa torsi)
      - offset : gaya pada pos relatif lokal offset_vec_local (m) → timbul torsi (spin)
    """
    J = mCue * v_target
    Fmag = J / dt
    Fvec = [Fmag * dir_unit[0], Fmag * dir_unit[1], 0.0]

    client.setStepping(True)
    if hit_mode == "central" or offset_vec_local is None:
        sim.addForceAndTorque(cue_h, Fvec, [0, 0, 0])
    else:
        sim.addForce(cue_h, [offset_vec_local[0], offset_vec_local[1], offset_vec_local[2]], Fvec)
    client.step()
    client.setStepping(False)
    return J, Fmag


def apply_force_torque_steps(sim, client, handle, F_vec, T_vec, n_steps, offset_vec_local=None):
    """
    Terapkan gaya/torsi manual selama n_steps.
    - Jika offset_vec_local None: gaya di COM via addForceAndTorque(F,T)
    - Jika offset_vec_local ada: gaya via addForce(offset), torsi via addForceAndTorque(0,T)
    """
    if n_steps <= 0:
        return

    client.setStepping(True)
    i = 0
    while i < int(n_steps):
        if offset_vec_local is None:
            sim.addForceAndTorque(handle, F_vec, T_vec)
        else:
            sim.addForce(handle, [offset_vec_local[0], offset_vec_local[1], offset_vec_local[2]], F_vec)
            if abs(T_vec[0]) > 0.0 or abs(T_vec[1]) > 0.0 or abs(T_vec[2]) > 0.0:
                sim.addForceAndTorque(handle, [0.0, 0.0, 0.0], T_vec)
        client.step()
        i += 1
    client.setStepping(False)


def free_run(sim, client, duration_s, sample_dt=0.5, sample_handle=None):
    client.setStepping(False)
    t0 = time.time()
    while time.time() - t0 < duration_s:
        time.sleep(sample_dt)
        if sample_handle is not None:
            v_lin, v_ang = sim.getObjectVelocity(sample_handle)
            speed = vlen3(v_lin)
            omega_str = (round(v_ang[0], 3), round(v_ang[1], 3), round(v_ang[2], 3))
            print(f"[FREE-RUN] |v|={speed:.3f} m/s | omega={omega_str}")


def print_positions(sim, name2h):
    print("[POSITIONS]")
    for name in name2h.keys():
        h = name2h[name]
        p = sim.getObjectPosition(h, -1)
        print(f"  {name:>12s} -> ({p[0]:+.3f}, {p[1]:+.3f}, {p[2]:+.3f})")
# -------------------------------------------------------


# ----------------- 1 GILIRAN (dialog) ------------------
def interactive_turn(sim, client, cue, all_balls, dt, massCue, radiusCue):
    print("\n=== GILIRAN BARU ===")
    aim_mode = ask_choice("Mode bidik", ["manual", "target"], "manual")

    if aim_mode == "manual":
        # Force + Torque; opsional offset posisi gaya
        Fx = ask_float("Gaya Fx (N)", 5.0)
        Fy = ask_float("Gaya Fy (N)", 0.0)
        Fz = ask_float("Gaya Fz (N)", 0.0)
        Tx = ask_float("Torsi Tx (N·m)", 0.0)
        Ty = ask_float("Torsi Ty (N·m)", 0.0)
        Tz = ask_float("Torsi Tz (N·m)", 0.0)

        use_offset = ask_choice("Pakai offset posisi gaya relatif ke COM?", ["y", "n"], "y")
        offset_vec = None
        if use_offset == "y":
            print("Offset dalam KERANGKA LOKAL bola (meter).")
            print("Tips: rz negatif (mis. -0.005) = pukul sedikit ke bawah (backspin).")
            rx = ask_float("Offset rx (m)", 0.0)
            ry = ask_float("Offset ry (m)", 0.0)
            rz = ask_float("Offset rz (m)", -0.005)

            rx_c, ry_c, rz_c, clamped = clamp_offset_to_radius(rx, ry, rz, radiusCue, safety=OFFSET_SAFETY)
            if clamped:
                print(f"[CLAMP] Offset melebihi radius. Di-skala ke ({rx_c:.4f}, {ry_c:.4f}, {rz_c:.4f}) m")
            offset_vec = (rx_c, ry_c, rz_c)

        nsteps   = int(ask_float("Pulse length (jumlah step)", 1))
        free_dur = ask_float("Durasi free-run (detik)", 4.0)

        F_vec = [Fx, Fy, Fz]
        T_vec = [Tx, Ty, Tz]
        print(f"[MANUAL F/T] F=({Fx:.3f}, {Fy:.3f}, {Fz:.3f}) N | "
              f"T=({Tx:.3f}, {Ty:.3f}, {Tz:.3f}) N·m | steps={nsteps}")
        if offset_vec is not None:
            print(f"[OFFSET] r_local=({offset_vec[0]:.4f}, {offset_vec[1]:.4f}, {offset_vec[2]:.4f}) m (clamped<= {OFFSET_SAFETY:.2f}*R)")

        apply_force_torque_steps(sim, client, cue, F_vec, T_vec, nsteps, offset_vec_local=offset_vec)
        v_lin, v_ang = sim.getObjectVelocity(cue)
        speed = vlen3(v_lin)
        omega_str = (round(v_ang[0], 3), round(v_ang[1], 3), round(v_ang[2], 3))
        print(f"[AFTER PULSE] |v|={speed:.3f} m/s | omega={omega_str}")

        free_run(sim, client, free_dur, 0.5, cue)

    else:
        # Target mode → arah cue→target otomatis, lalu impuls 1-step
        method = ask_choice("Target method", ["by_name", "nearest"], "nearest")
        tname = None
        if method == "by_name":
            print("Bola tersedia:")
            for nm in all_balls.keys():
                print("  -", nm)
            tname_input = input("Nama target [/Sphere[0]]: ").strip()
            if tname_input == "":
                tname = "/Sphere[0]"
            else:
                tname = tname_input

        dir_unit, desc = aim_direction(sim, cue, all_balls, method, tname)
        speed    = ask_float("Kecepatan target (m/s)", 2.0)
        hit_mode = ask_choice("Jenis pukulan", ["central", "offset"], "central")

        offset_vec = None
        if hit_mode == "offset":
            print("Masukkan offset gaya relatif ke COM (KERANGKA LOKAL), meter.")
            rx = ask_float("Offset rx (m)", 0.0)
            ry = ask_float("Offset ry (m)", 0.0)
            rz = ask_float("Offset rz (m)", -0.005)
            rx_c, ry_c, rz_c, clamped = clamp_offset_to_radius(rx, ry, rz, radiusCue, safety=OFFSET_SAFETY)
            if clamped:
                print(f"[CLAMP] Offset melebihi radius. Di-skala ke ({rx_c:.4f}, {ry_c:.4f}, {rz_c:.4f}) m")
            offset_vec = (rx_c, ry_c, rz_c)

        free_dur = ask_float("Durasi free-run (detik)", 4.0)

        print(f"[AIM] {desc}")
        J, Fmag = fire_once(sim, client, cue, hit_mode, dir_unit, speed, massCue, dt=dt, offset_vec_local=offset_vec)
        print(f"[IMPULSE] v_target={speed:.2f} | J={J:.4f} N·s | F_once={Fmag:.2f} N")
        if offset_vec is not None:
            print(f"[OFFSET] r_local=({offset_vec[0]:.4f}, {offset_vec[1]:.4f}, {offset_vec[2]:.4f}) m (clamped<= {OFFSET_SAFETY:.2f}*R)")

        free_run(sim, client, free_dur, 0.5, cue)

    # Akhiri giliran: hentikan semua bola & tampilkan posisi
    handles = []
    for h in all_balls.values():
        handles.append(h)
    stop_all_balls(sim, handles, client)
    print_positions(sim, all_balls)

    lanjut = ask_choice("Lanjut giliran berikutnya?", ["y", "n"], "y")
    return lanjut == "y"
# -------------------------------------------------------


# --------------------- MAIN ---------------------------
def main():
    client = RemoteAPIClient()  
    sim = client.getObject('sim')

    sim.startSimulation()
    client.setStepping(False)

    try:
        balls = discover_balls(sim, BALL_NAMES)
        cue   = balls[CUE_BALL]

        dt = sim.getSimulationTimeStep()
        m  = get_mass(sim, cue)
        d, r = get_diameter_radius(sim, cue)

        reset_body(sim, cue, client)

        print(f"[INIT] dt={dt:.4f}s | mass(cue)={m:.3f} kg | diam(cue)={d:.3f} m (R={r:.3f} m, clamp≤{OFFSET_SAFETY:.2f}*R)")
        print_positions(sim, balls)

        while True:
            keep = interactive_turn(sim, client, cue, balls, dt, m, r)
            if not keep:
                break

        print("\n[END] Permainan selesai.")

    finally:
        try:
            handles = []
            discovered = discover_balls(sim, BALL_NAMES)
            for h in discovered.values():
                handles.append(h)
            stop_all_balls(sim, handles, client)
        except Exception:
            pass

        try:
            sim.stopSimulation()
        except Exception:
            pass


if __name__ == "__main__":
    main()
