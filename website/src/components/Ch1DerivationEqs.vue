<template>
  <!-- Chapter 1's derivation, in full, for the deeper dive (the director
       wanted the whole derivation available there, not only the pieces the
       talk's beats show) — the one-dimensional model from the SSA to the three-zone
       stress solution and its velocity companion, the published article (J. Glaciol. 72, e76) §2.2 +
       Appendix B, typeset by cinematic/scene_ch01/build_theory_eqs.py (R2
       ch01/eq2/), one column. The connecting text is never invented: the
       director required the derivation to use the paper's own words, so
       every gloss is the paper's own sentence — the
       text that follows that equation in the paper and leads into the next
       — lightly trimmed; equation numbers are the published PDF's (Appendix B = B.1–B.22). The same
       component shows the Glen's-law entry (set="glen"). -->
  <div class="sp-wrap">
    <p v-if="SETS[set].intro" class="sp-gloss sp-intro" v-html="SETS[set].intro" />
    <ol class="sp-root">
      <li v-for="r in SETS[set].rows" :key="r.eq" class="sp-row">
        <div v-if="r.head" class="sp-head">
          <h6 class="sp-head-title">{{ r.head.title }}</h6>
          <p class="sp-gloss" v-html="r.head.text" />
        </div>
        <div class="sp-line">
          <img :src="eqUrl(r.eq)" :style="box(r.eq)" class="sp-eq" :alt="r.alt" />
          <span class="sp-num">{{ r.num }}</span>
        </div>
        <p class="sp-gloss" v-html="r.gloss" />
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import { CH1_EQ, type Ch1EqName } from '../config/ch1Eqs'
import { mediaUrl } from '../config/media'

interface Row {
  eq: Ch1EqName
  /** The paper's equation number(s). */
  num: string
  alt: string
  /** The paper's text after this equation (trusted static HTML). */
  gloss: string
  /** A sub-heading + the paper's lead-in paragraph above this row. */
  head?: { title: string; text: string }
}

