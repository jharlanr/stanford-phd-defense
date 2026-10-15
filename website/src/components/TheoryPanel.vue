<template>
  <div
    class="tp-root"
    :style="{
      opacity: hidden ? 0 : 1,
      transitionDuration: hidden ? '0.5s' : '0.9s',
    }"
  >
    <!-- Chalkboard backdrop — its OWN layer so the beat 3→4 seam entry
         can hold it transparent (the globe's flattened slab stays
         visible beneath the arriving field image — the director's rule: no
         fade to black, ever) and then dim the surroundings AFTER the
         field has landed. -->
    <div class="tp-backdrop" :style="{ opacity: tw.bgA }" />
    <!-- ══════════ The plot stage — FULL SCREEN (the director's request).
         Equations live IN the figure (SVG <image> at plot coordinates),
         not in a side column. On the log-log stage the plot squeezes
         left (tw.plotW) to make room for the two cards beside it. ══ -->
    <div class="tp-stage">
      <svg
        ref="svgRef"
        class="tp-svg"
        :viewBox="`0 0 ${VW} ${VH}`"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <!-- RdBu_r, bottom = −vmax, top = +vmax (vertical colorbar) -->
          <linearGradient id="tp-rdbu" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%"   stop-color="#053061" />
            <stop offset="20%"  stop-color="#2166ac" />
            <stop offset="35%"  stop-color="#92c5de" />
            <stop offset="50%"  stop-color="#f7f7f7" />
            <stop offset="65%"  stop-color="#f4a582" />
            <stop offset="80%"  stop-color="#b2182b" />
            <stop offset="100%" stop-color="#67001f" />
          </linearGradient>
          <!-- Clip to the LIVE plot width (tw.plotW) — on the squeezed
               log-log stage the nondim ensemble tails (x̂ beyond ±6)
               otherwise stick out past the figure box. -->
          <clipPath id="tp-curveclip">
            <rect :x="FX" :y="curveTop" :width="tw.plotW" :height="Math.max(1, curveBottom - curveTop)" />
          </clipPath>
          <!-- the plot split at the patch edges (the derivation's fades) -->
          <clipPath id="tp-clip-patch">
            <rect :x="xDim(-patchHalfKm)" :y="curveTop" :width="Math.max(0, xDim(patchHalfKm) - xDim(-patchHalfKm))" :height="Math.max(1, curveBottom - curveTop)" />
          </clipPath>
          <clipPath id="tp-clip-outer">
            <rect :x="FX" :y="curveTop" :width="Math.max(0, xDim(-patchHalfKm) - FX)" :height="Math.max(1, curveBottom - curveTop)" />
            <rect :x="xDim(patchHalfKm)" :y="curveTop" :width="Math.max(0, FX + tw.plotW - xDim(patchHalfKm))" :height="Math.max(1, curveBottom - curveTop)" />
          </clipPath>
          <!-- Wipe clip: the field survives only ABOVE the sweep line —
               the line consumes it from the bed up. -->
          <clipPath id="tp-wipeclip">
            <rect :x="FX - 4" :y="FY - 4" :width="tw.plotW + 8" :height="Math.max(0, sweepLineY - FY) + 4" />
          </clipPath>
          <!-- Stage-8 map colorbars (horizontal), the exact matplotlib
               stops the fig2 PNGs were drawn with (twins_map_fig2.json). -->
          <linearGradient v-for="m in MAPS2" :id="`tp-cmap-${m.key}`" :key="`cm${m.key}`"
                          x1="0" y1="0" x2="1" y2="0">
            <stop v-for="(c, k) in m.stops" :key="k"
                  :offset="`${(k / (m.stops.length - 1)) * 100}%`" :stop-color="c" />
          </linearGradient>
          <!-- The solution CARDS (the director's request): the takeaway card's
               look — a dark gradient plate, a gold edge, a deep shadow. -->
          <linearGradient id="tp-card-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#1e180c" stop-opacity="0.985" />
            <stop offset="100%" stop-color="#0a0805" stop-opacity="0.985" />
          </linearGradient>
          <filter id="tp-card-shadow" x="-20%" y="-40%" width="140%" height="180%">
            <feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#000000" flood-opacity="0.8" result="s1" />
            <feDropShadow in="s1" dx="0" dy="0" stdDeviation="14" flood-color="#f4cf6a" flood-opacity="0.16" />
          </filter>
          <marker id="tp-arrow" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#f5c75e" />
          </marker>
          <marker id="tp-arrow-dark" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#7a4a10" />
          </marker>
        </defs>

        <!-- ══════════ THE RESERVED EQUATION AREA (the director asked for
             one): centered above the domain / plot. The Stokes
             system (eq 1) on the field stage; the SSA (eq 7) replaces it
             IN PLACE after the wipe (same baseline, one crossfade) and
             never leaves through the derivation. eq (7) is three
             registered pieces so its basal-drag term can drop out and the
             line close up (tw.dragA, tw.cGap). ══════════ -->
        <image v-if="tw.stokesA > 0.004" :style="{ opacity: tw.stokesA }"
               v-bind="eqAt('stokes', K_GOV, EQ_CX, GOV_BASE_Y, 'center', 'baseline')" />
        <g v-if="tw.govA > 0.004" :style="{ opacity: tw.govA }">
          <image v-bind="eqAt('ssa', K_GOV, SSA_X0 + ssaShiftMem, GOV_BASE_Y, 'left', 'baseline', 'ssa_mem')" />
          <image v-if="tw.dragA > 0.004" :style="{ opacity: tw.dragA }"
                 v-bind="eqAt('ssa', K_GOV, SSA_X0 + ssaShiftMem, GOV_BASE_Y, 'left', 'baseline', 'ssa_drag')" />
          <image v-bind="eqAt('ssa', K_GOV, SSA_X0 + ssaShiftGrav, GOV_BASE_Y, 'left', 'baseline', 'ssa_grav')" />
          <!-- under-brace term anatomy: extents are TeX-measured, so the
               braces ride their terms as the gap opens and closes -->
          <g v-if="tw.braceA > 0.004">
            <g v-for="b in ssaBraces" :key="b.key" :style="{ opacity: b.a }">
              <path :d="bracePath(b.x0, b.x1, b.y)"
                    fill="none" stroke="rgba(245,199,94,0.75)" stroke-width="3" />
              <text :x="(b.x0 + b.x1) / 2" :y="b.y + 64" text-anchor="middle" class="tp-ssa-label">
                {{ b.label }}
              </text>
            </g>
          </g>
        </g>
        <!-- Row B: the stress–velocity relation alone, centred under the
             governing equation (the director dropped the velocity solution
             equation from the talk and asked for the τxx–u relationship
             centred under the governing equation — the velocity
             SOLUTION is the u' profile on the plot; its equation lives in
             the deeper dive's derivation). -->
        <image v-if="tw.tauUA > 0.004" :style="{ opacity: tw.tauUA }"
               v-bind="eqAt('tau_u', K_EQ, EQ_CX, ROWB_BASE_Y, 'center', 'baseline')" />

        <!-- ══════════ FIELD (field + average stages) ══════════ -->
        <g v-if="tw.fieldA > 0.004 && sweepLineY > FY + 1"
           :style="{ opacity: tw.fieldA }"
           :transform="`translate(0 ${tw.fieldShift.toFixed(1)})`">
          <g clip-path="url(#tp-wipeclip)">
            <image
              :href="fieldUrl"
              :x="FX" :y="FY" :width="tw.plotW" :height="FH"
              preserveAspectRatio="none"
            />
            <rect :x="FX" :y="FY" :width="tw.plotW" :height="FH"
                  fill="none" stroke="rgba(245,245,245,0.6)" stroke-width="2" />
          </g>

          <!-- Field axis (left: height above bed; colorbar right). -->
          <g class="tp-axis" v-if="tw.wipeT < 0.98">
            <!-- Bed tick only while the bed still exists (pre-wipe). -->
            <template v-if="tw.wipeT < 0.02">
              <line :x1="FX - 8" :x2="FX" :y1="FY + FH" :y2="FY + FH" />
              <text :x="FX - 14" :y="FY + FH + 5" text-anchor="end">0</text>
            </template>
            <line :x1="FX - 8" :x2="FX" :y1="FY" :y2="FY" />
            <text :x="FX - 14" :y="FY + 5" text-anchor="end">{{ heroH }}</text>
            <text :x="FX - 95" :y="FY + FH / 2" text-anchor="middle"
                  :transform="`rotate(-90 ${FX - 95} ${FY + FH / 2})`" class="tp-axis-name">
              height above bed [m]
            </text>
          </g>
          <g class="tp-axis" v-if="tw.wipeT < 0.98">
            <rect :x="cbX" :y="FY" :width="18" :height="FH" fill="url(#tp-rdbu)"
                  stroke="rgba(255,255,255,0.6)" stroke-width="1.5" />
            <text :x="cbX + 28" :y="FY + 10">+{{ vmaxKpa }}</text>
            <text :x="cbX + 28" :y="FY + FH / 2 + 5">0</text>
            <text :x="cbX + 28" :y="FY + FH">−{{ vmaxKpa }}</text>
            <image class="tp-ax-eq"
                   v-bind="eqAt('ax_field_tau', K_LBL - 0.4, cbX + 9, FY - 26, 'center', 'baseline')" />
          </g>

          <!-- ── fig-1 schematic — fades in AUTOMATICALLY on the field
               stage: GOLD patch + gold ℓ, boundary-layer bands titled
               UPSTREAM / DOWNSTREAM, and the bed's sliding law
               in three places under the bed — Weertman outside, τ_b = 0
               across the patch. Bronze ink ON the field. ── -->
          <g v-if="tw.schemA > 0.004" :style="{ opacity: tw.schemA }">
            <!-- upstream + downstream boundary-layer bands -->
            <rect :x="xDim(-patchHalfKm - BL_SPAN_KM)" :y="FY"
                  :width="xDim(-patchHalfKm) - xDim(-patchHalfKm - BL_SPAN_KM)"
                  :height="FH"
                  fill="rgba(110,170,255,0.10)"
                  stroke="rgba(140,190,255,0.9)" stroke-width="2.5" stroke-dasharray="9 6" />
            <rect :x="xDim(patchHalfKm)" :y="FY"
                  :width="xDim(patchHalfKm + BL_SPAN_KM) - xDim(patchHalfKm)"
                  :height="FH"
                  fill="rgba(110,170,255,0.10)"
                  stroke="rgba(140,190,255,0.9)" stroke-width="2.5" stroke-dasharray="9 6" />
            <text :x="xDim(-patchHalfKm - BL_SPAN_KM / 2)" :y="FY - 44"
                  text-anchor="middle" class="tp-side-title">upstream</text>
            <text :x="xDim(patchHalfKm + BL_SPAN_KM / 2)" :y="FY - 44"
                  text-anchor="middle" class="tp-side-title">downstream</text>
            <text :x="xDim(-patchHalfKm - BL_SPAN_KM / 2)" :y="FY - 12"
                  text-anchor="middle" class="tp-band-label up">boundary layer</text>
            <text :x="xDim(patchHalfKm + BL_SPAN_KM / 2)" :y="FY - 12"
                  text-anchor="middle" class="tp-band-label up">boundary layer</text>

            <line :x1="FX" :x2="FX + tw.plotW" :y1="FY" :y2="FY"
                  stroke="#f5c75e" stroke-width="3.5" />
            <line :x1="FX" :x2="FX + tw.plotW" :y1="FY + FH" :y2="FY + FH"
                  stroke="#a8795a" stroke-width="3.5" />
            <!-- the slippery patch — GOLD -->
            <line :x1="xDim(-patchHalfKm)" :x2="xDim(patchHalfKm)"
                  :y1="FY + FH" :y2="FY + FH"
                  stroke="#f5c75e" stroke-width="9" stroke-linecap="round" />
            <!-- ℓ double-arrow just below the patch — split around a
                 centered gold ℓ so glyph and arrow never collide -->
            <line :x1="xDim(-patchHalfKm)" :x2="xDim(-0.8)"
                  :y1="FY + FH + 46" :y2="FY + FH + 46"
                  stroke="#f5c75e" stroke-width="2" marker-start="url(#tp-arrow)" />
            <line :x1="xDim(0.8)" :x2="xDim(patchHalfKm)"
                  :y1="FY + FH + 46" :y2="FY + FH + 46"
                  stroke="#f5c75e" stroke-width="2" marker-end="url(#tp-arrow)" />
            <image v-bind="eqAt('lbl_ell', 4.2, xDim(0), FY + FH + 58, 'center', 'baseline')" />
            <!-- h double-arrow at the far left (on field → dark) -->
            <line :x1="xDim(-37)" :x2="xDim(-37)" :y1="FY + 6" :y2="FY + FH - 6"
                  stroke="#7a4a10" stroke-width="2"
                  marker-start="url(#tp-arrow-dark)" marker-end="url(#tp-arrow-dark)" />
            <image v-bind="eqAt('lbl_h', 4.2, xDim(-37) + 14, FY + FH / 2 + 12, 'left', 'baseline')" />
            <!-- ice-flow arrow -->
            <line :x1="xDim(-30)" :x2="xDim(-16)" :y1="FY + 52" :y2="FY + 52"
                  stroke="#7a4a10" stroke-width="3" marker-end="url(#tp-arrow-dark)" />
            <text :x="xDim(-23)" :y="FY + 86" text-anchor="middle" class="tp-schem-label">ice flow</text>
            <!-- α: dashed reference dipping below the plot-horizontal surface -->
            <line :x1="xDim(16)" :x2="xDim(38)" :y1="FY + 4" :y2="FY + 52"
                  stroke="rgba(122,74,16,0.85)" stroke-width="2" stroke-dasharray="7 6" />
            <image v-bind="eqAt('lbl_alpha', 4.2, xDim(35.4), FY + 44, 'left', 'baseline')" />
            <!-- the bed's sliding law, in three places under the bed -->
            <image v-bind="eqAt('slide', K_EQ, xDim(-22), FY + FH + 112, 'center', 'baseline')" />
            <image v-bind="eqAt('slide0', K_EQ, xDim(0), FY + FH + 112, 'center', 'baseline')" />
            <image v-bind="eqAt('slide', K_EQ, xDim(22), FY + FH + 112, 'center', 'baseline')" />
          </g>

          <!-- The sweep line (average stage) — gold, level riding below -->
          <g v-if="tw.wipeT > 0.001 && tw.wipeT < 0.999">
            <line :x1="FX" :x2="FX + tw.plotW" :y1="sweepLineY" :y2="sweepLineY"
                  stroke="#f5c75e" stroke-width="4" />
            <image v-bind="eqAt('sweep_zh', K_LBL + 0.3, FX + tw.plotW - 88, sweepLineY + 34, 'right', 'baseline')" />
            <text :x="FX + tw.plotW - 14" :y="sweepLineY + 34" text-anchor="end" class="tp-sweep-label">
              {{ tw.wipeT.toFixed(2) }}
            </text>
          </g>
        </g>

        <!-- ══════════ ZONE HIGHLIGHTS (derivation) ══════════ -->
        <rect v-if="tw.bandPatch > 0.004" :style="{ opacity: tw.bandPatch }"
              :x="xDim(-patchHalfKm)" :y="curveTop"
              :width="xDim(patchHalfKm) - xDim(-patchHalfKm)"
              :height="curveBottom - curveTop"
              fill="rgba(245,199,94,0.08)"
              stroke="rgba(245,199,94,0.85)" stroke-width="2.5" stroke-dasharray="8 6" />
        <!-- (No boundary-layer rectangles — the director found the blue
             dashed boxes confusing and asked for the fades alone —
             the zone being solved is the one NOT faded.) -->

        <!-- The solutions ride their zones: eq (12) INSIDE the patch band
             (never outside it — the director found it confusing when the
             inside-the-patch solution appeared outside the patch; the x-range is ±30 km on
             these beats so it fits), eq (42)'s boundary-layer rows in the
             upstream AND downstream zones. -->

        <!-- Non-dim scales + master equations — land with the collapse
             and stay through the log-log stage (the director wanted them
             near the stress-curve figure). -->
        <g v-if="tw.masterA > 0.004" :style="{ opacity: tw.masterA }">
          <!-- two homes, CROSSFADED with the log-log squeeze (tw.colT):
               the plot's top-left, and the log-log column beside the
               plot — never a flight across the curve -->
          <g v-if="tw.colT < 0.996" :style="{ opacity: (1 - tw.colT) ** 2 }">
            <!-- The director's layout: the two scales in the [] above the
                 figure and the nondimensional solutions for the upstream,
                 patch, and downstream sections in the plot; the
                 downstream solution first went beneath the curve because
                 the upper right was taken by the legend — now
                 the legend lives bottom-left and the downstream
                 solution is top-right at K_ND (it no longer fit beneath the
                 curve at the back-row size). -->
            <image v-bind="eqAt('scales', K_ND_SCALES, EQ_CX, GOV_BASE_Y, 'center', 'baseline')" />
            <image v-bind="eqAt('master', K_ND, FX + 40, curveTop + 22)" />
            <image v-bind="eqAt('nd_mid_c', K_ND, ndZoneCenters[1], curveTop + 22, 'center', 'top')" />
            <image v-bind="eqAt('nd_dn', kNdDn, FX + tw.plotW - ND_ZONE_PAD, curveTop + 22, 'right', 'top')" />
          </g>
          <g v-if="tw.colT > 0.004" :style="{ opacity: tw.colT ** 2 }">
            <image v-bind="eqAt('scales', LOGLOG_EQ_K, LOGLOG_EQ_X, LOGLOG_EQ_Y)" />
            <image v-bind="eqAt('master', LOGLOG_EQ_K, LOGLOG_EQ_X, LOGLOG_MASTER_Y)" />
          </g>
        </g>

        <!-- ══════════ CURVE PLOT ══════════ -->
        <g v-if="tw.curveA > 0.004 || tw.ensA > 0.004">
          <!-- frame + zero line -->
          <rect :x="FX" :y="curveTop" :width="tw.plotW" :height="curveBottom - curveTop"
                fill="none" stroke="rgba(245,245,245,0.6)" stroke-width="2.5" />
          <line :x1="FX" :x2="FX + tw.plotW" :y1="yCurve(0)" :y2="yCurve(0)"
                stroke="rgba(245,245,245,0.4)" stroke-width="1.5" />

          <!-- dimensional axes (fade with axesA; fade out on collapse).
               Titles are the paper's Fig. 4a labels, LaTeX-set. -->
          <g class="tp-axis" :style="{ opacity: tw.axesA * (1 - tw.collapse) }">
            <template v-for="t in xTicksKm" :key="`cx${t}`">
              <line :x1="xDim(t)" :x2="xDim(t)" :y1="curveBottom" :y2="curveBottom + 8" />
              <text :x="xDim(t)" :y="curveBottom + 34" text-anchor="middle">{{ t }}</text>
            </template>
            <image class="tp-ax-eq"
                   v-bind="eqAt('ax_x_c', K_AX, FX + tw.plotW / 2, curveBottom + 46, 'center', 'top')" />
            <template v-for="t in yTicksKpa" :key="`cy${t}`">
              <line :x1="FX - 8" :x2="FX" :y1="yCurve(t)" :y2="yCurve(t)" />
              <text :x="FX - 14" :y="yCurve(t) + 5" text-anchor="end">{{ t }}</text>
            </template>
            <image class="tp-ax-eq"
                   v-bind="eqAt('ax_tau', K_AX, FX - 106, (curveTop + curveBottom) / 2, 'center', 'middle')"
                   :transform="`rotate(-90 ${FX - 106} ${(curveTop + curveBottom) / 2})`" />
          </g>

          <!-- u' axis — right-hand side, violet, the upper half only
               (the velocity perturbation is positive; zero on the stress
               zero line). -->
          <g v-if="tw.velA > 0.004" class="tp-axis tp-axis-vel" :style="{ opacity: tw.velA }">
            <template v-for="v in VEL_TICKS" :key="`vy${v}`">
              <line :x1="FX + tw.plotW" :x2="FX + tw.plotW + 8" :y1="yVel(v)" :y2="yVel(v)" />
              <text :x="FX + tw.plotW + 14" :y="yVel(v) + 9">{{ v }}</text>
            </template>
            <image v-bind="eqAt('ax_u', K_AX, FX + tw.plotW + 96, (curveTop + yVel(0)) / 2, 'center', 'middle')"
                   :transform="`rotate(-90 ${FX + tw.plotW + 96} ${(curveTop + yVel(0)) / 2})`" />
          </g>

          <!-- non-dimensional composite axis (fades in with collapse):
               Fig. 4b's three panels — words above, LaTeX axes below -->
          <g class="tp-axis" :style="{ opacity: tw.collapse }" v-if="tw.collapse > 0.004">
            <line :x1="zoneMidL" :x2="zoneMidL" :y1="curveTop" :y2="curveBottom"
                  stroke="rgba(245,245,245,0.5)" stroke-width="2.5" stroke-dasharray="5 6" />
            <line :x1="zoneMidR" :x2="zoneMidR" :y1="curveTop" :y2="curveBottom"
                  stroke="rgba(245,245,245,0.5)" stroke-width="2.5" stroke-dasharray="5 6" />
            <template v-for="t in ND_UP_TICKS" :key="`ndu${t}`">
              <line :x1="xNdUp(t)" :x2="xNdUp(t)" :y1="curveBottom" :y2="curveBottom + 8" />
              <text :x="xNdUp(t)" :y="curveBottom + 34" text-anchor="middle">{{ t }}</text>
            </template>
            <line :x1="xNdMid(0.5)" :x2="xNdMid(0.5)" :y1="curveBottom" :y2="curveBottom + 8" />
            <text :x="xNdMid(0.5)" :y="curveBottom + 34" text-anchor="middle">0</text>
            <template v-for="t in ND_DN_TICKS" :key="`ndd${t}`">
              <line :x1="xNdDn(t)" :x2="xNdDn(t)" :y1="curveBottom" :y2="curveBottom + 8" />
              <text :x="xNdDn(t)" :y="curveBottom + 34" text-anchor="middle">{{ t }}</text>
            </template>
            <template v-for="(c, i) in ndZoneCenters" :key="`ndz${i}`">
              <image class="tp-ax-eq"
                     v-bind="eqAt(ND_AXIS_EQS[i], K_AX, c, curveBottom + 46, 'center', 'top')" />
              <text :ref="(el) => setZoneWordEl(i, el)" :x="ndZoneWordX(i, c)" :y="curveTop - 16"
                    text-anchor="middle" class="tp-zone-word" :style="{ letterSpacing: ndZoneTracking }">
                {{ ND_ZONE_WORDS[i] }}
              </text>
            </template>
            <template v-for="t in [-1, 0, 1]" :key="`ndy${t}`">
              <line :x1="FX - 8" :x2="FX" :y1="yNd(t)" :y2="yNd(t)" />
              <text :x="FX - 14" :y="yNd(t) + 5" text-anchor="end">{{ t }}</text>
            </template>
            <image class="tp-ax-eq"
                   v-bind="eqAt('ax_nd_tau', K_AX, FX - 76, (curveTop + curveBottom) / 2, 'center', 'middle')"
                   :transform="`rotate(-90 ${FX - 76} ${(curveTop + curveBottom) / 2})`" />
          </g>

          <!-- ══ derivation: the three zones drawn (average → layers):
               patch-edge lines, zone words + the C of eq (8) ══ -->
          <g v-if="tw.zonesA > 0.004" :style="{ opacity: tw.zonesA }">
            <line :x1="xDim(-patchHalfKm)" :x2="xDim(-patchHalfKm)"
                  :y1="curveTop" :y2="curveBottom"
                  stroke="rgba(245,199,94,0.85)" stroke-width="2.5" stroke-dasharray="8 6" />
            <line :x1="xDim(patchHalfKm)" :x2="xDim(patchHalfKm)"
                  :y1="curveTop" :y2="curveBottom"
                  stroke="rgba(245,199,94,0.85)" stroke-width="2.5" stroke-dasharray="8 6" />
            <!-- (The M of DOWNSTREAM used to cross the figure box: the words
                 sat at x = ±22 km on the ±25 km axis;
                 the outer ones now hang from the plot's edges, ZONE_WORD_INSET in) -->
            <text :x="FX + ZONE_WORD_INSET" :y="curveBottom - 80" text-anchor="start"
                  class="tp-zone-word up" :style="{ opacity: 0.9 * dimOuter }">upstream</text>
            <text :x="xDim(0)" :y="curveBottom - 80" text-anchor="middle"
                  class="tp-zone-word patch" :style="{ opacity: (0.78 + 0.22 * tw.bandPatch) * dimPatch }">patch</text>
            <text :x="FX + tw.plotW - ZONE_WORD_INSET" :y="curveBottom - 80" text-anchor="end"
                  class="tp-zone-word up" :style="{ opacity: 0.9 * dimOuter }">downstream</text>
            <image :style="{ opacity: dimOuter }" v-bind="eqAt('cpos', K_LBL + 0.4, FX + ZONE_WORD_INSET, curveBottom - 26, 'left', 'baseline')" />
            <image :style="{ opacity: dimPatch }" v-bind="eqAt('c0', K_LBL + 0.4, xDim(0), curveBottom - 26, 'center', 'baseline')" />
            <image :style="{ opacity: dimOuter }" v-bind="eqAt('cpos', K_LBL + 0.4, FX + tw.plotW - ZONE_WORD_INSET, curveBottom - 26, 'right', 'baseline')" />
          </g>

          <!-- ══ ACL stage: patch region marked across the full y-range
               (tracks the ℓ slider when the viewer explores) ══ -->
          <g v-if="tw.aclA > 0.004" :style="{ opacity: tw.aclA }">
            <rect :x="xDim(-aclHalfKm)" :y="curveTop"
                  :width="xDim(aclHalfKm) - xDim(-aclHalfKm)"
                  :height="curveBottom - curveTop"
                  fill="rgba(245,199,94,0.05)"
                  stroke="rgba(245,199,94,0.8)" stroke-width="2.5" stroke-dasharray="8 6" />
          </g>

          <g clip-path="url(#tp-curveclip)">
            <!-- The u' profile (violet, the paper's eq 66 for the hero) and
                 the hero stress curve (gold), each drawn in two pieces —
                 outside the patch and inside it — so the zone NOT being
                 solved fades (the director's rule: while the work is
                 inside the patch, everything outside the patch should
                 fade, and while the up- and downstream
                 parts are being solved the patch should fade). -->
            <g v-for="side in CURVE_SIDES" :key="side"
               :clip-path="`url(#tp-clip-${side})`"
               :style="{ opacity: side === 'patch' ? dimPatch : dimOuter }">
              <path v-if="tw.velA > 0.004" :d="velPath" fill="none"
                    :stroke="VEL_COLOR" stroke-width="3" stroke-linejoin="round"
                    :style="{ opacity: 0.85 * tw.velA }" />
              <path v-if="tw.curveA > 0.004" :d="heroCurvePath" fill="none"
                    stroke="#f5c75e" stroke-width="3.5"
                    stroke-linejoin="round"
                    :style="{ opacity: tw.curveA }" />
            </g>

            <!-- analytic overlays (eqs 12 + 43, dimensional) — WHITE
                 dashed so they read against the gold simulation curve -->
            <path v-if="tw.anaMidA > 0.004" :d="anaMidPath" fill="none"
                  stroke="rgba(255,255,255,0.95)" stroke-width="3" stroke-dasharray="10 7"
                  :style="{ opacity: tw.anaMidA * (1 - tw.cardMid) * dimPatch }" />
            <template v-if="tw.anaUpA > 0.004">
              <path :d="anaUpPath" fill="none"
                    stroke="rgba(255,255,255,0.95)" stroke-width="3" stroke-dasharray="10 7"
                    :style="{ opacity: tw.anaUpA * (1 - tw.cardUp) * dimOuter }" />
              <path :d="anaDnPath" fill="none"
                    stroke="rgba(255,255,255,0.95)" stroke-width="3" stroke-dasharray="10 7"
                    :style="{ opacity: tw.anaUpA * (1 - tw.cardUp) * dimOuter }" />
            </template>
            <!-- ensemble (ensemble → log-log); each run lerps dim → nondim -->
            <g v-if="tw.ensA > 0.004" :style="{ opacity: tw.ensA }">
              <g v-for="(r, i) in ensembleRuns" :key="`run${i}`"
                 :style="{ opacity: runOpacity(r), transition: 'opacity 0.25s' }">
                <path :d="runPaths[i]" fill="none"
                      :stroke="H_COLORS[r.h]" stroke-width="2.2"
                      stroke-linejoin="round"
                      :stroke-dasharray="r.gamma === 0.5 ? '8 6' : undefined" />
                <path v-for="(mk, k) in runMarkers[i]" :key="`mk${i}-${k}`"
                      :d="mk" :fill="H_COLORS[r.h]" fill-opacity="0.9"
                      stroke="rgba(0,0,0,0.5)" stroke-width="0.8" />
              </g>
              <!-- master curve (n=1: exp / linear / −exp) -->
              <path v-if="tw.masterA > 0.004" :d="masterPath" fill="none"
                    stroke="#f5c75e" stroke-width="4.5"
                    :style="{ opacity: tw.masterA }" />
            </g>

            <!-- ══ ACL stage: τ_val line + the measured length. All of it
                 tracks the τ_val/α/h/ℓ sliders. ══ -->
            <g v-if="tw.aclA > 0.004" :style="{ opacity: tw.aclA }">
              <line :x1="FX" :x2="FX + tw.plotW" :y1="yCurve(aclTauVal)" :y2="yCurve(aclTauVal)"
                    stroke="rgba(255,255,255,0.85)" stroke-width="2" stroke-dasharray="10 8" />
              <text :x="FX + tw.plotW - 20" :y="yCurve(aclTauVal) - 14" text-anchor="end" class="tp-acl-tauval">τ<tspan class="tp-sub" dy="7">val</tspan><tspan dy="-7"> = {{ aclTauVal }} kPa</tspan></text>
              <template v-if="aclHasCross">
                <!-- drop lines at the crossing + the patch onset, from
                     the τ_val line up to the arrow -->
                <line :x1="xDimClamped(aclCrossKm)" :x2="xDimClamped(aclCrossKm)"
                      :y1="yCurve(aclTauVal)" :y2="aclArrowY"
                      stroke="rgba(245,199,94,0.9)" stroke-width="2.5" stroke-dasharray="4 5" />
                <line :x1="xDim(aclOnsetKm)" :x2="xDim(aclOnsetKm)"
                      :y1="yCurve(aclTauVal)" :y2="aclArrowY"
                      stroke="rgba(245,199,94,0.9)" stroke-width="2.5" stroke-dasharray="4 5" />
                <!-- the ACL itself — gold double arrow ABOVE the curve's
                     peak (the director's request), the estimate on a
                     dark plate right above it -->
                <line :x1="xDimClamped(aclCrossKm)" :x2="xDim(aclOnsetKm)"
                      :y1="aclArrowY" :y2="aclArrowY"
                      stroke="#f5c75e" stroke-width="3.5"
                      marker-start="url(#tp-arrow)" marker-end="url(#tp-arrow)" />
                <rect :x="aclPlate.x" :y="aclPlate.y" :width="aclPlate.w" :height="ACL_PLATE_H"
                      rx="10" class="tp-acl-plate" />
                <text :x="aclPlate.x + aclPlate.w / 2" :y="aclPlate.y + ACL_PLATE_H - 16"
                      text-anchor="middle" class="tp-acl-label">{{ aclText }}</text>
              </template>
            </g>
          </g>

          <!-- ── ensemble legend — INSIDE the axes (ensemble → log-log).
               Column heads are LaTeX; the gold master curve gets
               its own row once it lands. ── -->
          <g v-if="tw.ensA > 0.02" :style="{ opacity: tw.ensA * legFade }" class="tp-leg"
             @mouseleave="hoverFilter = null">
            <rect :x="legX" :y="legY" :width="LEGW" :height="LEGH" rx="10"
                  fill="rgba(10,9,8,0.88)" stroke="rgba(245,199,94,0.6)" stroke-width="2" />
            <text :x="legX + 18" :y="legY + 38" class="tp-leg-title">
              {{ ensembleRuns.length }} Elmer/Ice runs
            </text>
            <image v-bind="eqAt('leg_n1', K_LBL, legX + LEGW - 18, legY + 38, 'right', 'baseline')" />
            <!-- h column — click a row to PIN it -->
            <image class="tp-leg-head" v-bind="eqAt('leg_h', K_LBL, legX + 18, legY + 76, 'left', 'baseline')" />
            <g v-for="(h, i) in [300, 1000, 2000, 3000]" :key="`lh${h}`"
               class="tp-leg-row"
               @mouseenter="hoverFilter = { key: 'h', value: h }"
               @click="togglePin('h', h)">
              <rect :x="legX + 10" :y="legY + 86 + i * 36" width="130" height="34" rx="6"
                    :fill="pinned.h === h ? 'rgba(245,199,94,0.14)' : 'transparent'"
                    :stroke="pinned.h === h ? 'rgba(245,199,94,0.8)' : 'none'"
                    stroke-width="1.5" />
              <rect :x="legX + 18" :y="legY + 94 + i * 36" width="22" height="22" rx="4"
                    :fill="H_COLORS[h]" />
              <text :x="legX + 50" :y="legY + 112 + i * 36" class="tp-leg-txt">{{ h }}</text>
            </g>
            <!-- α column -->
            <image class="tp-leg-head" v-bind="eqAt('leg_alpha', K_LBL, legX + 168, legY + 76, 'left', 'baseline')" />
            <g v-for="(a, i) in ['0.1', '0.5', '1.0']" :key="`la${a}`"
               class="tp-leg-row"
               @mouseenter="hoverFilter = { key: 'alpha', value: parseFloat(a) }"
               @click="togglePin('alpha', parseFloat(a))">
              <rect :x="legX + 160" :y="legY + 86 + i * 36" width="112" height="34" rx="6"
                    :fill="pinned.alpha === parseFloat(a) ? 'rgba(245,199,94,0.14)' : 'transparent'"
                    :stroke="pinned.alpha === parseFloat(a) ? 'rgba(245,199,94,0.8)' : 'none'"
                    stroke-width="1.5" />
              <text :x="legX + 168" :y="legY + 114 + i * 36" class="tp-leg-glyph">{{ ALPHA_GLYPHS[a] }}</text>
              <text :x="legX + 202" :y="legY + 112 + i * 36" class="tp-leg-txt">{{ a }}</text>
            </g>
            <!-- γ column -->
            <image class="tp-leg-head" v-bind="eqAt('leg_gamma', K_LBL, legX + 296, legY + 76, 'left', 'baseline')" />
            <g class="tp-leg-row" @mouseenter="hoverFilter = { key: 'gamma', value: 0.1 }"
               @click="togglePin('gamma', 0.1)">
              <rect :x="legX + 288" :y="legY + 86" width="130" height="34" rx="6"
                    :fill="pinned.gamma === 0.1 ? 'rgba(245,199,94,0.14)' : 'transparent'"
                    :stroke="pinned.gamma === 0.1 ? 'rgba(245,199,94,0.8)' : 'none'"
                    stroke-width="1.5" />
              <line :x1="legX + 296" :x2="legX + 334" :y1="legY + 106" :y2="legY + 106"
                    stroke="rgba(245,245,245,0.9)" stroke-width="3" />
              <text :x="legX + 344" :y="legY + 112" class="tp-leg-txt">0.1</text>
            </g>
            <g class="tp-leg-row" @mouseenter="hoverFilter = { key: 'gamma', value: 0.5 }"
               @click="togglePin('gamma', 0.5)">
              <rect :x="legX + 288" :y="legY + 122" width="130" height="34" rx="6"
                    :fill="pinned.gamma === 0.5 ? 'rgba(245,199,94,0.14)' : 'transparent'"
                    :stroke="pinned.gamma === 0.5 ? 'rgba(245,199,94,0.8)' : 'none'"
                    stroke-width="1.5" />
              <line :x1="legX + 296" :x2="legX + 334" :y1="legY + 142" :y2="legY + 142"
                    stroke="rgba(245,245,245,0.9)" stroke-width="3" stroke-dasharray="8 6" />
              <text :x="legX + 344" :y="legY + 148" class="tp-leg-txt">0.5</text>
            </g>
            <!-- the gold master curve = the analytical solution
                 — in the free fourth row under α / γ, so the box never grows -->
            <g v-if="tw.masterA > 0.004" :style="{ opacity: tw.masterA }">
              <line :x1="legX + 168" :x2="legX + 206" :y1="legY + 206" :y2="legY + 206"
                    stroke="#f5c75e" stroke-width="4.5" stroke-linecap="round" />
              <text :x="legX + 216" :y="legY + 214" class="tp-leg-txt tp-leg-ana">analytical solution</text>
            </g>
          </g>
        </g>

        <!-- Each solution lands on a CARD first (the director asked for
             an outlined card like the takeaway cards, with the solution
             larger than it will be on the next beat, when it is placed
             inside the patch bounds, and the same cadence for the up-
             and downstream solutions): the patch solution on its beat,
             the two boundary-layer rows on a card EACH (one card for
             upstream, one for downstream, at the director's request), stacked
             the same width; drawn AFTER the curve plot so the plates sit
             over the curve (more opaque); the NEXT beat shrinks
             them into their zones (tw.cardMid / tw.cardUp 1 → 0) and the
             dashed overlays draw as they land. -->
        <template v-if="tw.anaMidA > 0.004">
          <rect v-if="tw.cardMid > 0.004" class="tp-eq-card"
                :style="{ opacity: tw.anaMidA * tw.cardMid ** 2 }"
                v-bind="cardRect([midPose])" />
          <image :style="{ opacity: tw.anaMidA * (tw.cardMid + (1 - tw.cardMid) * dimPatch) }"
                 v-bind="midPose" />
        </template>
        <template v-if="tw.anaUpA > 0.004">
          <rect v-if="tw.cardUp > 0.004" class="tp-eq-card"
                :style="{ opacity: tw.anaUpA * tw.cardUp ** 2 }"
                v-bind="cardRect([upPose], cardWUp)" />
          <rect v-if="tw.cardUp > 0.004" class="tp-eq-card"
                :style="{ opacity: tw.anaUpA * tw.cardUp ** 2 }"
                v-bind="cardRect([dnPose], cardWUp)" />
          <image :style="{ opacity: tw.anaUpA * (tw.cardUp + (1 - tw.cardUp) * dimOuter) }"
                 v-bind="upPose" />
          <image :style="{ opacity: tw.anaUpA * (tw.cardUp + (1 - tw.cardUp) * dimOuter) }"
                 v-bind="dnPose" />
        </template>

        <!-- ══════════ ACL equations — stages 7–8:
             in the equation band ABOVE the plot (tw.topPad drops
             the plot top to make room), side by side, centered over the
             plot. Real LaTeX (build_acl_eqs.py) at ONE shared scale so
             the two read at the same glyph size, baselines aligned; the
             slider parameters h, α, ℓ, τ_val are inked gold in the TeX
             source. ══════════ -->
        <g v-if="stage >= S.acl && tw.aclA > 0.004" :style="{ opacity: tw.aclA }">
          <image :href="eq2Url('acl')"
                 :x="aclEqs.aclX" :y="EQ2_BASELINE_Y - EQ2_ACL.asc * EQ2_K"
                 :width="EQ2_ACL.w * EQ2_K" :height="EQ2_ACL.h * EQ2_K" />
          <image :href="eq2Url('taumax')"
                 :x="aclEqs.tauX" :y="EQ2_BASELINE_Y - EQ2_TAU.asc * EQ2_K"
                 :width="EQ2_TAU.w * EQ2_K" :height="EQ2_TAU.h * EQ2_K" />
        </g>

        <!-- ══════════ stage 8: α + h Greenland maps.
             The plot squeezes left (tw.plotW) and the two maps
             sit BESIDE it on a translucent panel — never over the curve,
             axes or equations. The PNGs are map-only on transparent
             backgrounds; titles + colorbars are drawn here, at figure
             scale, so the ticks stay legible at any window size. ══════ -->
        <g v-if="tw.mapsA > 0.004" :style="{ opacity: tw.mapsA }">
          <rect :x="mapsPanel.x" :y="mapsPanel.y" :width="mapsPanel.w" :height="mapsPanel.h"
                rx="14" fill="rgba(20, 17, 12, 0.42)"
                stroke="rgba(245, 199, 94, 0.45)" stroke-width="2" />
          <g v-for="(m, i) in MAPS2" :key="m.key">
            <text :x="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP) + MAP2_W / 2"
                  :y="mapsPanel.y + MAPS_PAD + MAP2_TITLE_H - 12"
                  text-anchor="middle" class="tp-map-title">{{ m.title }} <tspan class="tp-map-sym">{{ m.sym }}</tspan> {{ m.unit }}</text>
            <image :href="m.url"
                   :x="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP)"
                   :y="mapsPanel.y + MAPS_PAD + MAP2_TITLE_H"
                   :width="MAP2_W" :height="MAP2_W * MAP2_ASPECT" />
            <!-- horizontal colorbar under the map -->
            <rect :x="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP)"
                  :y="mapsCbarY" :width="MAP2_W" height="16" rx="3"
                  :fill="`url(#tp-cmap-${m.key})`"
                  stroke="rgba(255,255,255,0.6)" stroke-width="1.5" />
            <template v-for="t in m.ticks" :key="`${m.key}t${t.v}`">
              <line :x1="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP) + (t.v / m.vmax) * MAP2_W"
                    :x2="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP) + (t.v / m.vmax) * MAP2_W"
                    :y1="mapsCbarY + 16" :y2="mapsCbarY + (t.label ? 25 : 22)"
                    stroke="rgba(245,245,245,0.9)" stroke-width="2" />
              <text v-if="t.label"
                    :x="mapsPanel.x + MAPS_PAD + i * (MAP2_W + MAPS_GAP) + (t.v / m.vmax) * MAP2_W"
                    :y="mapsCbarY + 52"
                    :text-anchor="t.v === 0 ? 'start' : t.v === m.vmax ? 'end' : 'middle'"
                    class="tp-map-tick">{{ t.label }}</text>
            </template>
          </g>
        </g>
      </svg>
    </div>

    <!-- ══════════ log-log verification — its OWN stage. The
         collapsed figure squeezes left (tw.plotW) and the two square
         cards land SIDE BY SIDE on the right (the director wanted them
         side by side so each could be a little larger),
         each as wide as the column allows. Like the ACL slider card the
         column is laid out in FIGURE units and scaled through figRect,
         so the cards keep their place beside the plot at any window
         size; the legend + the scales/master equations sit under them
         (SVG, LOGLOG_* constants) — neither fits in the squeezed plot. -->
    <div
      class="tp-loglog"
      :style="{
        opacity: tw.loglogA,
        left: `${figRect.ox + COL_X * figRect.s}px`,
        top: `${figRect.oy + COL_TOP * figRect.s}px`,
        width: `${COL_W}px`,
        height: `${CARD_H}px`,
        gap: `${CARD_GAP}px`,
        transform: `scale(${figRect.s})`,
      }"
      v-show="tw.loglogA > 0.02"
    >
      <div v-for="card in loglogCards" :key="card.key" class="tp-loglog-card">
        <div class="tp-loglog-title">{{ card.title }}</div>
        <svg :viewBox="`0 0 ${LL_W} ${LL_H}`" class="tp-loglog-svg">
          <!-- faded decade gridlines -->
          <template v-for="d in card.decades" :key="`g${d}`">
            <line :x1="card.x(d)" :x2="card.x(d)" :y1="LL_TOP" :y2="LL_TOP + LL_P"
                  stroke="rgba(245,245,245,0.16)" stroke-width="1.5" />
            <line :x1="LLP" :x2="LLP + LL_P" :y1="card.y(d)" :y2="card.y(d)"
                  stroke="rgba(245,245,245,0.16)" stroke-width="1.5" />
          </template>
          <rect :x="LLP" :y="LL_TOP" :width="LL_P" :height="LL_P"
                fill="none" stroke="rgba(245,245,245,0.6)" stroke-width="2.5" />
          <template v-for="d in card.decades" :key="`d${d}`">
            <line :x1="card.x(d)" :x2="card.x(d)" :y1="LL_TOP + LL_P" :y2="LL_TOP + LL_P + 6"
                  stroke="rgba(245,245,245,0.8)" stroke-width="2.5" />
            <text :x="card.x(d)" :y="LL_TOP + LL_P + 34" text-anchor="middle" class="tp-ll-tick">
              10<tspan class="tp-ll-sup" dy="-13">{{ exp10(d) }}</tspan>
            </text>
            <line :x1="LLP - 6" :x2="LLP" :y1="card.y(d)" :y2="card.y(d)"
                  stroke="rgba(245,245,245,0.8)" stroke-width="2.5" />
            <text :x="LLP - 8" :y="card.y(d) + 9" text-anchor="end" class="tp-ll-tick">
              10<tspan class="tp-ll-sup" dy="-13">{{ exp10(d) }}</tspan>
            </text>
          </template>
          <!-- axis titles: Fig. 4c/d's, LaTeX-set. The y title
               lies HORIZONTAL over the plot box's top-left (not rotated
               down the side) — that side margin is what the bigger
               square is made of. -->
          <image class="tp-ax-eq"
                 v-bind="eqAt(card.xlabel, K_LL, LLP + LL_P / 2, LL_TOP + LL_P + 46, 'center', 'top')" />
          <image class="tp-ax-eq"
                 v-bind="eqAt(card.ylabel, K_LL, LLP, LL_TOP - 10, 'left', 'bottom')" />
          <line :x1="card.line.x1" :y1="card.line.y1" :x2="card.line.x2" :y2="card.line.y2"
                stroke="#f5c75e" stroke-width="3.5" stroke-dasharray="9 6" />
          <!-- slope-1 reference triangle -->
          <path :d="card.tri.d" fill="none" stroke="rgba(245,245,245,0.9)" stroke-width="2.5" />
          <text :x="card.tri.lx" :y="card.tri.ly" text-anchor="middle" class="tp-ll-tick">1</text>
          <text :x="card.tri.bx" :y="card.tri.by" text-anchor="middle" class="tp-ll-tick">1</text>
          <path v-for="(p, i) in card.pts" :key="`p${i}`"
                :d="p.d"
                :fill="p.open ? 'none' : p.c"
                :stroke="p.open ? p.c : 'rgba(0,0,0,0.5)'"
                :stroke-width="p.open ? 2 : 0.8"
                :style="{ opacity: p.dim ? 0.08 : 0.9, transition: 'opacity 0.25s' }" />
        </svg>
        <div class="tp-loglog-caption">
          <img :src="eq2Url('ll_kappa')" class="tp-ll-kappa" alt="κ ="
               :style="{
                 width: `${CH1_EQ.ll_kappa.w * LL_CAP_K}px`,
                 height: `${CH1_EQ.ll_kappa.h * LL_CAP_K}px`,
                 verticalAlign: `${-(CH1_EQ.ll_kappa.h - CH1_EQ.ll_kappa.base) * LL_CAP_K}px`,
               }" />
          {{ card.caption }}
        </div>
      </div>
    </div>

    <!-- ══════════ ACL exploration sliders — the acl stage.
         The viewer drives τ_val, α, h, ℓ, γ and the analytic n=1
         profile, the τ_val line, and the measured ACL all follow live.
         Laid out in FIGURE coordinates — the
         card is sized in viewBox units and scaled with the SVG
         (figRect), so it sits in the plot's lower-left quadrant (x < 0,
         τ < 0: never touched by the curve, below the ACL arrow) at the
         same place at every window width. Stage 8 (maps) squeezes the
         plot, so the card bows out there. ══════ -->
    <div
      class="tp-acl-controls"
      v-if="stage >= S.loglog"
      :style="{
        opacity: tw.aclA * (1 - tw.mapsA),
        pointerEvents: stage === S.acl ? 'auto' : 'none',
        left: `${figRect.ox + ACL_CARD.x * figRect.s}px`,
        top: `${figRect.oy + ACL_CARD.y * figRect.s}px`,
        width: `${ACL_CARD.w}px`,
        height: `${ACL_CARD.h}px`,
        transform: `scale(${figRect.s})`,
      }"
    >
      <div class="tp-ctl-row">
        <span class="tp-ctl-sym">τ<sub>val</sub></span>
        <input type="range" min="10" max="100" step="1"
               v-model.number="aclCtl.tauVal" />
        <span class="tp-ctl-val">{{ aclCtl.tauVal }} kPa</span>
      </div>
      <div class="tp-ctl-row">
        <span class="tp-ctl-sym">α</span>
        <input type="range" min="0.1" max="1.0" step="0.05"
               v-model.number="aclCtl.alphaDeg" />
        <span class="tp-ctl-val">{{ aclCtl.alphaDeg.toFixed(2) }}°</span>
      </div>
      <div class="tp-ctl-row">
        <span class="tp-ctl-sym">h</span>
        <input type="range" min="300" max="3000" step="50"
               v-model.number="aclCtl.h" />
        <span class="tp-ctl-val">{{ aclCtl.h }} m</span>
      </div>
      <div class="tp-ctl-row">
        <span class="tp-ctl-sym">ℓ</span>
        <input type="range" min="2" max="20" step="0.5"
               v-model.number="aclCtl.ellKm" />
        <span class="tp-ctl-val">{{ aclCtl.ellKm.toFixed(1) }} km</span>
      </div>
      <!-- γ as a two-position slider (0.1 · 0.5), the
           same toggle as the twin globes. step 0.4 from 0.1 lands on
           exactly the two values. The reset shares its row. -->
      <div class="tp-ctl-row">
        <span class="tp-ctl-sym">γ</span>
        <div class="tp-ctl-gamma">
          <input type="range" min="0.1" max="0.5" step="0.4" class="tp-binary"
                 v-model.number="aclCtl.gamma" />
          <span class="tp-ctl-val">{{ aclCtl.gamma.toFixed(1) }}</span>
        </div>
        <button class="tp-ctl-reset" @click="resetAclCtl">↺ defaults</button>
      </div>
    </div>

    <!-- Log-log stage: the door to the chapter's backup
         slides, bottom-right. -->
    <MoreDetailsPill
      v-if="stage === S.loglog"
      class="tp-more"
      :style="{ opacity: tw.loglogA, pointerEvents: tw.loglogA > 0.5 ? 'auto' : 'none' }"
    />
    <!-- the derivation door on the theory beats (the director asked for a
         "dive deeper: derivation" button on the Chapter 1 theory pages) -->
    <MoreDetailsPill
      v-if="stage >= S.patchGovern && stage <= S.summary"
      class="tp-more"
      label="Derivation"
      to="/additional-work/deeper/chapter1#derivation"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { mediaUrl } from '../config/media'
import MoreDetailsPill from './MoreDetailsPill.vue'
import {
  TP_VW, TP_VH, TP_FX, TP_FW, TP_FY, TP_FH, TP_HALF_KM,
} from '../config/theoryLayout'
import { ch1Stage } from '../config/ch1Beats'
import { CH1_EQ, CH1_EQ_CUTS_SSA, type Ch1EqName } from '../config/ch1Eqs'

const props = defineProps<{
  /** Math-mode stage = the Ch.1 beat minus ch1First('field'); named
   *  below as S.* (config/ch1Beats.ts owns the order). */
  stage: number
  /** True while warm-mounted behind the live globe (beat 3, and again
   *  on the twins beat): fully transparent, heavy first paint already
   *  done, waiting for the seam entry. */
  hidden?: boolean
  /** One-shot stage-0 entry effect (beat 3→4 morph):
   *  'seam' enters with a TRANSPARENT backdrop — the globe's flattened,
   *  painted slab (camera-fit to this panel's field rect) stays visible
   *  while the identical field image fades in over it, then the
   *  chalkboard dims the surroundings. Null = plain entry (opaque). */
  entryFx?: 'seam' | null
}>()

// ─────────────────────── static geometry ──────────────────────────────
// Full-screen stage: the viewBox approximates the
// viewport's aspect so the figure genuinely spans the screen. The
// stage-0 field-rect constants are SHARED with the beat 3→4 seam morph
// (src/config/theoryLayout.ts) — the Globe fits its camera so the slab
// lands exactly on this rect.
const VW = TP_VW
const VH = TP_VH
const FX = TP_FX        // plot-left
const FY = TP_FY        // field top
const FH = TP_FH        // field height
const CURVE_TOP_FULL = 110
const CURVE_BOTTOM = 850

const HALF_KM = TP_HALF_KM  // field/curve x half-range [km]
const X_TICKS_KM = [-40, -30, -20, -10, 0, 10, 20, 30, 40]
/** The derivation beats zoom the x-range to ±25 km (the director suggested ±30; 25 keeps the in-band equation legible) so
 *  the patch solution fits INSIDE its band; the field (±40 km raster),
 *  the ensemble and the ACL keep ±40. */
const DERIV_HALF_KM = 25
const COLLAPSE_TOP_PAD = 60   // room for the scales above the collapsed plot
const CURVE_SIDES = ['outer', 'patch'] as const
const ND_UP_TICKS = [-6, -4, -2]
const ND_DN_TICKS = [2, 4, 6]
const ND_TAU_MAX = 1.35

// Schematic boundary-layer band span [km] (≈ 2·[x] for the hero run).
const BL_SPAN_KM = 9

// Non-dim composite zones (fractions of plot width).
const ZONE_UP_F = 0.40
const ZONE_MID_F = 0.24

// Legend box (inside the plot axes, top-right, on the ensemble +
// collapse stages; in the log-log column once the plot squeezes).
// The "analytical solution" entry takes the
// free fourth row under the α / γ columns.
const LEGW = 440
const LEGH = 246

// ── Log-log stage layout ────────────────────────────────────────────
// The plot squeezes to LOGLOG_PLOTW and the right column takes the rest
// of the figure: the two SQUARE cards SIDE BY SIDE on top,
// each CARD_W wide, and under them the scales + master equations
// (left, beside the plot) and the ensemble legend (right) — the
// squeezed plot has no pocket left for either (the legend's old
// bottom-left pocket is crossed by the patch ramp below ~810 units).
// Everything is in figure units: the HTML column rides figRect like
// the ACL slider card, so one number places a thing at every window
// size (1 unit = 0.70 px at 1280, 0.79 at 1440, 1.06 at 1920×1200).
const LOGLOG_PLOTW = 640
const COL_X = FX + LOGLOG_PLOTW + 40          // 830: column left
const COL_W = VW - 20 - COL_X                 // 930: to the figure's right margin
const COL_TOP = 44                            // the figure's top edge is already under the sub-menu bar
const CARD_W = 450
const CARD_GAP = COL_W - 2 * CARD_W           // 30
const CARD_PAD = 12
// The card's SVG — its viewBox is in the same units (rendered 1:1).
const LL_W = CARD_W - 2 * CARD_PAD            // 426
const LLP = 66                                // left: y tick labels
const LL_RIGHT = 30                           // right: the last x label's overhang
const LL_TOP = 60                             // top: the horizontal y-axis title
const LL_P = LL_W - LLP - LL_RIGHT            // 330: the square plot box
const LL_H = LL_TOP + LL_P + 46 + 48          // 484: + x ticks + x-axis title
const CARD_TITLE_H = 34
const CARD_CAPTION_H = 36
// CSS heights below are these same numbers.
const CARD_H = CARD_PAD + CARD_TITLE_H + 6 + LL_H + CARD_CAPTION_H + 10   // 582
const LL_CAP_K = 2.9                          // caption's κ glyph: units per bp (≈ the 24-unit caption)
// Row 2 of the column: the equations (k 2.8, stacked, beside the plot)
// and the legend (right-aligned) share one LEGH-tall band.
const ROW2_Y = COL_TOP + CARD_H + 14          // 640 (ends 886: 20 px above the MORE DETAILS pill at 1280×800)
const LOGLOG_EQ_K = 2.8
const LOGLOG_EQ_X = COL_X
const LOGLOG_LEG_X = VW - 20 - LEGW           // 1320

// ── Stage names (config/ch1Beats.ts owns the order) ────────────────────
const S = {
  field: ch1Stage('field'),
  average: ch1Stage('average'),
  patchGovern: ch1Stage('patch-govern'),
  patchVelocity: ch1Stage('patch-velocity'),
  patchSolution: ch1Stage('patch-solution'),
  layersGovern: ch1Stage('layers-govern'),
  layersVelocity: ch1Stage('layers-velocity'),
  layersSolution: ch1Stage('layers-solution'),
  summary: ch1Stage('summary'),
  ensemble: ch1Stage('ensemble'),
  collapse: ch1Stage('collapse'),
  loglog: ch1Stage('loglog'),
  acl: ch1Stage('acl'),
  maps: ch1Stage('maps'),
} as const
/** The depth-averaged derivation: average → summary. */
function isDerivation(s: number): boolean {
  return s >= S.average && s <= S.summary
}

// ── LaTeX typography ───────────────────────────────────────────────────
// Every math glyph on the panel is Computer Modern compiled by latex +
// dvisvgm (cinematic/scene_ch01/build_theory_eqs.py → R2 ch01/eq2/).
// Sizes come from the TeX boxes (config/ch1Eqs.ts, in bp); K_* are
// viewBox units per bp, so one K = one type size everywhere it is used.
const K_GOV = 4.4     // the governing equation (reserved area)
const K_EQ = 3.6      // derived equations (row B, in-plot)
const K_AX = 3.6      // axis titles
const K_LBL = 3.2     // legend heads, in-plot reminders, schematic
const K_LL = 3.3      // log-log card axis titles (the card SVG renders 1:1 in figure units)
// The collapse beat's non-dimensional solutions in the plot and the two
// scales above it (the director asked for bigger nondimensional solution
// equations: there was space to fill, and the talk is projected for
// people at the back of the room — 3.4 before).
const K_ND = 4.8
const K_ND_SCALES = 4.2
// The downstream row is the longest and its zone (zoneMidR → the plot's
// right edge) the narrowest: it is sized to that zone with ND_ZONE_PAD
// each side, never past the divider (the τ used to overlap the dashed
// line, which the director flagged).
const ND_ZONE_PAD = 16

function eq2Url(name: string): string {
  return mediaUrl(`ch01/eq2/${name}.svg`)
}
type HAnchor = 'left' | 'center' | 'right'
type VAnchor = 'top' | 'baseline' | 'middle' | 'bottom'
/** <image> attributes placing equation `name` at scale k with the
 *  (x, y) anchor. `file` overrides the SVG (split pieces share a box). */
function eqAt(
  name: Ch1EqName, k: number, x: number, y: number,
  ha: HAnchor = 'left', va: VAnchor = 'top', file?: string,
): { href: string; x: number; y: number; width: number; height: number } {
  const b = CH1_EQ[name]
  const w = b.w * k
  const h = b.h * k
  const x0 = ha === 'left' ? x : ha === 'center' ? x - w / 2 : x - w
  const y0 =
    va === 'top' ? y
      : va === 'baseline' ? y - b.base * k
        : va === 'middle' ? y - h / 2
          : y - h
  return { href: eq2Url(file ?? name), x: x0, y: y0, width: w, height: h }
}

// ── The reserved equation area (the director's rule: that area is
// reserved for the equations) — above the domain on stage 0 (Stokes), above
// the plot through the derivation (the SSA, never leaving; row B below
// it holds each derived result). ──
const EQ_CX = FX + TP_FW / 2                 // centered on the plot
// Baseline 78: the SSA's top sits 30 units under the figure's top edge,
// which .tp-stage now keeps ≥ 0.5 rem below the ribbon's sub-menu bar
// at every window size (the band used to reach
// into the figure on height-limited viewports).
const GOV_BASE_Y = 78                        // governing-eq baseline
const BRACE_Y = GOV_BASE_Y + (CH1_EQ.ssa.h - CH1_EQ.ssa.base) * K_GOV + 6
const ROWB_BASE_Y = 171                      // row-B baseline (the τ–u relation, centred)
// Plot top through the derivation: the field (shifted by
// DERIV_FIELD_SHIFT during the wipe) ends 46 units above it, so the
// wipe's growing curve box lands exactly here.
const DERIV_TOP_PAD = 130                    // curveTop 110 + 130 = 240
const DERIV_FIELD_SHIFT = CURVE_TOP_FULL + DERIV_TOP_PAD - 46 - FY

// SSA split geometry (eq 7): TeX-measured term extents [bp → units].
const SSA_X0 = EQ_CX - (CH1_EQ.ssa.w * K_GOV) / 2
const SSA_GAP = (CH1_EQ_CUTS_SSA.dragEnd - CH1_EQ_CUTS_SSA.memEnd) * K_GOV
const SSA_PAD = 1.5 * K_GOV

// Velocity (faint violet, right-hand axis). Zero sits on the
// stress plot's zero line — both perturbations decay to 0 in the far
// field — and the axis tops out at VEL_TOP.
const VEL_COLOR = '#b9a3ec'
const VEL_TOP = 300           // m/yr at the plot top
const VEL_TICKS = [0, 100, 200, 300]

// Okabe-Ito, matched to the site palette.
const H_COLORS: Record<number, string> = {
  300: '#e69f00',
  1000: '#56b4e9',
  2000: '#f0e442',
  3000: '#7bd8b4',
}
const ALPHA_GLYPHS: Record<string, string> = { '0.1': '●', '0.5': '◆', '1.0': '▲' }

function exp10(d: number): number {
  return Math.round(Math.log10(d))
}

const fieldUrl = mediaUrl('ch01/field2d_n1.png')

// ── ACL stages 7–8: the equation band ────────────────────────────────
// The plot top drops by ACL_TOP_PAD so the ACL + max-τxx equations sit
// ABOVE the chart, side by side. They are real LaTeX (latex + dvisvgm,
// cinematic/scene_ch01/build_acl_eqs.py); EQ2_* are their dvisvgm
// viewBoxes in TeX pt (w, h, and the height above the baseline), and
// both draw at the SAME scale EQ2_K so their glyphs match, with the
// baselines aligned. (eq2Url is shared with the derivation's LaTeX,
// build_theory_eqs.py — same R2 folder, disjoint names.)
// 69 / 36 (were 55 / 22): the band's exponents start 36 units under
// the figure's top edge, itself kept clear of the ribbon's sub-menu
// bar by .tp-stage's padding.
const ACL_TOP_PAD = 69
const EQ2_K = 3.9
const EQ2_TOP = 36
const EQ2_ACL = { w: 156.508, h: 27.711, asc: 18.257 }
const EQ2_TAU = { w: 76.267, h: 20.597, asc: 13.763 }
const EQ2_BASELINE_Y = EQ2_TOP + EQ2_ACL.asc * EQ2_K

// Slider card, in viewBox units (scaled with the figure — figRect).
// Lower-left plot quadrant (x < 0, τ < 0 — the curve never goes there),
// below the ACL arrow's fallback place under the τ_val line (lowest at
// τ_val = 10 kPa: y ≈ 594) and above the plot's bottom edge.
const ACL_CARD = { x: TP_FX + 22, y: 604, w: 540, h: 232 }

// ── Stage 8: the α + h Greenland maps ────────────────────────────────
// The plot squeezes to MAPS_PLOTW; the maps panel sits to its right.
// fig2 PNGs (build_twins_grid.py --only maps2) are 760×1369 map-only,
// transparent. Colormap stops = twins_map_fig2.json (matplotlib plasma
// / cividis at 11 stops).
const MAPS_PLOTW = 1000
const MAP2_W = 260
const MAP2_ASPECT = 1369 / 760
const MAPS_PAD = 18
const MAPS_GAP = 26
const MAP2_TITLE_H = 46
const MAPS_CBAR_GAP = 22
const MAPS_PANEL_W = 2 * MAPS_PAD + 2 * MAP2_W + MAPS_GAP
const MAPS_PANEL_H = MAPS_PAD + MAP2_TITLE_H + MAP2_W * MAP2_ASPECT + MAPS_CBAR_GAP + 16 + 44 + MAPS_PAD
const MAPS2 = [
  {
    key: 'alpha',
    url: mediaUrl('ch01/alpha_map_fig2.png'),
    title: 'Along-flow slope',
    sym: 'α',
    unit: '[°]',
    vmax: 1,
    stops: ['#0d0887', '#41049d', '#6a00a8', '#8f0da4', '#b12a90', '#cc4778',
      '#e16462', '#f2844b', '#fca636', '#fcce25', '#f0f921'],
    ticks: [
      { v: 0, label: '0' }, { v: 0.25, label: '' }, { v: 0.5, label: '0.5' },
      { v: 0.75, label: '' }, { v: 1, label: '1.0' },
    ],
  },
  {
    key: 'h',
    url: mediaUrl('ch01/h_map_fig2.png'),
    title: 'Ice thickness',
    sym: 'h',
    unit: '[m]',
    vmax: 3400,
    stops: ['#00224e', '#083370', '#35456c', '#4f576c', '#666970', '#7d7c78',
      '#948e77', '#aea371', '#c8b866', '#e5cf52', '#fee838'],
    ticks: [
      { v: 0, label: '0' }, { v: 1000, label: '1000' },
      { v: 2000, label: '2000' }, { v: 3000, label: '3000' },
    ],
  },
] as const

// ─────────────────────── data ─────────────────────────────────────────
interface Run {
  h: number
  alpha_deg: number
  gamma: number
  ell_m: number
  xscale_m: number
  tauscale_kpa: number
  delta: number
  max_tau_kpa: number
  dl_m: number | null
  x_km: number[]
  tau_kpa: number[]
}
interface TheoryData {
  n: number
  lam: number
  vmax_kpa: number
  hero: Run
  sweep: { x_km: number[]; levels: number[]; curves: number[][] }
  analytic: {
    up_x_km: number[]; up_kpa: number[]
    mid_x_km: number[]; mid_kpa: number[]
    dn_x_km: number[]; dn_kpa: number[]
  }
  ensemble: Run[]
  kappa: { tau: number; dl: number }
  acl?: { tau_val_kpa: number; acl_m: number; onset_km: number; x_cross_km: number }
  master: {
    xhat_up: number[]; tauhat_up: number[]
    xfrac_patch: number[]; tauhat_patch: number[]
    xhat_dn: number[]; tauhat_dn: number[]
  }
}

const data = ref<TheoryData | null>(null)
const vmaxKpa = computed(() => data.value?.vmax_kpa ?? 250)
const heroH = computed(() => data.value?.hero.h ?? 1000)
const patchHalfKm = computed(() => (data.value?.hero.ell_m ?? 10000) / 2 / 1e3)

// ── The hero's velocity perturbation u'(x) (parabolic inside
// the patch, exponential decay outside) — the paper's 1-D solution,
// eq (66) (Appendix B), at the hero parameters, n = 1:
//   x ≤ 0      u'/u'_0 = exp(n^{n/(n+1)} x/[x])
//   0 ≤ x ≤ ℓ  (u' − u'_max)/((ρgαℓ/4B)^n ℓ) = −2^n/(n+1) |x/ℓ − 1/2|^{n+1}
//   x ≥ ℓ      u'/u'_0 = exp(−n^{n/(n+1)} (x − ℓ)/[x])
// with [u] = [x](ρgαℓ/4B)^n (eq 18), u'_0 = [u](1/n)^{n/(n+1)} (eq 40),
// u'_max = [u]((1/n)^{n/(n+1)} + 1/(2(n+1)δ)) (eq 63), δ = [x]/ℓ (eq 23).
// Hero (h 1 km, α 0.5°, γ 0.1, ℓ 10 km): u'_0 ≈ 143, u'_max ≈ 220 m/yr —
// the Elmer/Ice hero's depth-averaged u − u_∞ peaks at 221 m/yr.
// x is measured from the patch onset (the paper's convention); the plot
// axis is x − ℓ/2.
const B_N1 = 2e14                  // Pa s — Table 1: B⁻ⁿ = 5.0e−15 for n = 1
const SEC_PER_YR = 365.25 * 86400
const heroVel = computed<{ xKm: number[]; u: number[] } | null>(() => {
  const d = data.value
  if (!d) return null
  const n = 1
  const ell = d.hero.ell_m
  const xs = d.hero.xscale_m
  const delta = xs / ell
  const stressRatio = Math.pow((d.hero.tauscale_kpa * 1e3) / B_N1, n) // (ρgαℓ/4B)^n
  const uScale = xs * stressRatio
  const u0 = uScale * Math.pow(1 / n, n / (n + 1))
  const uMax = uScale * (Math.pow(1 / n, n / (n + 1)) + 1 / (2 * (n + 1) * delta))
  const lam = Math.pow(n, n / (n + 1))
  const xKm: number[] = []
  const u: number[] = []
  for (let X = -HALF_KM; X <= HALF_KM + 1e-9; X += 0.1) {
    const x = X * 1e3 + ell / 2
    let v: number
    if (x <= 0) v = u0 * Math.exp((lam * x) / xs)
    else if (x <= ell) {
      v = uMax - stressRatio * ell * (Math.pow(2, n) / (n + 1)) * Math.pow(Math.abs(x / ell - 0.5), n + 1)
    } else v = u0 * Math.exp((-lam * (x - ell)) / xs)
    xKm.push(X)
    u.push(v * SEC_PER_YR)
  }
  return { xKm, u }
})

// ── ACL stage interactive model ────────────────────────────────────────
// The acl stage is EXPLORABLE: sliders drive τ_val, α, h, ℓ and the analytic
// n=1 boundary-layer solution recomputes live (same math as
// build_theory_n1.py — [τ] = ρgαℓ/4, [x] = √(2Bh/C), profile
// exp / linear ramp / −exp, ACL = [x]·ln([τ]/τ_val)). At the untouched
// defaults the plot shows the hero Elmer/Ice run (the sliders' default
// values ARE the hero parameters; the analytic profile matches it to
// within ~2%, so the first slider touch is seamless).
const ACL_RHO = 917.0
const ACL_G = 9.81
const ACL_ETA = 1e14           // n=1 viscosity [Pa s]
const ACL_B = 2 * ACL_ETA     // B = A^(-1/n) with A = 1/(2η)
// The hero run's γ is 0.1; it is also a control (0.1 · 0.5).
const ACL_DEFAULTS = { tauVal: 30, alphaDeg: 0.5, h: 1000, ellKm: 10, gamma: 0.1 }
const aclCtl = reactive({ ...ACL_DEFAULTS })
function resetAclCtl(): void {
  Object.assign(aclCtl, ACL_DEFAULTS)
}
const aclDirty = computed(
  () =>
    aclCtl.tauVal !== ACL_DEFAULTS.tauVal ||
    aclCtl.alphaDeg !== ACL_DEFAULTS.alphaDeg ||
    aclCtl.h !== ACL_DEFAULTS.h ||
    aclCtl.ellKm !== ACL_DEFAULTS.ellKm ||
    aclCtl.gamma !== ACL_DEFAULTS.gamma,
)

// Analytic scales for the current slider values (n = 1).
const aclModel = computed(() => {
  const h = aclCtl.h
  const ellM = aclCtl.ellKm * 1000
  const alphaRad = (aclCtl.alphaDeg * Math.PI) / 180
  // C_b = γ·2η/h; ū_b/ū = 1/(1 + (2A/3)·h·C_b) = 1/(1 + 2γ/3) for n=1
  // — so [x] = h·√(2/γ + 4/3): γ = 0.5 halves the boundary layer.
  const gamma = aclCtl.gamma
  const cB = (gamma * 2 * ACL_ETA) / h
  const c = cB / (1 + (2 * gamma) / 3)
  const xscaleM = Math.sqrt((2 * ACL_B * h) / c)
  const tauscaleKpa = (ACL_RHO * ACL_G * alphaRad * ellM) / 4 / 1e3
  const halfKm = aclCtl.ellKm / 2
  const hasCross = tauscaleKpa > aclCtl.tauVal
  const aclM = hasCross ? xscaleM * Math.log(tauscaleKpa / aclCtl.tauVal) : null
  return {
    xscaleM,
    tauscaleKpa,
    halfKm,
    hasCross,
    aclM,
    onsetKm: -halfKm,
    crossKm: aclM !== null ? -halfKm - aclM / 1e3 : null,
  }
})

// Stage-7 display values: JSON (hero) until a slider moves, analytic
// after. Everything downstream (τ_val line, band, drop lines, arrow,
// label, curve) reads these.
const aclActive = computed(() => props.stage >= S.acl && aclDirty.value)
const aclTauVal = computed(() =>
  aclActive.value ? aclCtl.tauVal : data.value?.acl?.tau_val_kpa ?? 30,
)
const aclOnsetKm = computed(() =>
  aclActive.value ? aclModel.value.onsetKm : data.value?.acl?.onset_km ?? -5,
)
const aclCrossKm = computed(() =>
  aclActive.value
    ? aclModel.value.crossKm ?? -40
    : data.value?.acl?.x_cross_km ?? -13.7,
)
const aclHasCross = computed(() =>
  aclActive.value ? aclModel.value.hasCross : true,
)
const aclKmLabel = computed(() => {
  const m = aclActive.value ? aclModel.value.aclM ?? 0 : data.value?.acl?.acl_m ?? 8700
  return (m / 1e3).toFixed(1)
})
const aclHalfKm = computed(() =>
  aclActive.value ? aclModel.value.halfKm : patchHalfKm.value,
)
// The measurement arrow sits ABOVE the stress curve (the director found
// it a little distracting under it): ACL_ARROW_GAP over the
// curve's peak at the patch onset, the estimate on a plate right above
// the arrow, the drop lines reaching up from the τ_val line. The peak
// is [τ] once a slider has moved, the hero's max until then. When the
// plate would no longer fit under the plot's top edge (a peak within
// ~500 kPa of the 800 kPa frame — α AND ℓ near their maxima) the pair
// falls back under the τ_val line, where the upstream plot is empty.
const ACL_PLATE_H = 58
const ACL_ARROW_GAP = 46
const ACL_PLATE_GAP = 12
const aclPeakKpa = computed(() =>
  aclActive.value ? aclModel.value.tauscaleKpa : data.value?.hero.max_tau_kpa ?? 192,
)
const aclAbove = computed(
  () =>
    yCurve(aclPeakKpa.value) - ACL_ARROW_GAP - ACL_PLATE_GAP - ACL_PLATE_H >= curveTop.value + 8,
)
const aclArrowY = computed(() =>
  aclAbove.value
    ? yCurve(aclPeakKpa.value) - ACL_ARROW_GAP
    : yCurve(aclTauVal.value) + 14 + ACL_PLATE_H + ACL_PLATE_GAP,
)
const aclText = computed(() => `ACL ≈ ${aclKmLabel.value} km`)
// The plate: centered on the arrow, clamped inside the plot box. Its
// width is estimated from the text — EB Garamond at 42 units sets
// "ACL ≈ 8.7 km" 243 units wide; each further digit adds ~21.
const aclPlate = computed(() => {
  const w = 243 + 21 * (aclText.value.length - 12) + 40
  const cx = (xDimClamped(aclCrossKm.value) + xDim(aclOnsetKm.value)) / 2
  const x = Math.max(FX + 8, Math.min(FX + tw.plotW - w - 8, cx - w / 2))
  return { x, y: aclArrowY.value - ACL_PLATE_GAP - ACL_PLATE_H, w }
})

// The ACL can walk off the ±40 km window at extreme slider values —
// clamp its screen x to the plot edge (the label keeps the true km).
function xDimClamped(xKm: number): number {
  return xDim(Math.max(-tw.halfKm, Math.min(tw.halfKm, xKm)))
}

// Analytic profile path for the current slider values.
const aclAnalyticPath = computed<string>(() => {
  const m = aclModel.value
  const halfM = m.halfKm * 1e3
  const xs: number[] = []
  const ys: number[] = []
  for (let xKm = -HALF_KM; xKm <= HALF_KM + 1e-9; xKm += 0.2) {
    const xM = xKm * 1e3
    let tau: number
    if (xM < -halfM) {
      tau = m.tauscaleKpa * Math.exp((xM + halfM) / m.xscaleM)
    } else if (xM <= halfM) {
      tau = m.tauscaleKpa * (1 - (2 * (xM + halfM)) / (2 * halfM))
    } else {
      tau = -m.tauscaleKpa * Math.exp(-(xM - halfM) / m.xscaleM)
    }
    xs.push(xKm)
    ys.push(tau)
  }
  return pathFrom(xs, ys, xDim, yCurve)
})

// The ACL stage's axis limits are FIXED — slider moves
// must not rescale the plot. ±ACL_YMAX_KPA is the director's range
// (the y axis of the ACL slider page runs from −400 to 400);
// the strongest curve the sliders can produce (α=1.0°, ℓ=20 km → [τ] ≈
// 785 kPa) is clipped at the frame (tp-curveclip) rather than rescaling.
const ACL_YMAX_KPA = 400

// Profile-display subset (paper fig-4a filter δ ≤ 0.3): all 36 runs.
const ensembleRuns = computed<Run[]>(() =>
  (data.value?.ensemble ?? []).filter((r) => r.delta <= 0.3),
)

// ── interactive legend filter (ensemble → log-log) ──
// Hover previews; CLICK pins. Pins combine across
// columns (h=300 AND α=0.1), click again releases, clicking another
// value in the same column replaces. Hover overrides its own column
// while the pointer is down the legend.
type FilterKey = 'h' | 'alpha' | 'gamma'
const hoverFilter = ref<{ key: FilterKey; value: number } | null>(null)
const pinned = reactive<Partial<Record<FilterKey, number>>>({})
function togglePin(key: FilterKey, value: number): void {
  if (pinned[key] === value) delete pinned[key]
  else pinned[key] = value
}
function effFilter(): Partial<Record<FilterKey, number>> {
  const eff: Partial<Record<FilterKey, number>> = { ...pinned }
  const h = hoverFilter.value
  if (h) eff[h.key] = h.value
  return eff
}
function runMatches(r: Run): boolean {
  const eff = effFilter()
  if (eff.h !== undefined && r.h !== eff.h) return false
  if (eff.alpha !== undefined && r.alpha_deg !== eff.alpha) return false
  if (eff.gamma !== undefined && r.gamma !== eff.gamma) return false
  return true
}
function hasFilter(): boolean {
  return hoverFilter.value !== null || Object.keys(pinned).length > 0
}
function runOpacity(r: Run): number {
  if (!hasFilter()) return 0.85
  return runMatches(r) ? 1 : 0.06
}

// ─────────────────────── tweened scalars ──────────────────────────────
const tw = reactive({
  fieldA: 0,      // field image alpha
  fieldShift: 0,  // px the field row slides down (field stage; less on the wipe)
  schemA: 0,      // fig-1 schematic overlay (auto on the field stage)
  wipeT: 0,       // 0..1 depth-average wipe (field consumed bed→top)
  stokesA: 0,     // eq (1) in the reserved area (field stage → the wipe)
  govA: 0,        // eq (7), the SSA, in the reserved area (derivation)
  dragA: 1,       // eq (7)'s basal-drag term (0 inside the patch)
  cGap: 0,        // 0 = eq (7) as typeset, 1 = the drag gap closed
  braceA: 0,      // under-brace term anatomy
  gravDim: 0,     // 1 = gravity brace dimmed (layers: membrane ↔ drag)
  zonesA: 0,      // in-plot patch edges + zone words + C reminders
  uPatchA: 0,     // row B: patch-interior velocity (eq 66, middle)
  uBlA: 0,        // row B: boundary-layer velocity (eq 66, top)
  tauUA: 0,       // row B: the stress–velocity relation
  velA: 0,        // u' curve + its right-hand axis (violet)
  curveA: 0,      // hero curve (gold)
  axesA: 0,       // curve axes chrome
  bandPatch: 0,
  bandUp: 0,      // (unused — the zones fade instead)
  bandDn: 0,
  outerDim: 0,    // 1 = everything outside the patch faded (the patch beats)
  patchDim: 0,    // 1 = everything inside the patch faded (the boundary-layer beats)
  halfKm: 40,     // the plot's x half-range [km] (30 on the derivation beats)
  anaMidA: 0,     // eq (12) + its dashed overlay
  anaUpA: 0,      // eq (43) upstream + dashed overlays (up + down)
  cardMid: 0,     // 1 = the patch solution on its CARD (plot centre, large); 0 = in the patch band
  cardUp: 0,      // 1 = the two boundary-layer rows on their CARD; 0 = in their zones
  ensA: 0,
  ymaxK: 310,     // curve y half-range [kPa]
  collapse: 0,    // 0 = dimensional, 1 = non-dimensional
  masterA: 0,
  loglogA: 0,
  aclA: 0,        // τ_val line + ACL measurement
  mapsA: 0,       // stage 8: α + h Greenland maps, top-right in-figure
  topPad: 0,      // extra plot-top inset (derivation: the equation area)
  plotW: 1490,    // plot width — squeezed left on the log-log stage
  colT: 0,        // legend + scales/master eqs: 0 in the plot, 1 in the log-log column
  bgA: 1,         // chalkboard backdrop (transparent during seam entry)
})

type Targets = Partial<Record<keyof typeof tw, number>>
type Ease = (t: number) => number

let rafId: number | null = null
let anims: Array<{
  key: keyof typeof tw
  from: number
  to: number
  t0: number | null
  dur: number
  ease: Ease
  /** Fires once when this tween completes (never if superseded). */
  done?: () => void
}> = []

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
// Gentler than cubic — used for the long depth-average wipe so the
// sweep reads as one smooth continuous motion.
function easeInOutSine(t: number): number {
  return -(Math.cos(Math.PI * t) - 1) / 2
}

function animateTo(
  targets: Targets, dur = 700, ease: Ease = easeInOutCubic, done?: () => void,
): void {
  let carrier = false
  for (const [k, v] of Object.entries(targets) as Array<[keyof typeof tw, number]>) {
    anims = anims.filter((a) => a.key !== k)
    if (Math.abs(tw[k] - v) < 1e-4) continue
    anims.push({ key: k, from: tw[k], to: v, t0: null, dur, ease, done: carrier ? undefined : done })
    carrier = true
  }
  // Nothing to tween (already there): the follow-up runs straight away.
  if (!carrier && done) later(0, done)
  if (anims.length && rafId === null) rafId = requestAnimationFrame(tick)
}

function tick(now: number): void {
  for (const a of anims) {
    if (a.t0 === null) a.t0 = now
    const t = Math.min(1, (now - a.t0) / a.dur)
    tw[a.key] = a.from + (a.to - a.from) * a.ease(t)
  }
  const finished = anims.filter((a) => a.t0 !== null && now - a.t0 >= a.dur)
  anims = anims.filter((a) => a.t0 !== null && now - a.t0 < a.dur)
  rafId = anims.length ? requestAnimationFrame(tick) : null
  for (const a of finished) a.done?.()
}

function setInstant(targets: Targets): void {
  for (const [k, v] of Object.entries(targets) as Array<[keyof typeof tw, number]>) {
    anims = anims.filter((a) => a.key !== k)
    tw[k] = v
  }
}

// ─────────────────────── stage dispatch ───────────────────────────────
// Stages = Ch.1 beats from ch1First('field') (config/ch1Beats.ts):
//   field            Stokes field + auto schematic; eq (1) ABOVE the
//                    domain, Weertman sliding under the bed (τ_b = 0 on
//                    the patch), UPSTREAM / DOWNSTREAM over the layers
//   average          depth-average WIPE → gold 1-D curve; eq (7) takes
//                    eq (1)'s place in the reserved area; three zones
//   patch-govern     patch lit; eq (7)'s drag term drops, gap closes
//   patch-velocity   row B: patch velocity (eq 66); u' curve, right axis
//   patch-stress     row B: + the stress–velocity relation
//   patch-solution   eq (12) LARGE on a card at the plot's centre;
//                    it shrinks into the patch band — with
//                    its dashed overlay — on layers-govern
//   layers-govern    outer zones lit; drag term returns (full eq 7)
//   layers-velocity  row B: boundary-layer velocity (eq 66) + relation
//   layers-solution  eq (43)'s two rows LARGE on a card;
//                    they shrink into the up/downstream zones — with
//                    their dashed overlays — on summary
//   ensemble         the n = 1 ensemble, dimensional (full height again)
//   collapse         nondim COLLAPSE + master curve + scales eqs
//   loglog           figure slides left; square log-log cards
//   acl / maps       ACL (explorable) · + the α/h Greenland maps
const BASE: Record<keyof typeof tw, number> = {
  fieldA: 0, fieldShift: 0, schemA: 0, wipeT: 0,
  stokesA: 0, govA: 0, dragA: 1, cGap: 0, braceA: 0, gravDim: 0, zonesA: 0,
  uPatchA: 0, uBlA: 0, tauUA: 0, velA: 0,
  curveA: 0, axesA: 0,
  bandPatch: 0, bandUp: 0, bandDn: 0, outerDim: 0, patchDim: 0, halfKm: 40, anaMidA: 0, anaUpA: 0, cardMid: 0, cardUp: 0,
  ensA: 0, ymaxK: 310, collapse: 0, masterA: 0, loglogA: 0, aclA: 0,
  mapsA: 0,
  topPad: 0, plotW: 1490, colT: 0, bgA: 1,
}

function stageTargets(s: number): Targets {
  const t: Targets = { ...BASE }
  if (s === S.field) { t.fieldA = 1; t.fieldShift = 150; t.schemA = 1; t.stokesA = 1 }
  if (s >= S.average) t.wipeT = 1
  // The derivation: the governing equation NEVER leaves the reserved
  // area above the plot (the director's rule: the governing equation
  // stays up through the whole derivation).
  if (isDerivation(s)) {
    t.curveA = 1; t.axesA = 1; t.govA = 1; t.zonesA = 1
    t.topPad = DERIV_TOP_PAD; t.fieldShift = DERIV_FIELD_SHIFT
  }
  if (s === S.average) { t.fieldA = 1; t.braceA = 1 }
  // Inside the patch C = 0: the drag term is gone from eq (7).
  // The director's beat order: govern → velocity profile + the τ–u
  // relation → the τxx solution, inside the patch then in the boundary
  // layers; the zone NOT being solved FADES; no velocity equation, no
  // blue rectangles, gravity never dimmed; the x-range zooms to ±30 km.
  if (s >= S.patchGovern && s <= S.summary) t.halfKm = DERIV_HALF_KM
  if (s >= S.patchGovern && s <= S.patchSolution) { t.bandPatch = 1; t.dragA = 0; t.cGap = 1; t.outerDim = 1 }
  if (s === S.patchGovern) t.braceA = 1
  if (s >= S.patchVelocity && s <= S.layersSolution) t.velA = 1
  if (s >= S.patchVelocity && s <= S.patchSolution) t.tauUA = 1
  if (s >= S.patchSolution && s <= S.summary) t.anaMidA = 1
  if (s >= S.layersGovern && s <= S.layersSolution) t.patchDim = 1
  if (s === S.layersGovern) t.braceA = 1
  if (s >= S.layersVelocity && s <= S.layersSolution) t.tauUA = 1
  if (s === S.layersSolution || s === S.summary) t.anaUpA = 1
  // The solution CARDS (the director's request): each solution's first beat
  // shows it large on a card; the next beat places it in its zone.
  if (s === S.patchSolution) t.cardMid = 1
  if (s === S.layersSolution) t.cardUp = 1
  // summary: the stress alone across the domain, nothing faded, no u′,
  // no row B — the three solutions in their zones (then RESULTS).
  if (s >= S.ensemble && s <= S.loglog) { t.axesA = 1; t.ensA = 1; t.ymaxK = ensYmax() }
  if (s === S.collapse || s === S.loglog) { t.collapse = 1; t.masterA = 1 }
  if (s === S.collapse) t.topPad = COLLAPSE_TOP_PAD
  if (s === S.loglog) { t.loglogA = 1; t.plotW = LOGLOG_PLOTW }
  // The legend + the scales/master equations move into the log-log
  // column with the squeeze and STAY there while they fade out on the
  // ACL stage (never snap a fading legend across the plot).
  if (s >= S.loglog) t.colT = 1
  if (s >= S.acl) {
    t.curveA = 1; t.axesA = 1; t.aclA = 1; t.ymaxK = ACL_YMAX_KPA
    // The equation band above the plot.
    t.topPad = ACL_TOP_PAD
  }
  // Maps: the ACL stays; two Greenland maps — along-flow
  // slope α and thickness h — the bridge from the 1-D theory to applying
  // the ACL across the sheet. They no longer sit
  // over the plot — the plot squeezes left (as on the log-log stage) and
  // the maps land beside it.
  if (s === S.maps) { t.mapsA = 1; t.plotW = MAPS_PLOTW }
  return t
}

function ensYmax(): number {
  const runs = ensembleRuns.value
  if (!runs.length) return 500
  let m = 0
  for (const r of runs) m = Math.max(m, r.max_tau_kpa)
  return Math.ceil((m * 1.08) / 100) * 100
}

let staggerTimers: number[] = []
function clearStagger(): void {
  for (const id of staggerTimers) window.clearTimeout(id)
  staggerTimers = []
}
function later(ms: number, fn: () => void): void {
  staggerTimers.push(window.setTimeout(fn, ms))
}

function applyStage(s: number, animate: boolean, from = -1): void {
  clearStagger()
  hoverFilter.value = null
  for (const k of Object.keys(pinned) as FilterKey[]) delete pinned[k]
  // Each visit to the ACL stages starts from the hero defaults.
  if (s < S.acl) resetAclCtl()
  const t = stageTargets(s)
  if (!animate) {
    setInstant(t)
    return
  }
  // The solution cards: arriving on a card beat from before it, the card
  // fades in IN PLACE (its flag snaps to 1 first — never a flight out of
  // the band); leaving a card beat for a stage without the equation, the
  // flag parks to 0 only after the fade (never a flight while fading).
  if (s === S.patchSolution && from < s) setInstant({ cardMid: 1 })
  if (s === S.layersSolution && from < s) setInstant({ cardUp: 1 })
  const park: Targets = {}
  if (t.anaMidA === 0 && tw.cardMid > 0.004) { park.cardMid = 0; delete t.cardMid }
  if (t.anaUpA === 0 && tw.cardUp > 0.004) { park.cardUp = 0; delete t.cardUp }
  if (Object.keys(park).length) later(900, () => setInstant(park))
  if (s === S.field) {
    // Entry: field settles in first; the schematic notations + the
    // Stokes system then fade in AUTOMATICALLY. On the beat 3→4 seam
    // morph the whole panel enters with a TRANSPARENT
    // backdrop over the camera-fit slab: the root Transition's 0.9 s
    // fade IS the field crossfade (same image, same rect — the object
    // never blinks), the chalkboard then dims the surroundings, and the
    // schematic follows.
    const fx = props.entryFx ?? null
    const { schemA: _s, stokesA: _k, ...rest } = t
    if (fx === 'seam') {
      const { bgA: _b, fieldA: _f, fieldShift: _fs, ...restAnim } = rest
      setInstant({ schemA: 0, stokesA: 0, bgA: 0, fieldA: 1, fieldShift: 150 })
      animateTo(restAnim, 700)
      later(1100, () => animateTo({ bgA: 1 }, 900))
      later(2100, () => animateTo({ schemA: 1, stokesA: 1 }, 900))
    } else {
      setInstant({ schemA: 0, stokesA: 0 })
      animateTo(rest, 900)
      later(1000, () => animateTo({ schemA: 1, stokesA: 1 }, 900))
    }
  } else if (s === S.average) {
    // The depth-average WIPE is the stage's content: the gold line
    // consumes the field bed→surface while the gold 1-D curve grows in
    // the space it frees. The Stokes system stays in the reserved area
    // through the sweep, then the SSA replaces it IN PLACE — one
    // crossfade, same baseline (the director's request). Plays on the click that
    // enters this stage (and on a deep link straight here) — never
    // again on back-nav from later stages.
    if (from > S.average) {
      animateTo(t, 900)
      return
    }
    const { wipeT: _w, axesA: _a, govA: _g, braceA: _br, zonesA: _z, ...rest } = t
    // The SSA lands when the sweep ENDS (chained to the tween, not a
    // wall-clock timer — a busy main thread can delay rAF, and the
    // equation must never arrive before the average it describes).
    setInstant({ wipeT: 0, govA: 0, braceA: 0, zonesA: 0 })
    animateTo({ ...rest, axesA: 0, stokesA: 1 }, 600)
    later(700, () => animateTo({ wipeT: 1 }, 5200, easeInOutSine, () => {
      later(100, () => animateTo({ axesA: 1, govA: 1, stokesA: 0, zonesA: 1 }, 900))
      later(900, () => animateTo({ braceA: 1 }, 700))
    }))
  } else if (s === S.patchGovern && from < s) {
    // The patch lights; THEN its basal-drag term leaves eq (7) and the
    // equation closes up around the gap — membrane stress vs gravity.
    const { dragA: _d, cGap: _c, ...rest } = t
    animateTo(rest, 700)
    later(700, () => animateTo({ dragA: 0 }, 700))
    later(1300, () => animateTo({ cGap: 1 }, 900, easeInOutSine))
  } else if (s === S.layersGovern && from < s) {
    // Outer zones light, the patch's row B clears; the gap reopens and
    // the drag term + its brace return; gravity's brace steps back.
    const { dragA: _d, cGap: _c, braceA: _b, cardMid: _cm, ...rest } = t
    animateTo(rest, 700)
    animateTo({ cardMid: 0 }, 900)
    later(500, () => animateTo({ cGap: 0 }, 900, easeInOutSine))
    later(1300, () => animateTo({ dragA: 1, braceA: 1 }, 700))
  } else if ((s === S.patchVelocity || s === S.layersVelocity) && from === s - 1) {
    // The braces clear, row B's velocity solution lands in their place,
    // and the u' curve follows its equation onto the plot.
    const { tauUA, velA, ...rest } = t
    animateTo(rest, 450)
    later(350, () => animateTo({ tauUA }, 700))
    later(900, () => animateTo({ velA }, 1100))
  } else if (s === S.collapse) {
    // Collapse first; the master curve + its equations land after.
    const { masterA: _m, ...rest } = t
    animateTo(rest, 1700)
    later(1750, () => animateTo({ masterA: 1 }, 600))
  } else if (s === S.loglog) {
    // tw.plotW squeezes the collapsed figure into the left ~half at
    // FULL height (the director wanted no letterboxed blank space); the
    // log-log cards fade in as it settles.
    const { loglogA: _l, ...rest } = t
    animateTo(rest, 1100)
    later(700, () => animateTo({ loglogA: 1 }, 700))
  } else if (s === S.acl) {
    // Hero curve returns, then the τ_val line + ACL measurement draw.
    const { aclA: _c, ...rest } = t
    animateTo(rest, 900)
    later(1000, () => animateTo({ aclA: 1 }, 1100))
  } else if (s === S.maps && from === S.acl) {
    // ACL → maps: the plot squeezes left (same 1.1 s as the log-log
    // squeeze) while the maps arrive beside it and the sliders bow out.
    animateTo(t, 1100)
  } else {
    animateTo(t, 800)
  }
}

watch(
  () => props.stage,
  (s, old) => applyStage(s, true, old ?? -1),
)

// Warm-mount reveal: the stage prop is already 0 while hidden, so the
// unhide edge (beat 3→4) must trigger the entry staging itself.
watch(
  () => props.hidden,
  (h, old) => {
    if (old && !h) applyStage(props.stage, true)
  },
)

// Re-apply once data lands (ymaxK + ACL geometry depend on it). The
// wipe stage re-runs its animation — a deep link straight to the
// depth-averaging beat should still show the wipe. The field stage needs
// no data (image field + static schematic) — re-applying would CLOBBER
// the seam entry's staging mid-flight.
watch(data, () => {
  if (props.stage >= S.average) applyStage(props.stage, props.stage === S.average)
})

onMounted(() => {
  // Stage FIRST — the seam entry must start the instant the panel
  // mounts (backdrop transparent over the camera-fit slab), never
  // waiting on the data fetch. Deep-link mounts land animated for the
  // two stages whose motion IS the content (entry schematic + wipe);
  // end-state for the rest.
  applyStage(props.stage, props.stage === S.average || props.stage === S.field)
  fetch(mediaUrl('ch01/theory_n1.json'))
    .then(async (r) => {
      if (r.ok) data.value = (await r.json()) as TheoryData
    })
    .catch(() => {
      // Panel renders its chrome regardless; curves appear when data does.
    })
})

onBeforeUnmount(() => {
  clearStagger()
  if (rafId !== null) cancelAnimationFrame(rafId)
})

// ─────────────────────── coordinate mapping ───────────────────────────
// The curve band rides the wipe: its top edge hangs just below the
// sweep line, so the 1-D curve visibly GROWS out of the wiped field.
// sweepLineY is in the field group's frame; sweepAbsY adds its shift.
const sweepLineY = computed(() => FY + FH - tw.wipeT * FH)
const sweepAbsY = computed(() => sweepLineY.value + tw.fieldShift)
const curveTop = computed(() => {
  const base = CURVE_TOP_FULL + tw.topPad
  if (tw.ensA > 0.004 || tw.wipeT >= 0.999 || tw.fieldA < 0.004) return base
  return Math.max(base, sweepAbsY.value + 46)
})
const curveBottom = CURVE_BOTTOM
const cbX = computed(() => FX + tw.plotW + 16)

// ACL stages: the equation pair centered over the FULL-width plot and
// held there on the maps stage too (the squeezed plot slides under the
// ACL equation; the max-stress one then rides above the maps panel) —
// equations never move once they land.
const ACL_EQ_GAP = 130
const aclEqs = (() => {
  const aclW = EQ2_ACL.w * EQ2_K
  const tauW = EQ2_TAU.w * EQ2_K
  const x0 = FX + (TP_FW - (aclW + ACL_EQ_GAP + tauW)) / 2
  return { aclX: x0, tauX: x0 + aclW + ACL_EQ_GAP }
})()

// Stage-8 maps panel: rides the plot's right edge (so it glides in with
// the squeeze), vertically centered on the plot box.
const mapsPanel = computed(() => ({
  x: FX + tw.plotW + 34,
  y: curveTop.value + (curveBottom - curveTop.value - MAPS_PANEL_H) / 2,
  w: MAPS_PANEL_W,
  h: MAPS_PANEL_H,
}))
const mapsCbarY = computed(
  () => mapsPanel.value.y + MAPS_PAD + MAP2_TITLE_H + MAP2_W * MAP2_ASPECT + MAPS_CBAR_GAP,
)

// The SVG's rendered viewBox → screen mapping (preserveAspectRatio
// meet). HTML overlays that belong to the figure (the ACL slider card)
// are positioned + scaled through this, never from the window size
// (the director's request).
const svgRef = ref<SVGSVGElement | null>(null)
const figRect = reactive({ ox: 0, oy: 0, s: 1 })
function measureFig(): void {
  const el = svgRef.value
  if (!el) return
  const r = el.getBoundingClientRect()
  if (r.width < 1 || r.height < 1) return
  const s = Math.min(r.width / VW, r.height / VH)
  figRect.s = s
  figRect.ox = r.left + (r.width - VW * s) / 2
  figRect.oy = r.top + (r.height - VH * s) / 2
}
let figObserver: ResizeObserver | null = null
onMounted(() => {
  measureFig()
  if (svgRef.value) {
    figObserver = new ResizeObserver(measureFig)
    figObserver.observe(svgRef.value)
  }
  window.addEventListener('resize', measureFig)
})
onBeforeUnmount(() => {
  figObserver?.disconnect()
  window.removeEventListener('resize', measureFig)
})

function xDim(xKm: number): number {
  return FX + ((xKm + tw.halfKm) / (2 * tw.halfKm)) * tw.plotW
}
const xTicksKm = computed(() => X_TICKS_KM.filter((t) => Math.abs(t) <= tw.halfKm + 1e-6))
/** The derivation's fades: the zone not being solved steps back. */
const dimOuter = computed(() => 1 - 0.8 * tw.outerDim)
const dimPatch = computed(() => 1 - 0.8 * tw.patchDim)
/** In-zone equations never wider than their zone (less a margin). */
// ── The solution cards ──
// Card pose = the equation at K_CARD, centred on the plot (the two
// boundary-layer rows stacked, left-aligned); zone pose = where it
// rides on the summary beat. tw.cardMid / tw.cardUp lerp the <image>
// box between them, so the NEXT beat is one shrinking flight.
const K_CARD = 5.0
const CARD_PAD_X = 44
const CARD_PAD_Y = 30
/** Between the two boundary-layer rows: each on its own plate (pad above
 *  and below) + 18 px between the plates. */
const CARD_ROW_GAP = 2 * CARD_PAD_Y + 18
type EqBox = { href: string; x: number; y: number; width: number; height: number }
function lerpBox(a: EqBox, b: EqBox, t: number): EqBox {
  return {
    href: a.href,
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    width: a.width + (b.width - a.width) * t,
    height: a.height + (b.height - a.height) * t,
  }
}
const plotMidY = computed(() => (curveTop.value + curveBottom) / 2)
// the card's entry pops a touch (0.94 → 1) with its fade
const kCardMid = computed(() => K_CARD * (0.94 + 0.06 * tw.anaMidA))
const kCardUp = computed(() => K_CARD * (0.94 + 0.06 * tw.anaUpA))
const midPose = computed<EqBox>(() => lerpBox(
  eqAt('tau_patch_v2_c', kMid.value, xDim(0), curveTop.value + 16, 'center', 'top'),
  eqAt('tau_patch_v2_c', kCardMid.value, EQ_CX, plotMidY.value, 'center', 'middle'),
  tw.cardMid,
))
/** The two boundary-layer plates share one width (the wider row's). */
const cardWUp = computed(() =>
  Math.max(CH1_EQ.tau_bl_up_v3_c.w, CH1_EQ.tau_bl_dn_v3_c.w) * kCardUp.value + 2 * CARD_PAD_X)
const upPose = computed<EqBox>(() => {
  const k = kCardUp.value
  const w = Math.max(CH1_EQ.tau_bl_up_v3_c.w, CH1_EQ.tau_bl_dn_v3_c.w) * k
  const h = CH1_EQ.tau_bl_up_v3_c.h * k
  return lerpBox(
    eqAt('tau_bl_up_v3_c', kUp.value, FX + 30, curveTop.value + 20, 'left', 'top'),
    eqAt('tau_bl_up_v3_c', k, EQ_CX - w / 2, plotMidY.value - CARD_ROW_GAP / 2 - h, 'left', 'top'),
    tw.cardUp,
  )
})
const dnPose = computed<EqBox>(() => {
  const k = kCardUp.value
  const w = Math.max(CH1_EQ.tau_bl_up_v3_c.w, CH1_EQ.tau_bl_dn_v3_c.w) * k
  return lerpBox(
    eqAt('tau_bl_dn_v3_c', kDn.value, FX + tw.plotW - 30, curveTop.value + 20, 'right', 'top'),
    eqAt('tau_bl_dn_v3_c', k, EQ_CX - w / 2, plotMidY.value + CARD_ROW_GAP / 2, 'left', 'top'),
    tw.cardUp,
  )
})
/** The card plate round a set of equation boxes (follows them as they
 *  fly; its opacity is the card flag SQUARED, so it is mostly gone by
 *  mid-flight and never reads as a plate stretched across the plot). */
function cardRect(boxes: EqBox[], minW = 0): { x: number; y: number; width: number; height: number } {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
  for (const b of boxes) {
    x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y)
    x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height)
  }
  return {
    x: x0 - CARD_PAD_X, y: y0 - CARD_PAD_Y,
    width: Math.max(minW, x1 - x0 + 2 * CARD_PAD_X), height: y1 - y0 + 2 * CARD_PAD_Y,
  }
}

