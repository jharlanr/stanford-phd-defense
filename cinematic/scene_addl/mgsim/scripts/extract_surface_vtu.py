"""Extract the top-surface fields from an Elmer/Ice cauchy .vtu and
resample them onto the PUBLISHED analysis lattice (591x591 @ 25 m,
coords centered on the domain, +/-7375 m) so the MGSIM ensemble runs
can be differenced against cinematic/source_data/pnas_sims/*.nc.

Runs on the VM with stdlib + numpy + scipy only (no vtk/meshio/pyvista):
the .vtu is a VTK XML UnstructuredGrid with raw appended binary, so the
DataArray offsets in the header are enough to np.fromfile each array.

  python3 extract_surface_vtu.py <in.vtu> <out.npz>
"""
import re
import sys
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay

GRID_HALF_M = 7375.0     # published analysis tile: 14.75 km across
GRID_RES_M = 25.0

# Elmer writes the symmetric Cauchy tensor in this Voigt order.
STRESS_KEYS = ('sigma_xx', 'sigma_yy', 'sigma_zz',
               'sigma_xy', 'sigma_yz', 'sigma_xz')


def parse_header(path):
    """Return (arrays, data_start, header_dtype). `arrays` maps name ->
    (dtype, ncomp, offset); offsets are relative to the appended blob."""
    with open(path, 'rb') as fh:
        head = fh.read(1 << 20)
    marker = head.find(b'<AppendedData')
    if marker < 0:
        raise SystemExit('no <AppendedData> — not a raw-appended .vtu')
    enc = re.search(rb'<AppendedData\s+encoding="([^"]+)"', head[marker:]).group(1)
    if enc != b'raw':
        raise SystemExit(f'appended encoding {enc!r} unsupported (expected raw)')
    data_start = head.index(b'_', marker) + 1

    xml = head[:marker].decode('utf-8', 'replace')
    hdr_t = re.search(r'header_type="(\w+)"', xml)
    header_dtype = np.dtype({'UInt32': '<u4', 'UInt64': '<u8'}[
        hdr_t.group(1) if hdr_t else 'UInt32'])
    if re.search(r'byte_order="BigEndian"', xml):
        raise SystemExit('BigEndian .vtu unsupported')

    npoints = int(re.search(r'NumberOfPoints="(\d+)"', xml).group(1))

    typemap = {'Float64': '<f8', 'Float32': '<f4',
               'Int32': '<i4', 'Int64': '<i8', 'UInt8': '<u1'}
    arrays = {}
    for tag in re.findall(r'<DataArray[^>]*/>', xml):
        typ = re.search(r'type="(\w+)"', tag)
        off = re.search(r'offset="(\d+)"', tag)
        if not (typ and off):
            continue
        nm = re.search(r'Name="([^"]*)"', tag)
        ncomp = re.search(r'NumberOfComponents="(\d+)"', tag)
        name = nm.group(1) if nm else '__points__'
        # <Points> has no Name; it is the only unnamed Float64 x3 array.
        arrays[name] = (np.dtype(typemap[typ.group(1)]),
                        int(ncomp.group(1)) if ncomp else 1,
                        int(off.group(1)))
    return arrays, data_start, header_dtype, npoints


def read_array(path, arrays, data_start, header_dtype, npoints, name):
    dt, ncomp, off = arrays[name]
    # Each appended block is [header_dtype byte-count][payload].
    start = data_start + off + header_dtype.itemsize
    a = np.fromfile(path, dtype=dt, count=npoints * ncomp, offset=start)
    return a.reshape(npoints, ncomp) if ncomp > 1 else a


def top_surface_index(x, y, z):
    """The mesh is a vertical extrusion, so each (x, y) column holds one
    node per level. Return the index of the highest node in each column."""
    xi = np.round(x * 1e3).astype(np.int64)
    yi = np.round(y * 1e3).astype(np.int64)
    order = np.lexsort((z, yi, xi))
    xs, ys = xi[order], yi[order]
    # last row of each (xi, yi) run == largest z in that column
    last = np.empty(xs.size, bool)
    last[-1] = True
    last[:-1] = (xs[:-1] != xs[1:]) | (ys[:-1] != ys[1:])
    return order[last]


def main(src, dst):
    arrays, data_start, hdt, npoints = parse_header(src)
    pts_key = '__points__' if '__points__' in arrays else 'Points'
    pts = read_array(src, arrays, data_start, hdt, npoints, pts_key)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]

    top = top_surface_index(x, y, z)
    print(f'  {npoints} nodes -> {top.size} surface nodes', flush=True)

    # Centre exactly like the published nc ("coords centered to (0,0)").
    cx = 0.5 * (x.min() + x.max())
    cy = 0.5 * (y.min() + y.max())
    sx, sy = x[top] - cx, y[top] - cy

    fields = {}
    for i, key in enumerate(STRESS_KEYS, start=1):
        fields[key] = read_array(src, arrays, data_start, hdt, npoints,
                                 f'stress {i}')[top]
    vel = read_array(src, arrays, data_start, hdt, npoints, 'velocity')[top]
    fields['velo_x'], fields['velo_y'], fields['velo_z'] = vel.T
    fields['speed_h'] = np.hypot(vel[:, 0], vel[:, 1])
    fields['topo_surf'] = z[top]
    fields['topo_bed'] = read_array(src, arrays, data_start, hdt, npoints,
                                    'beddem')[top]

    n = int(round(2 * GRID_HALF_M / GRID_RES_M)) + 1
    gx = np.linspace(-GRID_HALF_M, GRID_HALF_M, n)
    gy = np.linspace(-GRID_HALF_M, GRID_HALF_M, n)
    GX, GY = np.meshgrid(gx, gy)              # row = y, col = x (as in the nc)

    # One triangulation of the surface nodes, reused for every field.
    tri = Delaunay(np.column_stack([sx, sy]))
    out = {'x': gx.astype('f4'), 'y': gy.astype('f4')}
    for key, val in fields.items():
        out[key] = LinearNDInterpolator(tri, val.astype(np.float64))(GX, GY).astype('f4')
        print(f'  {key:10s} {np.nanmin(out[key]):+.4g} .. {np.nanmax(out[key]):+.4g}',
              flush=True)

    np.savez_compressed(dst, **out)
    print(f'  wrote {dst}', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