// Notation helpers (the paper's symbols in Garamond italics).
const T = '<i>τ</i><sub>xx</sub>'
const X = '[<i>x</i>]'
const U = '[<i>u</i>]'
const DERIVATION: Row[] = [
  {
    eq: 'drv_ssa',
    num: '4',
    alt: '∂x(2hτxx) − τb − ρgh ∂xs = 0',
    gloss:
      `where <i>g</i> is gravity, <i>h</i>, <i>ρ</i>, <i>s</i> are ice thickness, density, and surface, respectively, and ${T} is longitudinal deviatoric stress. This approximation of Stokes requires a dominant contribution of sliding to the overall velocity, namely <i>γ</i> ≪ 1 (eq. 3). As mentioned above, this depth-averaged model uses the following parameterization for the basal shear term,`,
  },
  {
    eq: 'drv_weertman',
    num: '5, B.3',
    alt: 'τb = C|u|^{1/n−1}u, C = Cb (ub/u)^{1/n}',
    gloss:
      `where <i>C</i>, <i>u</i> are depth-averaged quantities with <i>C</i> = <i>C</i><sub>b</sub>(<i>u</i><sub>b</sub>/<i>u</i>)<sup>1/<i>n</i></sup> (eq. B.3) relating the depth integrated quantity <i>C</i> in our 1-D model with the basal quantities <i>C</i><sub>b</sub>, <i>u</i><sub>b</sub> from the Elmer/Ice simulations. The flow law exponent <i>n</i> comes from Glen’s flow law (Glen 1955), which relates the strain rate to the applied stress as`,
  },
  {
    eq: 'drv_glen',
    num: '6',
    alt: 'τxx = B|ε̇xx|^{1/n−1} ε̇xx, ε̇xx = ∂x u',
    gloss:
      `with <i>B</i> the ice hardness parameter and <i>ε̇</i><sub>xx</sub> = ∂<sub>x</sub><i>u</i> the deviatoric strain rate, where <i>u</i> is horizontal velocity. We take the simplifying case of constant ice thickness and surface slope, <i>s</i><sub>x</sub> = −<i>α</i>. With these relationships, we rewrite the SSA equation in terms of velocity as`,
  },
  {
    eq: 'ssa',
    num: '7',
    alt: '2Bh(|u_x|^{1/n−1}u_x)_x − C|u|^{1/n−1}u + ρghα = 0',
    gloss: 'where derivatives are here and henceforth denoted with subscripts. The basal traction condition is piecewise constant across the domain,',
  },
  {
    eq: 'drv_cx',
    num: '8',
    alt: 'C(x) = 0 on [0, ℓ]; C > 0 outside',
    gloss:
      'We are predominantly interested in the spatial structure of the perturbed stress that arises from the presence of a spatially finite patch of free-slip. Our model considers the stress profile across the patch as setting the boundary condition for the surrounding boundary layers upstream and downstream from the patch. Inside the patch <i>C</i> = 0 and the SSA reduces to',
  },
  {
    eq: 'drv_patch_ode',
    num: '9',
    alt: '(2hτxx)_x = −τd on the patch',
    gloss:
      'where <i>τ</i><sub>d</sub> = <i>ρghα</i> is the driving stress. Independent of <i>n</i>, this yields a linear membrane stress profile across the patch (see also Fig. 4 b, f, middle panel) of',
  },
  {
    eq: 'drv_patch_linear',
    num: '10',
    alt: 'τxx(x) = τxx(0) − (τd/2h) x',
    gloss:
      `The antisymmetry of the membrane stress about the patch center, ${T}(<i>ℓ</i>/2) = 0, gives the boundary condition at the upstream patch edge,`,
  },
  {
    eq: 'drv_patch_bc',
    num: '11, 13',
    alt: 'τxx(0) = −τxx(ℓ) = τdℓ/4h = ρgαℓ/4 ≡ [τxx]',
    gloss: 'such that eq. 10 can be rewritten as',
  },
  {
    eq: 'tau_patch',
    num: '12',
    alt: 'τxx = ρgαℓ/4 (1 − 2x/ℓ)',
    gloss:
      `yielding a characteristic scale for the stress perturbation, [${T}] ≡ <i>ρgαℓ</i>/4 (eq. 13). Outside the patch where our basal traction is given by <i>C</i>(<i>x</i>) = <i>C</i>, the governing equation is`,
  },
  {
    eq: 'drv_outside',
    num: '14',
    alt: '(2hτxx)_x − C|u|^{1/n−1}u = −τd outside the patch',
    gloss:
      `subjected to the boundary condition above (eq. 11). Using the constitutive relation ${T} = <i>B</i>|<i>u</i><sub>x</sub>|<sup>1/<i>n</i>−1</sup><i>u</i><sub>x</sub>, the relevant length and velocity scales of this region can be found from the balance between the deviatoric stress gradient term, 2<i>Bh</i>(|<i>u</i><sub>x</sub>|<sup>1/<i>n</i>−1</sup><i>u</i><sub>x</sub>)<sub>x</sub>, and the basal drag term, <i>C</i>|<i>u</i>|<sup>1/<i>n</i>−1</sup><i>u</i>, in eq. 7,`,
  },
  {
    eq: 'drv_bl_balance',
    num: '15, 16',
    alt: 'membrane ~ drag ⇒ [x] = (2Bh/C)^{n/(n+1)}',
    gloss:
      `from which ${U}<sup>1/<i>n</i></sup> cancels, giving the characteristic lengthscale of this region (eq. 16). This region is host to a boundary layer (BL) at the edge (upstream and downstream) of the patch, where the flow transitions from the far field, which is characterized by a balance between basal drag and driving stress, to the patch interior, which is characterized by a balance between longitudinal stresses and driving stress. Thus, across this boundary layer, there is a balance between longitudinal stresses and basal drag. The velocity scale is then determined by the membrane stress boundary condition at <i>x</i> = 0 (eq. 11),`,
  },
  {
    eq: 'drv_u_scale',
    num: '17, 18',
    alt: '2Bh [u]^{1/n}/[x]^{1/n} = τdℓ/2 ⇒ [u] = [x](τdℓ/4Bh)^n = [x](ρgαℓ/4B)^n',
    gloss: 'Nondimensionalizing with',
  },
  {
    eq: 'drv_nondim',
    num: '19–21',
    alt: 'u = [u]ũ, x = [x]x̃, τxx = [τxx]τ̃xx',
    gloss:
      `with ${U}, ${X}, and [${T}] defined in eqs. 18, 16, and 13 respectively, gives the dimensionless governing equation outside the patch,`,
  },
  {
    eq: 'drv_nondim_ode',
    num: '22, 23',
    alt: '(|ũ_x̃|^{1/n−1}ũ_x̃)_x̃ − |ũ|^{1/n−1}ũ = −2δ, δ ≡ [x]/ℓ',
    gloss:
      `where <i>δ</i> ≡ ${X}/<i>ℓ</i> is the ratio of the boundary layer extent to the patch length (not to be confused with the Dirac delta function). Here, we decompose the velocity into a sum of two components, namely the background far-field velocity <i>u</i><sub>∞</sub> and the perturbed boundary layer velocity <i>u</i>′. We do this in order to facilitate later comparison between this analytical solution and the depth-averaged numerical simulations with the background velocity subtracted away. In particular, we take`,
  },
  {
    eq: 'drv_decomp',
    num: '24, 25',
    alt: 'ũ(x̃) = ε + ũ′(x̃), ε ≡ u∞/[u]',
    gloss:
      'where <i>ε</i> relates the relative scales of the far-field and perturbation velocity components. Substitution into the dimensionless governing equation, noting that <i>ũ</i><sub>x̃</sub> = <i>ũ</i>′<sub>x̃</sub>, gives',
  },
  {
    eq: 'drv_subst',
    num: '26',
    alt: '(|ũ′_x̃|^{1/n−1}ũ′_x̃)_x̃ − |ε + ũ′|^{1/n−1}(ε + ũ′) = −2δ',
    gloss:
      'We note that the dimensionless background balance, obtained by evaluating the governing equation far from the patch where <i>ũ</i>′ → 0, requires',
  },
  {
    eq: 'drv_bg',
    num: '27',
    alt: '|ε|^{1/n−1}ε = 2δ',
    gloss: 'which allows us to rewrite the governing equation as',
  },
  {
    eq: 'drv_exact',
    num: '28',
    alt: '(|ũ′_x̃|^{1/n−1}ũ′_x̃)_x̃ = |ε + ũ′|^{1/n−1}(ε + ũ′) − |ε|^{1/n−1}ε',
    gloss:
      'For <i>n</i> = 1, the right-hand side simplifies exactly: (<i>ε</i> + <i>ũ</i>′) − <i>ε</i> = <i>ũ</i>′, independent of <i>ε</i>. For <i>n</i> &gt; 1, since <i>ε</i> = (2<i>δ</i>)<sup><i>n</i></sup> ≪ 1 when <i>δ</i> ≪ 1 (eq. 27), the right-hand side of eq. 28 reduces to |<i>ũ</i>′|<sup>1/<i>n</i>−1</sup><i>ũ</i>′, giving the leading-order boundary layer equation to be eq. 29, which is subjected to the boundary conditions eqs. 30–31,',
  },
  {
    eq: 'drv_bl_ode',
    num: '29–31',
    alt: 'the leading-order non-dimensional boundary-layer equation with its two conditions',
    gloss:
      `where the second condition is the dimensionless version of eq. 11. Taking typical scales of <i>h</i> ~ 10<sup>3</sup> m, <i>ℓ</i> ~ 10<sup>4</sup> m, <i>B</i> ~ 7.5 × 10<sup>7</sup> Pa s<sup>1/3</sup>, <i>C</i> ~ 5 × 10<sup>6</sup> Pa s<sup>1/3</sup> m<sup>−1/3</sup> gives ${X} ~ 2.3 × 10<sup>3</sup> m (eq. 16). In order to strictly use SSA to describe this system, we must have <i>h</i> ≪ ${X} ≪ <i>ℓ</i>. With the scales estimated from above, we have <i>h</i> ~ 1 × 10<sup>3</sup> m, ${X} ~ 2.3 × 10<sup>3</sup> m, and <i>ℓ</i> ~ 10<sup>4</sup> m, meaning <i>δ</i> ~ 0.23. While the parameter combinations may not place us deeply within the asymptotic regime of <i>δ</i> ≪ 1, the resulting reduced-order model is reasonable, illustrative and interpretable, but not asymptotically strict. Thus, the remainder of this derivation shall be concerned with evaluating analytically the system under these assumptions, but note that the boundary layer scaling (eq. 16) sufficiently captures relationships outside this parameter regime (see, e.g., Fig. 4 c, d, g, h). For convenience, we define <i>y</i> ≡ |<i>u</i>′<sub>x</sub>|<sup>1/<i>n</i>−1</sup><i>u</i>′<sub>x</sub>, so that <i>u</i>′<sub>x</sub> = |<i>y</i>|<sup><i>n</i>−1</sup><i>y</i> (eqs. 32–33), which allows us to write our leading-order governing equation as eq. 35; integration of this equation (and applying the boundary condition from eq. 30) yields eq. 36:`,
  },
  {
    eq: 'drv_bl_first',
    num: '32–36',
    alt: 'y ≡ |ũ′_x̃|^{1/n−1} ũ′_x̃ = τ̃xx; (1/(n+1)) d|y|^{n+1}/dũ′ = |ũ′|^{1/n−1}ũ′ ⇒ |y|^{n+1} = n|ũ′|^{(n+1)/n}',
    gloss:
      'where we can drop the absolute values given the solution (subjected to the boundary conditions) will be positive everywhere, and we write, for simplicity, <i>u</i>′<sub>x</sub> = <i>n</i><sup><i>n</i>/(<i>n</i>+1)</sup><i>u</i>′ (eq. 38). Integration of the ODE gives',
  },
  {
    eq: 'drv_bl_u',
    num: '37–40',
    alt: "ũ′_x̃ = n^{n/(n+1)} ũ′ ⇒ ũ′ = ũ′0 exp(n^{n/(n+1)} x̃), ũ′0 = (1/n)^{n/(n+1)}",
    gloss:
      `where <i>u</i>′<sub>0</sub> ≡ <i>u</i>′(0) = (1/<i>n</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> is determined by the boundary condition at <i>x</i> = 0, namely |<i>y</i>(0)|<sup><i>n</i>+1</sup> = 1<sup><i>n</i>+1</sup> = <i>n</i>|<i>u</i>′<sub>0</sub>|<sup>(<i>n</i>+1)/<i>n</i></sup>. This gives the velocity structure in the boundary layer (as discussed further in Appendix B, below). For the deviatoric stress, we use the constitutive relation in dimensionless form, ${T} = |<i>u</i>′<sub>x</sub>|<sup>1/<i>n</i>−1</sup><i>u</i>′<sub>x</sub> = <i>y</i>(<i>x</i>) (eq. 41). Substituting the velocity solution gives the dimensionless stress decay profile`,
  },
  {
    eq: 'drv_bl_tau',
    num: '41, 42',
    alt: 'τ̃xx = y = n^{1/(n+1)} ũ′^{1/n} = exp(n^{−1/(n+1)} x̃)',
    gloss:
      `where we drop the absolute value signs because <i>u</i>′ &gt; 0 and <i>u</i>′<sub>x</sub> &gt; 0 in the upstream boundary layer. Downstream from the trailing edge of the patch (<i>x</i> = <i>ℓ</i>), the stress profile is solved for in the same way, with the stress decaying at the same rate into <i>x</i> &gt; <i>ℓ</i>. In summary, the relevant spatial scale for the stress perturbation differs across the domain. Namely, ${X} = (2<i>Bh</i>/<i>C</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> (eq. 16) dictates the stress decay lengthscale upstream and downstream from the patch (eq. 42), and <i>ℓ</i> characterizes the linear stress variation lengthscale across the patch interior (eq. 12). Returning to dimensional variables ${T} and <i>x</i>, we write the summary for the deviatoric stress profile across the full domain:`,
  },
  {
    eq: 'drv_summary',
    num: '43',
    alt: 'τxx/(ρgαℓ/4) = exp(n^{−1/(n+1)} x/[x]) (x ≤ 0); 1 − 2x/ℓ (0 ≤ x ≤ ℓ); −exp(−n^{−1/(n+1)} (x−ℓ)/[x]) (x ≥ ℓ)',
    gloss:
      `Inside the boundary layer regions, the spatial coordinate <i>x</i> is measured from the nearest patch edge and scaled by ${X} (eq. 16), while inside the patch the coordinate is measured from the upstream edge and scaled by the patch length <i>ℓ</i>. This analytical solution is rendered as the solid black curve in Fig. 4 b, f.`,
  },
  // ── Appendix B · the velocity ──────────────────────────────────────
  {
    eq: 'drv_patch_ux',
    num: 'B.6, B.7',
    alt: "u'_x = |τxx/B|^{n−1} τxx/B = (ρgαℓ/4B)^n |1 − 2x/ℓ|^{n−1}(1 − 2x/ℓ)",
    head: {
      title: 'Appendix B · Velocity',
      text:
        `We now present the 1-D model for the velocity field. Outside the patch, we have already encountered the velocity solution as an intermediate step in deriving stress (eq. 40). For the velocity across the patch, we begin by recalling the dimensional linear deviatoric stress profile across the patch (eq. 12), where again we have returned to dimensional variables. We obtain the velocity gradient from the constitutive relation ${T} = <i>B</i>|<i>u</i><sub>x</sub>|<sup>1/<i>n</i>−1</sup><i>u</i><sub>x</sub> (recalling that <i>u</i><sub>x</sub> = <i>u</i>′<sub>x</sub> because <i>u</i><sub>∞</sub> is constant), and substitute the linear stress profile, which gives`,
    },
    gloss:
      `We introduce dimensionless variables <i>ũ</i>′ = <i>u</i>′/${U}, <i>ξ</i> = <i>x</i>/<i>ℓ</i> (eq. B.8), where ${U} = ${X}(<i>τ</i><sub>d</sub><i>ℓ</i>/(4<i>Bh</i>))<sup><i>n</i></sup> (eq. 18). Converting the <i>x</i> derivative using <i>u</i>′<sub>x</sub> = (1/<i>ℓ</i>)<i>du</i>′/<i>dξ</i> and substituting the dimensionless variables, the (<i>τ</i><sub>d</sub><i>ℓ</i>/(4<i>Bh</i>))<sup><i>n</i></sup> factors cancel (eqs. B.9–B.10), leaving (dropping tildes)`,
  },
  {
    eq: 'drv_patch_xi',
    num: 'B.8, B.11',
    alt: "ũ′ = u′/[u], ξ = x/ℓ ⇒ du′/dξ = (ℓ/[x]) |1 − 2ξ|^{n−1}(1 − 2ξ) = (1/δ) |1 − 2ξ|^{n−1}(1 − 2ξ)",
    gloss:
      `where <i>δ</i> = ${X}/<i>ℓ</i> (eq. 23). We integrate from <i>ξ</i> = 0, where <i>u</i>′(0) = <i>u</i>′<sub>0</sub> = (1/<i>n</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> is the velocity at the patch edge (eq. 40). We note that the antiderivative of |1 − 2<i>ξ</i>|<sup><i>n</i>−1</sup>(1 − 2<i>ξ</i>) with respect to <i>ξ</i> is −|1 − 2<i>ξ</i>|<sup><i>n</i>+1</sup>/(2(<i>n</i> + 1)), which can be verified by considering two cases separately, <i>ξ</i> &lt; 1/2 and <i>ξ</i> &gt; 1/2 (eqs. B.13–B.14). With this, we integrate directly to get`,
  },
  {
    eq: 'drv_patch_int',
    num: 'B.12, B.18',
    alt: "u′(ξ) = u′0 + (1/δ)∫0^ξ |1 − 2ξ′|^{n−1}(1 − 2ξ′) dξ′ = u′0 + [1 − |1 − 2ξ|^{n+1}]/(2(n+1)δ)",
    gloss:
      'where <i>u</i>′<sub>0</sub> = (1/<i>n</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> is the velocity at the patch edge. The velocity is symmetric about the patch center <i>ξ</i> = 1/2, where it reaches its maximum value of',
  },
  {
    eq: 'drv_umax_nd',
    num: 'B.19',
    alt: "u′max = u′0 + 1/(2(n+1)δ) = (1/n)^{n/(n+1)} + 1/(2(n+1)δ)",
    gloss:
      `Below we derive a suitable normalization for the velocity perturbation within the patch. Subtracting the velocity maximum (eq. B.19) from the patch-interior equation (eq. B.18) gives <i>u</i>′(<i>ξ</i>) − <i>u</i>′<sub>max</sub> = −|1 − 2<i>ξ</i>|<sup><i>n</i>+1</sup>/(2(<i>n</i> + 1)<i>δ</i>) (eq. B.20). Returning to dimensional variables using <i>u</i>′ = ${U}<i>ũ</i>′, <i>ξ</i> = <i>x</i>/<i>ℓ</i>, and ${U} = ${X}(<i>τ</i><sub>d</sub><i>ℓ</i>/(4<i>Bh</i>))<sup><i>n</i></sup> (eq. 18), and noting that 1/<i>δ</i> = <i>ℓ</i>/${X}, the factors of ${X} cancel to give`,
  },
  {
    eq: 'u_patch',
    num: 'B.21',
    alt: "(u′ − u′max)/((ρgαℓ/4B)^n ℓ) = −2^n/(n+1) |x/ℓ − 1/2|^{n+1}",
    gloss:
      `The right-hand side depends only on <i>x</i>/<i>ℓ</i>: the velocity shape within the patch is independent of the basal sliding coefficient <i>C</i> and the coupling length ${X}, which enter only through the peak amplitude <i>u</i>′<sub>max</sub>. Thus, for comparison between the numerical and analytical curves across the patch, the depth-averaged numerical velocity magnitudes are shifted by the maximum velocity <i>u</i>′<sub>max</sub> and normalized by (<i>ρgαℓ</i>/4<i>B</i>)<sup><i>n</i></sup><i>ℓ</i>, such that all curves collapse regardless of <i>δ</i> onto the analytical curve (black curves, Fig. B1 b, e). The perturbed velocity in the upstream and downstream boundary layer regions, derived in the main text (eq. 40), is rescaled by the perturbed velocity at the patch edge <i>u</i>′<sub>0</sub>, such that the dimensionless velocity at the patch edges is unity. The velocity decay length outside the patch, like the stresses, is characterized by ${X} (eq. 16). In summary, the velocity model across the domain is expressed as`,
  },
  {
    eq: 'drv_velo_summary',
    num: 'B.22',
    alt: 'the three-zone velocity solution (eq. B.22)',
    gloss:
      `where ${X} = (2<i>Bh</i>/<i>C</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> (eq. 16), the patch-edge and maximum perturbed velocities are given in dimensional form by <i>u</i>′<sub>0</sub> = ${U}(1/<i>n</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> and <i>u</i>′<sub>max</sub> = ${U}[(1/<i>n</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> + 1/(2(<i>n</i> + 1)<i>δ</i>)], with the velocity scale ${U} = ${X}(<i>ρgαℓ</i>/4<i>B</i>)<sup><i>n</i></sup> (eq. 18).`,
  },
]