const kMid = computed(() =>
  Math.min(K_EQ, (xDim(patchHalfKm.value) - xDim(-patchHalfKm.value) - 14) / CH1_EQ.tau_patch_v2_c.w))
const kUp = computed(() => Math.min(K_EQ, (xDim(-patchHalfKm.value) - FX - 50) / CH1_EQ.tau_bl_up_v3_c.w))
const kDn = computed(() => Math.min(K_EQ, (FX + tw.plotW - xDim(patchHalfKm.value) - 50) / CH1_EQ.tau_bl_dn_v3_c.w))
function yCurve(kpa: number): number {
  const half = (curveBottom - curveTop.value) / 2
  const mid = curveTop.value + half
  return mid - (kpa / tw.ymaxK) * half
}
/** u' [m/yr] → y: zero on the stress zero line, VEL_TOP at the top. */
function yVel(u: number): number {
  const half = (curveBottom - curveTop.value) / 2
  const mid = curveTop.value + half
  return mid - (u / VEL_TOP) * half
}
function yNd(tauHat: number): number {
  const half = (curveBottom - curveTop.value) / 2
  const mid = curveTop.value + half
  return mid - (tauHat / ND_TAU_MAX) * half
}
const zoneMidL = computed(() => FX + ZONE_UP_F * tw.plotW)
const zoneMidR = computed(() => FX + (ZONE_UP_F + ZONE_MID_F) * tw.plotW)
function xNdUp(xh: number): number {
  return FX + ((xh + 6) / 6) * ZONE_UP_F * tw.plotW
}
function xNdMid(xi: number): number {
  return zoneMidL.value + xi * ZONE_MID_F * tw.plotW
}
function xNdDn(xh: number): number {
  return zoneMidR.value + (xh / 6) * (1 - ZONE_UP_F - ZONE_MID_F) * tw.plotW
}
/** The downstream row's size: K_ND, or what its zone holds inside the pads. */
const kNdDn = computed(() =>
  Math.min(K_ND, (FX + tw.plotW - zoneMidR.value - 2 * ND_ZONE_PAD) / CH1_EQ.nd_dn.w))
