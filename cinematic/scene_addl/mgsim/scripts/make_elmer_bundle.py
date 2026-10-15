"""Build a self-contained, portable Elmer/Ice bundle for the MGSIM bed ensemble.

Takes the PUBLISHED viscous sif for lake 2019cw428 verbatim and makes exactly
four kinds of edit, one bundle per realization:

  1. bedDEM_path  -> the MGSIM realization (literal lowercase filename)
  2. ZsDEM_path   -> literal lowercase filename  (the published sif builds
                     "_D25km_H1004_" with capitals while the files on disk are
                     lowercase; harmless on macOS, fatal on the Linux VM)
  3. the speedDEM Variable 3 block and its Exported Variable are deleted
                     (diagnostics only; the *_speed_*.dat was never archived)
  4. out_path / vtu_path get the realization tag so the 10 runs don't collide
  5. the UDF path is rebased from ../../PROG to the bundle's own PROG/

Physics, mesh, BCs, Csi, temperature profile, solver settings: untouched.
"""
import hashlib, re, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / 'data/source_copies'
DEMS = HERE / 'data/derived/dems'
OUT = HERE / 'elmer_bundle'
LAKE, N_REAL = '2019cw428', 10
STEM = f'{LAKE}_bed_d25km_h1004_a0.792'
SURF = f'{LAKE}_surface_d25km_h1004_a0.792.dat'

base = (SRC / f'{LAKE}_glen_d25km_r2500m_tsic_base.sif').read_text()

# ---- the exact blocks we replace, asserted so a source change cannot pass silently
OLD_PATHS = '''$ bedDEM_path = "../dems/2019cw" lakenum_cw_str "_bed_D" domain_km_str "km_H" Hp_str "_a" alphadeg_str ".dat"
$ ZsDEM_path  = "../dems/2019cw" lakenum_cw_str "_surface_D" domain_km_str "km_H" Hp_str "_a" alphadeg_str ".dat"
$ spdDEM_path = "../dems/2019cw" lakenum_cw_str "_speed_D" domain_km_str "km_H" Hp_str "_a" alphadeg_str ".dat"
$ out_path = "2019cw" lakenum_cw_str "_d" domain_km_str "km_r2500m_Csi" Csi_str "_Tsic_" patch_nopatch_str "_cauchy.result"
$ vtu_path = "2019cw" lakenum_cw_str "_d" domain_km_str "km_r2500m_Csi" Csi_str "_Tsic_" patch_nopatch_str "_cauchy.vtu"'''

OLD_SPEED_BLOCK = '''
  ! Speed
  Variable 3 = String "speedDEM"
  Variable 3 data file = File $spdDEM_path
  Variable 3 x0 = Real 0.0
  Variable 3 y0 = Real 0.0
  Variable 3 lx = Real 24750.0
  Variable 3 ly = Real 24750.0
  Variable 3 Nx = Integer 166
  Variable 3 Ny = Integer 166
  Variable 3 Invert = Logical False
  Variable 3 Fill = Logical False
  Variable 3 Position Tol = Real 1.0e-1
'''
OLD_EXPORTED = '  Exported Variable 5 = -dofs 1 "speedDEM"\n'

for name, blk in [('paths', OLD_PATHS), ('speed block', OLD_SPEED_BLOCK), ('exported', OLD_EXPORTED)]:
    assert blk in base, f'published sif no longer contains the expected {name}'
assert base.count('"../../PROG/USF_TAVz"') == 4, 'expected 4 UDF references'


OLD_PATCH_STR = re.search(r'\$ patch_nopatch_str = \s*"patch"', base).group(0)
OLD_WEERTMAN = ('    Real MATC "(1 - (((tx[0] - xc)^2 + (tx[1] - yc)^2) < R^2)) * C_out"')
OLD_OUTPUT = '  Output File = File $out_path\n'
for nm, blk in [('patch_nopatch_str', OLD_PATCH_STR), ('weertman', OLD_WEERTMAN),
                ('output file', OLD_OUTPUT)]:
    assert blk in base, f'published sif no longer contains the expected {nm}'


