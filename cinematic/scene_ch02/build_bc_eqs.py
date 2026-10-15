"""Bake the Ch.2 boundary-condition equation chips.

The ask: clicking "boundary conditions" over the simulation-domain block
paints the BCs on the object AND floats equation chips coupled to each
interface (inflow/outflow walls, flow-parallel walls, bed outside +
inside the patch/blister, free surface), for BOTH the viscous and the
elastic model.

Every equation below is cross-validated against the run sifs and the
PNAS SI Appendix section 4 (a line-by-line reconciliation):

VISCOUS (full Stokes, Glen n=3, per-lake tuned c_b; sif BCs 1-6):
  surface   sigma.n = 0                          (natural BC, SI eq 40)
  bed r>R   u.n_b = 0 ; tau_b = -c_b|u_b|^{m-1}u_b   (m = 1/3, SI 41-42)
  bed r<=R  tau_b = 0  (free-slip patch, SI eq 43)
  x walls   u_x = u_SIA(z') Dirichlet (SI eq 44; transverse/vertical free)
  y walls   u.y = 0 (free slip)

ELASTIC (E = 3.077 GPa, nu = 0.3, u_b = 0; template BCs 1-6):
  surface   sigma.n = 0                                    (SI eq 48)
  bed r>R   u = 0                                          (SI eq 50)
  bed r<=R  sigma.n_b = -P_w rho_i g H n_b  (blister, SI eq 51)
  x walls   u_x = u_b + 2(1+nu) rho g sin(alpha)/E (Hz'-z'^2/2)  (SI 49)
  y walls   u.y = 0

Outputs: cinematic/data/ch02_bc/*.svg → R2 ch02/bc/*.svg
Run:  cinematic/.venv/bin/python -u cinematic/scene_ch02/build_bc_eqs.py
Then: rclone copy cinematic/data/ch02_bc r2:<bucket>/ch02/bc --header-upload 'Cache-Control: public, max-age=31536000, immutable'
      (cd website && rclone sync r2:<bucket> .r2-cache)
"""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "ch02_bc"
OUT.mkdir(parents=True, exist_ok=True)

EQS = {
    # shared
    "bc_surface": r"$\boldsymbol{\sigma}\cdot\mathbf{n} = \mathbf{0}$",
    "bc_lateral": r"$\mathbf{u}\cdot\hat{\mathbf{y}} = 0$",
    # viscous
    "bc_v_wall":
        r"$u_x = u_{\mathrm{SIA}}(z')$",
    "bc_v_wall_full":
        r"$u_{\mathrm{SIA}}(z') = \frac{2A(T)}{n+1}\,(\rho_i g \sin\alpha)^{n}"
        r"\left[H^{\,n+1} - (H-z')^{\,n+1}\right]"
        r" + \left(\frac{\rho_i g H \sin\alpha}{c_b}\right)^{1/m}$",
    "bc_v_bed":
        r"$\mathbf{u}\cdot\mathbf{n}_b = 0\,,\quad"
        r" \boldsymbol{\tau}_b = -c_b\,|\mathbf{u}_b|^{m-1}\,\mathbf{u}_b$",
    "bc_v_patch":
        r"$\boldsymbol{\tau}_b = \mathbf{0}\quad (r \leq R)$",
    # elastic
    "bc_e_wall":
        r"$u_x = u_b + \frac{2(1+\nu)\,\rho_i g \sin\alpha}{E}"
        r"\left(H z' - \frac{z'^2}{2}\right)$",
    "bc_e_bed":
        r"$\mathbf{u} = \mathbf{0}$",
    "bc_e_patch":
        r"$\boldsymbol{\sigma}\cdot\mathbf{n}_b = -P_w\,\rho_i g H\,\mathbf{n}_b"
        r"\quad (r \leq R)$",
}


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"text.usetex": False, "mathtext.fontset": "cm"})
    for name, tex in EQS.items():
        fig = plt.figure()
        t = fig.text(0, 0, tex, fontsize=24, color="#f5f0e6")
        fig.canvas.draw()
        bb = t.get_window_extent()
        fig.set_size_inches(bb.width / fig.dpi + 0.1, bb.height / fig.dpi + 0.1)
        out_svg = OUT / f"{name}.svg"
        fig.savefig(out_svg, transparent=True, bbox_inches="tight", pad_inches=0.04)
        plt.close(fig)
        print(f"wrote {out_svg.name}")
    print("\nupload:\n  rclone copy cinematic/data/ch02_bc r2:<bucket>/ch02/bc --header-upload 'Cache-Control: public, max-age=31536000, immutable'")


if __name__ == "__main__":
    main()