/** Collapse panel centers (Fig. 4b's three panels). */
const ndZoneCenters = computed(() => [
  (FX + zoneMidL.value) / 2,
  (zoneMidL.value + zoneMidR.value) / 2,
  (zoneMidR.value + FX + tw.plotW) / 2,
])

// ── The SSA (eq 7) in the reserved area, as three registered pieces.
// cGap slides the gravity term left by the drag term's TeX width and
// re-centers the whole line, so closing the gap IS the re-typeset
// equation 2Bh(|u_x|^{1/n−1}u_x)_x + ρghα = 0 (the patch interior).
const ssaShiftMem = computed(() => (SSA_GAP / 2) * tw.cGap)
const ssaShiftGrav = computed(() => (-SSA_GAP / 2) * tw.cGap)
const ssaBraces = computed(() => {
  const k = K_GOV
  const c = CH1_EQ_CUTS_SSA
  const y = BRACE_Y
  return [
    { key: 'mem', label: 'membrane stress', x0: SSA_X0 + SSA_PAD + ssaShiftMem.value,
      x1: SSA_X0 + c.memEnd * k + ssaShiftMem.value, a: tw.braceA },
    { key: 'drag', label: 'basal drag', x0: SSA_X0 + c.dragStart * k + ssaShiftMem.value,
      x1: SSA_X0 + c.dragEnd * k + ssaShiftMem.value, a: tw.braceA * tw.dragA },
    { key: 'grav', label: 'gravity', x0: SSA_X0 + c.gravStart * k + ssaShiftGrav.value,
      x1: SSA_X0 + c.gravEnd * k + ssaShiftGrav.value, a: tw.braceA * (1 - 0.7 * tw.gravDim) },
  ].map((b) => ({ ...b, y }))
})