// Glen's flow law as its own entry (the director noticed the flow law
// appeared nowhere in the additional-work pages): the paper's eq. 6
// with its sentence, and Table 1's flow-law rows with §2.1's sentence.
const GLEN: Row[] = [
  {
    eq: 'drv_glen',
    num: '6',
    alt: 'τxx = B|ε̇xx|^{1/n−1} ε̇xx, ε̇xx = ∂x u',
    gloss:
      'with <i>B</i> the ice hardness parameter and <i>ε̇</i><sub>xx</sub> = ∂<sub>x</sub><i>u</i> the deviatoric strain rate, where <i>u</i> is horizontal velocity.',
  },
  {
    eq: 'glen_table',
    num: 'Table 1',
    alt: 'n = 1 or 3; B^−n = 5.0e−15 (n = 1), 2.4e−24 (n = 3) Pa^−n s^−1',
    gloss:
      'We repeated this experiment for two ice rheologies: Newtonian (<i>n</i> = 1) and Glen (<i>n</i> = 3).',
  },
]

const SETS: Record<'derivation' | 'glen', { intro?: string; rows: Row[] }> = {
  derivation: {
    intro:
      'To derive the one-dimensional (1-D) model, we begin by considering the depth-averaged shallow-shelf approximation (SSA) (MacAyeal 1989)',
    rows: DERIVATION,
  },
  glen: {
    intro:
      'The flow law exponent <i>n</i> comes from Glen’s flow law (Glen 1955), which relates the strain rate to the applied stress as',
    rows: GLEN,
  },
}

