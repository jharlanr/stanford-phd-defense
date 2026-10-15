// slabnewt_patch_donuts.geo — core → donut1 → donut2 → coarse

// core → donut1 → donut2 → coarse, compatible with Gmsh 4.4.1

Mesh.Algorithm = 5; // Delaunay

// ---- Mesh sizes ----
lc    = 200.0;   // coarse/global size (outermost)
lcc1  = 80.0;   // inner core size
lcc2  = 40.0;    // donut-1 size (fine ring)
lcc3  = 80.0;   // donut-2 size (blend ring)

// ---- Domain ----
L = 24750.0; //
Point(1) = {0,  0,  0, lc};
Point(2) = {L,  0,  0, lc};
Point(3) = {L,  L,  0, lc};
Point(4) = {0,  L,  0, lc};
Line(1) = {1,2};
Line(2) = {2,3};
Line(3) = {3,4};
Line(4) = {4,1};
Line Loop(10) = {1,2,3,4};
Plane Surface(20) = {10};

// ---- Physical tags ----
Physical Line(1) = {1}; // bottom
Physical Line(2) = {2}; // right
Physical Line(3) = {3}; // top
Physical Line(4) = {4}; // left
Physical Surface(5) = {20}; // single body

// ---- Core + Donut parameters ----
xc = L/2; yc = L/2;
r_core = 1500.0;
annulus1_thickness = 2000.0; // R1..R2 (donut-1)
annulus2_thickness = 2000.0; // R2..R3 (donut-2)

R1 = r_core;
R2 = r_core + annulus1_thickness;
R3 = r_core + annulus1_thickness + annulus2_thickness;

// ===============================
// Core: r <= R1 → lcc1 ; else lc
Field[1] = Ball;
Field[1].XCenter = xc; Field[1].YCenter = yc; Field[1].ZCenter = 0;
Field[1].Radius  = R1;
Field[1].VIn  = lcc1;
Field[1].VOut = lc;

// ===============================
// Donut-1 (R1..R2) → lcc2, else lc
Field[2] = Ball; // outer bound (<= R2 -> lcc2)
Field[2].XCenter = xc; Field[2].YCenter = yc; Field[2].ZCenter = 0;
Field[2].Radius  = R2;
Field[2].VIn  = lcc2;
Field[2].VOut = lc;

Field[3] = Ball; // inner bound (<= R1 -> lc, > R1 -> lcc2)
Field[3].XCenter = xc; Field[3].YCenter = yc; Field[3].ZCenter = 0;
Field[3].Radius  = R1;
Field[3].VIn  = lc;
Field[3].VOut = lcc2;

Field[4] = Max;                // lcc2 in R1..R2, lc elsewhere
Field[4].FieldsList = {2, 3};

// ===============================
// Donut-2 (R2..R3) → lcc3, else lc
Field[6] = Ball; // outer bound (<= R3 -> lcc3)
Field[6].XCenter = xc; Field[6].YCenter = yc; Field[6].ZCenter = 0;
Field[6].Radius  = R3;
Field[6].VIn  = lcc3;
Field[6].VOut = lc;

Field[7] = Ball; // inner bound (<= R2 -> lc, > R2 -> lcc3)
Field[7].XCenter = xc; Field[7].YCenter = yc; Field[7].ZCenter = 0;
Field[7].Radius  = R2;
Field[7].VIn  = lc;
Field[7].VOut = lcc3;

Field[8] = Max;                // lcc3 in R2..R3, lc elsewhere
Field[8].FieldsList = {6, 7};

// ===============================
// Final combo: min(core, donut-1, donut-2)
Field[9] = Min;
Field[9].FieldsList = {1, 4, 8};

Background Field = 9;

// ---- Bounds (4.4.1-safe; avoid Min(a,b,c)) ----
Mesh.CharacteristicLengthMin = lcc2; // pick the smallest explicitly
Mesh.CharacteristicLengthMax = lc;
Mesh.CharacteristicLengthExtendFromBoundary = 0;