// Legend home: top-right inside the axes (ensemble + collapse); on the
// log-log stage it GLIDES with the squeeze (tw.colT, same tween) into
// the column's second row, right-aligned, and holds that place while
// it fades out on the ACL stage (switching log-log → ACL
// used to snap the legend across the plot while it was still fading —
// the legend the director saw jumping around).
// The director then saw the legend take a circular path it did not
// need and asked for a direct move — so the start of
// the glide is the FULL-width home (a constant), not the live plot edge
// that the squeeze was moving under it.
// With the bigger nondimensional solution equations the director asked
// for (there was space to fill), the legend's plot home is the BOTTOM-LEFT —
// the upstream curves never dip below zero, so that corner is empty on
// the ensemble and collapse beats — and the downstream solution takes
// the top-right at K_ND. The move to the log-log column is a CUT, not a
// glide across the squeezing plot: the legend fades out at its home and
// in at the column (legFade), its position switching at the midpoint.
const legX = computed(() => (tw.colT < 0.5 ? FX + 22 : LOGLOG_LEG_X))
const legY = computed(() => (tw.colT < 0.5 ? curveBottom - LEGH - 18 : ROW2_Y))
const legFade = computed(() => Math.abs(2 * tw.colT - 1))

// Scales + master equations: top-left in the plot (k 3.4) on the
// collapse stage; on the log-log stage, stacked in the column's second
// row beside the plot's right edge (the scales are the cards' x-axes),
// centered on the legend's band. The template crossfades the two.
const LOGLOG_EQ_BLOCK_H =
  CH1_EQ.scales.h * LOGLOG_EQ_K + 24 + CH1_EQ.master.h * LOGLOG_EQ_K