withDefaults(defineProps<{ set?: 'derivation' | 'glen' }>(), { set: 'derivation' })

function eqUrl(name: Ch1EqName): string {
  return mediaUrl(`ch01/eq2/${name}.svg`)
}
/** The TeX box at --eqk CSS px per bp (width + aspect; a wide line clamps to the column). */
function box(name: Ch1EqName) {
  const b = CH1_EQ[name]
  return { width: `calc(${b.w} * var(--eqk))`, aspectRatio: `${b.w} / ${b.h}` }
}
</script>

<style scoped>
.sp-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(8 * var(--eqk));
}
.sp-root {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(11 * var(--eqk));
}
.sp-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  max-width: 100%;
}
.sp-line {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 100%;
}
.sp-eq {
  display: block;
  flex: 0 1 auto;
  max-width: 100%;
  height: auto;
  user-select: none;
}
/* the paper's equation number, as in the PDF's margin */
.sp-num {
  flex: none;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  color: var(--gold-dim);
  white-space: nowrap;
}
.sp-num::before { content: '('; }
.sp-num::after { content: ')'; }
.sp-head {
  margin: calc(6 * var(--eqk)) 0 0.4rem;
  padding-top: calc(6 * var(--eqk));
  border-top: 1px solid rgba(232, 185, 74, 0.25);
  width: 100%;
}
.sp-head-title {
  margin: 0 0 0.4rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500;
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--gold);
}
.sp-gloss {
  margin: 0;
  max-width: 52rem;
  font-size: 0.95rem;
  line-height: 1.4;
  color: #cfc9bd;
}
.sp-intro { font-size: 1rem; }
.sp-gloss :deep(i) { font-family: 'EB Garamond', serif; font-size: 1.12em; }
.sp-gloss :deep(sub),
.sp-gloss :deep(sup) { font-size: 0.72em; }
</style>
