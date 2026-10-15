// The three chapter TAKEAWAYS — the ONE place they are worded (the
// director's requirement: each chapter's implications are written on its
// implications page and are consistent with what the conclusions page
// shows).
//
// The Conclusion page lists all three (SectionConclusion.vue); each
// chapter's Implications slide closes on its own, word for word: Chapter
// 1 under the twin Greenlands (TwinGlobes.vue), Chapter 2 and Chapter 3
// under their one figure (Ch2Implications.vue, Ch3Implications.vue).
// Edit a line here and all of them follow — never retype it in a
// component. Each chapter's LAST beat (`takeaway` in its registry) dims
// the page and pops its line into a centred card (TakeawayPop.vue, the
// director's design), and the Introduction's last step pops INTRO_TAKEAWAY below.
//
// Headlines only — the director wanted just the headline takeaways,
// without the verbosity (the support lines were removed then). The
// lines are his wording:
//   1 · the current line: "stress perturbation magnitude scales with slope and
//       patch length, decay length scales with thickness and
//       slipperiness" (max τxx = ρgαℓ/4; ACL ∝ h·f(γ)) — before that, the
//       JOG discussion's "the interior ice sheet is less vulnerable to
//       triggering hydrofracture-driven lake drainage".
//   2 · with the chapter viscous-only on the talk: "3d stress
//       perturbation from slippery patch is tensile upstream, compressive
//       downstream, and modulated by basal topography" — before that the
//       PNAS line, elastic peaks far higher than viscous but stays close
//       to the drained lake (the elastic model lives in the deeper dive).
//   3 · ESSD abstract — "extending lake drainage classification from
//       rate-based to mechanism-based". The director is still turning this
//       one over; edit freely.
export interface Takeaway {
  chapter: string
  point: string
}

export const TAKEAWAYS: readonly Takeaway[] = [
  {
    chapter: 'Chapter 1',
    point:
      'Stress perturbation magnitude scales with slope and patch length, decay length scales with thickness and slipperiness.',
  },
  {
    chapter: 'Chapter 2',
    point:
      '3D stress perturbation from a slippery patch is tensile upstream, compressive downstream, and modulated by basal topography.',
  },
  {
    chapter: 'Chapter 3',
    point:
      'Lake drainage can be classified by mechanism, not just by rate.',
  },
]

export const CH1_TAKEAWAY = TAKEAWAYS[0].point
export const CH2_TAKEAWAY = TAKEAWAYS[1].point
export const CH3_TAKEAWAY = TAKEAWAYS[2].point

// The Introduction's takeaway — a QUESTION, the one the chapters answer
// (the director's design: the Introduction's last beat highlights the
// presenter's own paper, and the takeaway is the question itself — what
// is the character of the stress perturbation induced by a lake drainage?).
// It pops on the Introduction's last step (timeline2) over the
// highlighted Rines 2026 card. Deliberately NOT in TAKEAWAYS: the
// Conclusion lists the three chapters' lines only.
export const INTRO_TAKEAWAY = 'What is the character of the stress perturbation induced by a lake drainage?'