const LOGLOG_EQ_Y = ROW2_Y + (LEGH - LOGLOG_EQ_BLOCK_H) / 2
const LOGLOG_MASTER_Y = LOGLOG_EQ_Y + CH1_EQ.scales.h * LOGLOG_EQ_K + 24
// Fig. 4b's zone words close their tracking as the plot squeezes
// (DOWNSTREAM at 0.14 em no longer fits its 36 % of a 640-unit plot).
const ndZoneTracking = computed(() => `${(0.14 - 0.07 * tw.colT).toFixed(3)}em`)
/** The zone words never cross the plot's frame: the outer
 *  derivation words hang from the edges, ZONE_WORD_INSET in; the collapse
 *  headers are clamped inside the box by their measured widths. */
const ZONE_WORD_INSET = 14
const zoneWordEls: (SVGTextElement | null)[] = [null, null, null]
const zoneWordW = ref<number[]>([0, 0, 0])
function setZoneWordEl(i: number, el: unknown): void {
  zoneWordEls[i] = (el as SVGTextElement | null) ?? null
}
function measureZoneWords(): void {
  const w = zoneWordEls.map((el) => {
    try { return el?.getComputedTextLength() ?? 0 } catch { return 0 }
  })
  if (w.some((v, i) => Math.abs(v - zoneWordW.value[i]) > 0.5)) zoneWordW.value = w
}
watch([ndZoneTracking, () => tw.collapse > 0.004], () => nextTick(measureZoneWords), { flush: 'post' })
function ndZoneWordX(i: number, c: number): number {
  const half = (zoneWordW.value[i] || 0) / 2
  return Math.min(Math.max(c, FX + ZONE_WORD_INSET + half), FX + tw.plotW - ZONE_WORD_INSET - half)
}
// Fig. 4b's panel labels (zone words) sit ABOVE the collapsed plot.
const ND_ZONE_WORDS = ['upstream', 'patch', 'downstream'] as const
// the talk's coordinate is centred on the patch: x + l/2 and x - l/2 in the boundary layers
const ND_AXIS_EQS = ['ax_nd_up_c', 'ax_nd_mid', 'ax_nd_dn_c'] as const