def make_sif(i, cfg):
    """cfg is 'patch' (published) or 'nopatch' (C_out everywhere, no slippery
    patch) so the pair gives delta-sigma1 per realization."""
    tag = f'mgsim{i:02d}'
    new_paths = (
        f'$ real_str    = "{tag}"\n'
        f'$ bedDEM_path = "dems/{STEM}_{tag}.dat"\n'
        f'$ ZsDEM_path  = "dems/{SURF}"\n'
        f'$ out_path = "2019cw" lakenum_cw_str "_d" domain_km_str "km_r2500m_Csi" Csi_str '
        f'"_Tsic_" patch_nopatch_str "_" real_str "_cauchy.result"\n'
        f'$ vtu_path = "2019cw" lakenum_cw_str "_d" domain_km_str "km_r2500m_Csi" Csi_str '
        f'"_Tsic_" patch_nopatch_str "_" real_str "_cauchy.vtu"'
    )
    s = base.replace(OLD_PATHS, new_paths)
    s = s.replace(OLD_SPEED_BLOCK, '\n')
    s = s.replace(OLD_EXPORTED, '')
    s = s.replace('"../../PROG/USF_TAVz"', '"PROG/USF_TAVz"')
    # do not write the ~466 MB .result restart file; sigma1 comes from the .vtu
    s = s.replace(OLD_OUTPUT, '')
    if cfg == 'nopatch':
        s = s.replace(OLD_PATCH_STR, '$ patch_nopatch_str = \t"nopatch"')
        s = s.replace(OLD_WEERTMAN, '    Real MATC "C_out"')
        assert 'R^2' not in s
    assert 'spdDEM' not in s and 'speedDEM' not in s and 'Output File' not in s
    return tag, s


# elmer_bundle/results/ holds fields pulled back off the VM — it is not
# generated here, so never let a rebuild of the bundle wipe it.
if OUT.exists():
    for child in OUT.iterdir():
        if child.name == 'results':
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
(OUT / 'sifs').mkdir(parents=True)
(OUT / 'dems').mkdir()
(OUT / 'PROG').mkdir()

missing = [i for i in range(N_REAL) if not (DEMS / f'{STEM}_mgsim{i:02d}.dat').exists()]
assert not missing, f'missing realization DEMs {missing} — re-run notebook 03'

for cfg in ('patch', 'nopatch'):
    for i in range(N_REAL):
        tag, txt = make_sif(i, cfg)
        (OUT / 'sifs' / f'{LAKE}_glen_d25km_r2500m_tsic_{cfg}_{tag}.sif').write_text(txt)
for i in range(N_REAL):
    shutil.copy2(DEMS / f'{STEM}_mgsim{i:02d}.dat', OUT / 'dems')
shutil.copy2(SRC / SURF, OUT / 'dems')
shutil.copy2(SRC / f'{LAKE}_d25km_r2500m.geo', OUT)
for f in ('run_ensemble.sh', 'README.md'):          # static bundle files, kept
    shutil.copy2(HERE / 'scripts/bundle_files' / f, OUT)   # outside the rebuilt tree
(OUT / 'run_ensemble.sh').chmod(0o755)
for f in ('USF_TAVz', 'USF_TAVz.F90'):
    shutil.copy2(SRC / 'PROG' / f, OUT / 'PROG')

# manifest with checksums so a partial transfer to the VM is detectable
lines = []
# results/ is pulled back FROM the VM; the manifest records only what ships TO it.
shipped = [p for p in sorted(OUT.rglob('*')) if 'results' not in p.relative_to(OUT).parts]
for p in shipped:
    if p.is_file():
        lines.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()[:16]}  '
                     f'{p.stat().st_size:>10}  {p.relative_to(OUT)}')
(OUT / 'MANIFEST.txt').write_text('\n'.join(lines) + '\n')
print(f'bundle at {OUT}')
print(f'  {2 * N_REAL} sifs (patch + nopatch), {N_REAL + 1} DEMs, geo, UDF (+source), manifest')
print(f'  total {sum(p.stat().st_size for p in shipped if p.is_file()) / 1e6:.1f} MB')