const yTicksKpa = computed<number[]>(() => {
  const m = tw.ymaxK
  const step = m > 600 ? 400 : m > 320 ? 200 : 100
  const out: number[] = []
  for (let v = -Math.floor(m / step) * step; v <= m; v += step) out.push(v)
  return out
})

// ─────────────────────── curve paths ──────────────────────────────────
function pathFrom(
  xs: number[], ys: number[],
  mapX: (x: number) => number, mapY: (y: number) => number,
): string {
  const parts: string[] = []
  for (let i = 0; i < xs.length; i++) {
    parts.push(`${i === 0 ? 'M' : 'L'} ${mapX(xs[i]).toFixed(1)} ${mapY(ys[i]).toFixed(1)}`)
  }
  return parts.join(' ')
}

// Hero curve: during the wipe, interpolate the partial-average stack at
// level wipeT; once the wipe completes it IS the (denser) hero profile.
// On the explorable ACL stage, slider input swaps in the analytic
// profile for the chosen parameters.
const heroCurvePath = computed<string>(() => {
  if (aclActive.value) return aclAnalyticPath.value
  const d = data.value
  if (!d) return ''
  if (tw.wipeT >= 0.999) {
    return pathFrom(d.hero.x_km, d.hero.tau_kpa, xDim, yCurve)
  }
  const { x_km, levels, curves } = d.sweep
  const t = Math.min(Math.max(tw.wipeT, 0), 1)
  const fi = t * (levels.length - 1)
  const i0 = Math.floor(fi)
  const i1 = Math.min(levels.length - 1, i0 + 1)
  const f = fi - i0
  const ys = curves[i0].map((v, k) => v + (curves[i1][k] - v) * f)
  return pathFrom(x_km, ys, xDim, yCurve)
})

const anaMidPath = computed<string>(() => {
  const d = data.value
  if (!d) return ''
  return pathFrom(d.analytic.mid_x_km, d.analytic.mid_kpa, xDim, yCurve)
})
const anaUpPath = computed<string>(() => {
  const d = data.value
  if (!d) return ''
  return pathFrom(d.analytic.up_x_km, d.analytic.up_kpa, xDim, yCurve)
})
// The downstream mirror (eq 43, bottom row) — dashed overlay only; its
// equation stays off screen (the director's choice: end on the patch + upstream pair).
const anaDnPath = computed<string>(() => {
  const d = data.value
  if (!d) return ''
  return pathFrom(d.analytic.dn_x_km, d.analytic.dn_kpa, xDim, yCurve)
})
const velPath = computed<string>(() => {
  const v = heroVel.value
  if (!v) return ''
  return pathFrom(v.xKm, v.u, xDim, yVel)
})

// Ensemble runs: every point owns a dimensional screen position and a
// non-dimensional one; tw.collapse lerps between them.
interface Pt { dx: number; dyKpa: number; nzone: 0 | 1 | 2; nxv: number; nyHat: number }
const runPts = computed<Pt[][]>(() => {
  const d = data.value
  if (!d) return []
  return ensembleRuns.value.map((r) => {
    const halfEll = r.ell_m / 2
    return r.x_km.map((xk, i) => {
      const xm = xk * 1e3
      const tau = r.tau_kpa[i]
      let nzone: 0 | 1 | 2
      let nxv: number
      if (xm < -halfEll) {
        nzone = 0
        nxv = Math.max(-7.5, (xm + halfEll) / r.xscale_m)
      } else if (xm <= halfEll) {
        nzone = 1
        nxv = (xm + halfEll) / r.ell_m
      } else {
        nzone = 2
        nxv = Math.min(7.5, (xm - halfEll) / r.xscale_m)
      }
      return { dx: xDim(xk), dyKpa: tau, nzone, nxv, nyHat: tau / r.tauscale_kpa }
    })
  })
})

function ndX(p: Pt): number {
  return p.nzone === 0 ? xNdUp(p.nxv) : p.nzone === 1 ? xNdMid(p.nxv) : xNdDn(p.nxv)
}

const runPaths = computed<string[]>(() => {
  const c = tw.collapse
  return runPts.value.map((pts) => {
    const parts: string[] = []
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i]
      const x = p.dx + (ndX(p) - p.dx) * c
      const y = yCurve(p.dyKpa) + (yNd(p.nyHat) - yCurve(p.dyKpa)) * c
      parts.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`)
    }
    return parts.join(' ')
  })
})

// Sparse α marker glyphs riding each curve (fig-4 encoding: shape = α).
function markerPathAt(x: number, y: number, alphaDeg: number, s: number): string {
  if (alphaDeg === 0.1) {
    return `M ${x - s} ${y} a ${s} ${s} 0 1 0 ${2 * s} 0 a ${s} ${s} 0 1 0 ${-2 * s} 0`
  }
  if (alphaDeg === 0.5) {
    return `M ${x} ${y - s} L ${x + s} ${y} L ${x} ${y + s} L ${x - s} ${y} Z`
  }
  return `M ${x} ${y - s} L ${x + s} ${y + s} L ${x - s} ${y + s} Z`
}

const runMarkers = computed<string[][]>(() => {
  const c = tw.collapse
  return runPts.value.map((pts, ri) => {
    const r = ensembleRuns.value[ri]
    const out: string[] = []
    const step = Math.max(12, Math.floor(pts.length / 9))
    for (let i = step; i < pts.length - 2; i += step) {
      const p = pts[i]
      const x = p.dx + (ndX(p) - p.dx) * c
      const y = yCurve(p.dyKpa) + (yNd(p.nyHat) - yCurve(p.dyKpa)) * c
      out.push(markerPathAt(x, y, r.alpha_deg, 6))
    }
    return out
  })
})

const masterPath = computed<string>(() => {
  const d = data.value
  if (!d) return ''
  const m = d.master
  const a = pathFrom(m.xhat_up, m.tauhat_up, xNdUp, yNd)
  const b = pathFrom(m.xfrac_patch, m.tauhat_patch, xNdMid, yNd).replace('M', 'L')
  const cc = pathFrom(m.xhat_dn, m.tauhat_dn, xNdDn, yNd).replace('M', 'L')
  return `${a} ${b} ${cc}`
})

// Under-brace path (a wide flat bracket with a center tick), in main
// SVG coordinates — used for the SSA term anatomy.
function bracePath(x0: number, x1: number, y: number): string {
  const mid = (x0 + x1) / 2
  const drop = 26
  const r = 14
  return [
    `M ${x0} ${y}`,
    `q 0 ${drop - r} ${r} ${drop - r}`,
    `L ${mid - r} ${y + drop - r}`,
    `q ${r} 0 ${r} ${r + 14}`,
    `q 0 ${-r - 14} ${r} ${-r - 14}`,
    `L ${x1 - r} ${y + drop - r}`,
    `q ${r} 0 ${r} ${-(drop - r)}`,
  ].join(' ')
}

// ─────────────────────── log-log scaling cards ─────────────────────────
interface LLCard {
  key: string
  title: string
  caption: string
  xlabel: Ch1EqName
  ylabel: Ch1EqName
  decades: number[]
  x: (v: number) => number
  y: (v: number) => number
  pts: Array<{ d: string; c: string; open: boolean; dim: boolean }>
  line: { x1: number; y1: number; x2: number; y2: number }
  tri: { d: string; lx: number; ly: number; bx: number; by: number }
}

function makeCard(
  key: string, title: string, caption: string, xlabel: Ch1EqName, ylabel: Ch1EqName,
  runs: Run[], px: (r: Run) => number, py: (r: Run) => number | null,
  kappa: number,
): LLCard {
  const vals = runs
    .map((r) => ({ r, px: px(r), py: py(r) }))
    .filter((v): v is { r: Run; px: number; py: number } => v.py !== null && v.py > 0 && v.px > 0)
  const all = vals.flatMap((v) => [v.px, v.py])
  const lo = Math.pow(10, Math.floor(Math.log10(Math.min(...all))))
  const hi = Math.pow(10, Math.ceil(Math.log10(Math.max(...all))))
  const decades: number[] = []
  for (let d = lo; d <= hi * 1.0001; d *= 10) decades.push(d)
  const lgLo = Math.log10(lo)
  const lgHi = Math.log10(hi)
  const x = (v: number) => LLP + ((Math.log10(v) - lgLo) / (lgHi - lgLo)) * LL_P
  const y = (v: number) => LL_TOP + LL_P - ((Math.log10(v) - lgLo) / (lgHi - lgLo)) * LL_P
  // Slope-1 reference triangle in the empty lower-right pocket below
  // the κ line: one decade per leg (drawn at 0.8× for breathing room).
  const decPx = LL_P / (lgHi - lgLo)
  const tx0 = LLP + 0.56 * LL_P
  const ty0 = LL_TOP + LL_P - 0.16 * LL_P
  const legX = 0.8 * decPx
  const legYpx = 0.8 * decPx
  const tri = {
    d: `M ${tx0} ${ty0} L ${tx0 + legX} ${ty0} L ${tx0 + legX} ${ty0 - legYpx} Z`,
    bx: tx0 + legX / 2,
    by: ty0 + 26,
    lx: tx0 + legX + 18,
    ly: ty0 - legYpx / 2 + 7,
  }
  return {
    key, title, caption, xlabel, ylabel, decades, x, y, tri,
    // Paper fig-4 encoding: color = h, glyph = α, OPEN marker = γ 0.5.
    pts: vals.map((v) => ({
      d: markerPathAt(x(v.px), y(v.py), v.r.alpha_deg, 7),
      c: H_COLORS[v.r.h] ?? '#ccc',
      open: v.r.gamma === 0.5,
      dim: hasFilter() && !runMatches(v.r),
    })),
    line: { x1: x(lo), y1: y(lo * kappa), x2: x(hi / kappa), y2: y(hi) },
  }
}

const loglogCards = computed<LLCard[]>(() => {
  const d = data.value
  if (!d) return []
  // ALL h < [x] < ℓ runs — the paper's fig-4c/d point set (69 runs).
  const runs = d.ensemble
  return [
    makeCard(
      'tau', 'Stress magnitude',
      `${d.kappa.tau.toFixed(2)} · ${runs.length} runs`,
      'll_x_tau', 'll_y_tau',
      runs, (r) => r.tauscale_kpa, (r) => r.max_tau_kpa, d.kappa.tau,
    ),
    makeCard(
      'dl', 'Decay lengthscale',
      `${d.kappa.dl.toFixed(2)} · ${runs.filter((r) => r.dl_m).length} runs`,
      'll_x_dl', 'll_y_dl',
      runs, (r) => r.xscale_m, (r) => r.dl_m, d.kappa.dl,
    ),
  ]
})
</script>

<style scoped>
/* Full-screen stage. NO z-index: DOM order keeps this above the globe
   canvas + HUD cards and below the beat-nav buttons. The chalkboard
   lives on .tp-backdrop so the seam entry can hold it transparent. */
.tp-root {
  position: fixed;
  inset: 0;
  background: transparent;
  pointer-events: none;
  /* Show/hide is a plain opacity tween on the ALREADY-PAINTED panel
     (mounted one beat early) — duration set inline: 0.9 s reveal,
     0.5 s hide. */
  transition: opacity 0.9s ease;
}

.tp-backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 90% at 30% 20%, #12100c 0%, #0a0908 55%, #060606 100%);
}

/* Stage: FULL SCREEN by default; slides left for the log-log stage.
   The width transition is what moves the collapsed figure aside. */
.tp-stage {
  position: absolute;
  top: 0;
  left: 0;
  right: 1vw;
  bottom: 0;
  display: flex;
  flex-direction: column;
  /* The top padding clears the ribbon AND its sub-menu bar (Explore's
     --chrome-bottom, rem-based) with TP_STAGE_GAP to spare, so the
     figure's y = 0 can never sit under the band — before (6.5vh alone)
     a height-limited viewport (1920×1080, or a windowed browser at
     1440×~790) started the SVG inside the band and hid the equations'
     exponents. theoryLayout.ts mirrors this
     for the beat 5→6 seam fit — change both or the seam misaligns. */
  padding: max(6.5vh, calc(var(--chrome-bottom, 0px) + 0.5rem)) 0 1vh 1vw;
}

.tp-svg {
  flex: 1 1 auto;
  width: 100%;
  min-height: 0;
}

/* Bigger axis type — people in the back of the room. */
.tp-axis line {
  stroke: rgba(245, 245, 245, 0.8);
  stroke-width: 2.5;
}
.tp-axis text {
  font-family: 'Inter', system-ui, sans-serif;
  /* 29 (was 27): the director asked for bigger axes */
  font-size: 29px;
  fill: rgba(245, 245, 245, 0.92);
  font-variant-numeric: tabular-nums;
}
.tp-axis .tp-axis-name {
  font-size: 28px;
  letter-spacing: 0.05em;
  fill: rgba(245, 245, 245, 0.88);
}

.tp-sweep-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 27px;
  fill: #f5c75e;
  font-variant-numeric: tabular-nums;
}

.tp-schem-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 22px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  fill: #7a4a10;
}

.tp-band-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 23px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.tp-band-label.patch { fill: rgba(245, 199, 94, 0.95); }
.tp-band-label.up    { fill: rgba(140, 190, 255, 0.95); }

/* UPSTREAM / DOWNSTREAM over the boundary-layer bands. */
.tp-side-title {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  fill: rgba(170, 205, 255, 1);
}

/* Zone words: bottom of the derivation plot; above the collapse's
   three panels (Fig. 4b's panel titles). */
.tp-eq-card {
  fill: url(#tp-card-grad);
  stroke: #f4cf6a;
  stroke-width: 2.5;
  rx: 16;
  filter: url(#tp-card-shadow);
}
.tp-zone-word {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 24px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  fill: rgba(245, 245, 245, 0.88);
}
.tp-zone-word.up    { fill: rgba(150, 195, 255, 1); }
.tp-zone-word.patch { fill: rgba(245, 199, 94, 1); }

/* LaTeX axis titles sit a touch under full white, like the tick text. */
.tp-ax-eq { opacity: 1; }
.tp-leg-head { opacity: 1; }

/* The u' axis: violet ticks + labels. */
.tp-axis.tp-axis-vel line { stroke: rgba(185, 163, 236, 0.8); }
.tp-axis.tp-axis-vel text { fill: rgba(185, 163, 236, 0.95); }

/* SSA term-anatomy labels (SVG text) */
.tp-ssa-label {
  font-family: 'Inter', system-ui, sans-serif;
  /* 24px crowded the three labels once the equation moved INSIDE the
     plot at SSA_W 640 — neighbors were touching. */
  font-size: 19px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  fill: var(--gold);
}

/* ── ACL stage ── */
.tp-acl-tauval {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 27px;
  fill: rgba(255, 255, 255, 0.9);
  letter-spacing: 0.03em;
}
.tp-acl-tauval .tp-sub { font-size: 19px; }
/* The estimate on its plate (the director's request): steady — the
   old 2.2 s opacity pulse went with the move; the plate is the emphasis. */
.tp-acl-label {
  font-family: 'EB Garamond', serif;
  font-size: 42px;
  fill: #f5c75e;
  letter-spacing: 0.02em;
}
.tp-acl-plate {
  fill: rgba(10, 9, 8, 0.86);
  stroke: rgba(245, 199, 94, 0.55);
  stroke-width: 1.5;
}

/* ── in-plot legend (SVG) ── */
.tp-leg { pointer-events: auto; cursor: default; }
.tp-leg-row { cursor: pointer; }
.tp-leg-title {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 23px;
  fill: var(--gold-bright);
  letter-spacing: 0.04em;
}
.tp-leg-h {
  /* Serif italic, NO uppercase transform — 'α' must stay a Greek
     alpha, not read as a Latin 'A'. */
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 24px;
  letter-spacing: 0.05em;
  fill: var(--gold);
}
.tp-leg-txt {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 24px;
  fill: rgba(245, 245, 245, 0.9);
  font-variant-numeric: tabular-nums;
}
.tp-leg-ana { fill: var(--gold-bright); }
.tp-leg-glyph {
  font-size: 24px;
  fill: rgba(245, 245, 245, 0.9);
}

/* ══════════ log-log cards — square, SIDE BY SIDE in the right column
   (loglog stage). Every size is in figure units:
   the column's left/top/scale come from figRect (like the ACL slider
   card), so the two cards are a fixed piece of the FIGURE — 1 unit =
   0.70 px at 1280, 0.79 at 1440, 1.06 at 1920×1200. Type: ticks 28
   (22 px at 1440), superscripts 21 (17 px), caption 24 (19 px). ═════ */
.tp-loglog {
  position: absolute;
  transform-origin: 0 0;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  transition: opacity 0.5s;
}
.tp-loglog-card {
  box-sizing: border-box;
  width: 450px;  /* = CARD_W */
  height: 582px; /* = CARD_H */
  padding: 12px 12px 10px; /* = CARD_PAD */
  background: rgba(10, 9, 8, 0.9);
  border: 1.5px solid var(--gold-faint);
  border-radius: 14px;
}
.tp-loglog-title {
  font-family: 'EB Garamond', serif;
  font-size: 30px;
  line-height: 34px; /* = CARD_TITLE_H */
  color: var(--gold-bright);
  margin-bottom: 6px;
  white-space: nowrap;
}
.tp-loglog-svg { width: 426px; height: 484px; display: block; } /* = LL_W × LL_H */
.tp-ll-tick {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 28px;
  fill: rgba(245, 245, 245, 0.92);
}
.tp-ll-sup {
  font-size: 21px;
}
.tp-ll-kappa { display: inline-block; opacity: 1; }
.tp-loglog-caption {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 24px;
  line-height: 36px; /* = CARD_CAPTION_H */
  color: rgba(245, 245, 245, 0.92);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ══════════ stage-8 maps panel (SVG) ══════════ */
.tp-map-title {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 27px;
  fill: var(--gold-bright);
  letter-spacing: 0.01em;
}
.tp-map-sym { font-style: italic; }
.tp-map-tick {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 22px;
  fill: rgba(245, 245, 245, 0.88);
  font-variant-numeric: tabular-nums;
}

/* ══════════ ACL sliders (acl stage).
   Every size below is in SVG viewBox units: the card's left/top/scale
   come from figRect, so it is a fixed piece of the FIGURE — the same
   size and place relative to the plot at any window width (1 unit =
   0.70 px at 1280, 0.79 px at 1440, 1.02 px at 1920). ══════════ */
.tp-acl-controls {
  position: absolute;
  box-sizing: border-box;
  transform-origin: 0 0;
  padding: 12px 20px 12px 14px;
  background: rgba(10, 9, 8, 0.88);
  border: 1.5px solid var(--gold-dim);
  border-radius: 14px;
  pointer-events: auto;
  transition: opacity 0.6s;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.tp-ctl-row {
  display: grid;
  grid-template-columns: 58px 1fr 124px;
  align-items: center;
  column-gap: 14px;
}
.tp-ctl-row:last-child { grid-template-columns: 58px 1fr auto; }

/* ≥ 1.05 rem at 1280 (34 × 0.70 = 24 px) */
.tp-ctl-sym {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 34px;
  line-height: 1;
  color: var(--gold-bright);
  text-align: right;
}
.tp-ctl-sym sub {
  font-size: 20px;
}

/* ≥ 1.15 rem at 1280 (27 × 0.70 = 19 px) */
.tp-ctl-val {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 27px;
  line-height: 1;
  color: rgba(245, 245, 245, 0.9);
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.tp-ctl-gamma {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tp-acl-controls input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  margin: 0;
  border-radius: 3px;
  background: rgba(245, 199, 94, 0.42);
  outline: none;
  cursor: pointer;
}
.tp-acl-controls input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1.5px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}
.tp-acl-controls input[type='range']::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1.5px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}

/* the two-position γ slider: a short track with its two stops marked */
.tp-acl-controls input[type='range'].tp-binary {
  width: 72px;
  flex: none;
  background:
    radial-gradient(circle at 12px 50%, rgba(245, 199, 94, 0.75) 3.5px, transparent 4px),
    radial-gradient(circle at calc(100% - 12px) 50%, rgba(245, 199, 94, 0.75) 3.5px, transparent 4px),
    rgba(245, 199, 94, 0.42);
}

.tp-ctl-reset {
  background: transparent;
  border: 1.5px solid var(--gold-dim);
  color: var(--gold);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 21px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 7px 18px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.2s, border-color 0.2s;
}
.tp-ctl-reset:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
}

/* log-log stage: the "more details" door, bottom-right corner */
.tp-more {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  transition: opacity 0.5s;
}
</style>
