// The Acknowledgements page's content: the groups of names, the
// split-out steps (one group per NEXT) and the parsing of a name line into
// what a face tile shows. The faces themselves live in ackHeadshots.gen.ts,
// written by cinematic/scene_acks/build_headshots.py from headshots.json.
// The page walks: an overview, one split-out step per group, then the
// full page again as the closing step.

// ── THE GROUPS ────────────────────────────────────────────────────────────
// The groups the director fills in. Coauthors are seeded from the papers'
// own author lists (factual); any group not yet written is a placeholder
// line, deliberately obvious, until it is replaced. Relationships are the
// director's to state — this file does not guess who advised whom.

/**
 * One name line: a plain string (the bare name), or the name with extras:
 *
 *   role         the relationship the director names for that person
 *                ("Second project advisor", "Master's advisor",
 *                "Undergrad thesis advisor"), printed under the face on
 *                the group's split-out step
 *   affiliation  where they are ("U. Oxford", "Princeton AOS")
 *
 * THE RULE (the director wanted the institutions out of the overview
 * cards and under the faces on the split-out instead): the OVERVIEW card
 * prints `name` only; the group's split-out step prints the role, then
 * the affiliation, small under the face. So `name` never carries a
 * parenthetical affiliation — that goes in `affiliation`. A nickname that
 * is part of the name stays in it ("Yue (Olivia) Meng").
 */
export type AckName = string | { name: string; role?: string; affiliation?: string }

/** The name line as the overview prints it (no role, no affiliation). */
export function ackNameText(n: AckName): string {
  return typeof n === 'string' ? n : n.name
}
/** The role the director gave that person, if any. */
export function ackNameRole(n: AckName): string | undefined {
  return typeof n === 'string' ? undefined : n.role
}
/** Their affiliation (split-out step only), if any. */
export function ackNameAffiliation(n: AckName): string | undefined {
  return typeof n === 'string' ? undefined : n.affiliation
}

export type AckGroup = {
  heading: string
  /** Names, or a single placeholder line while the group is unwritten. */
  names: AckName[]
  /** True while `names` is placeholder text rather than real names. */
  placeholder?: boolean
  /**
   * On the OVERVIEW only: this card sits under the previous group's card,
   * in the same grid cell, instead of taking a cell of its own (the
   * small "Earlier advisors" card under Fieldwork teammates keeps
   * the 4 × 2 grid). Its split-out step is unaffected.
   */
  stackUnder?: boolean
  /**
   * Its split-out step goes LAST (after every other group's), whatever its
   * place on the overview ("Internship mentors" shares the
   * Research groups column but is the final step, after Post-doc mentors).
   */
  stepLast?: boolean
  /**
   * The split-out step's ISOLATE-THEN-JOIN form (built for a beat on the
   * Fieldwork teammates row that isolates one face and then brings a
   * newcomer in): the step shows the group `withGroup` (by heading) again,
   * its faces faded back except `keep` (a name line of that group), and
   * this group's people join beside the kept face. The heading on the
   * step stays the other group's — it is the same row, one more beat.
   */
  isolate?: { withGroup: string; keep: string }
}

export const PUBLIC_GROUPS: AckGroup[] = [
  {
    heading: 'Committee and advisors',
    names: [
      'Prof. Ching-Yao Lai',
      'Prof. Dustin Schroeder',
      'Prof. Eric Dunham',
      'Prof. Ettore Biondi',
      // The role under the face is the project one ("Second project
      // advisor"), not the committee one (defense chair).
      { name: 'Prof. Jef Caers', role: 'Second project advisor' },
    ],
  },
  {
    heading: 'Coauthors',
    // The ESSD paper's authors (essd-2026-406), in the paper's order after
    // the director; then seven more coauthors in the order the director
    // listed them (Jef Caers here without the "Prof." — the slug, and so
    // the face, is the same).
    names: [
      'Ching-Yao Lai',
      'Ellianna Abrahams',
      'Michael G. Shahin',
      'Niall B. Coffey',
      'Eojin Lee',
      'Laura A. Stevens',
      'Yongji Wang',
      'Fiona Clerc',
      'Olivier Gagliardini',
      'James P. Hilditch',
      'Jonas Kloeckner',
      'David Zhen Yin', // was 'Zhen (David) Yin'; the headshot file keeps the old slug (headshots.json)
      'Jef Caers',
    ],
  },
  {
    heading: 'Research groups',
    // Named groups rather than a list of lab mates. Princeton AOS is
    // where the PhD began — its card carries the ACK_GROUP_PEOPLE list on
    // the split-out step.
    names: ['Stanford Icy Physics Group', 'Stanford Mineral-X', 'Princeton AOS'],
  },
  {
    // First names only, no photos (initials tiles). The card shares the
    // Research groups column on the overview (`stackUnder`) and its
    // split-out step comes after Post-doc mentors, the last of all
    // (`stepLast`).
    heading: 'Internship mentors',
    names: ['Stu', 'Allen'],
    stackUnder: true,
    stepLast: true,
  },
  {
    heading: 'Fieldwork teammates',
    names: [
      'Laura A. Stevens',
      'Meredith Nettles',
      'Stacy Larochelle',
      'Marianne Okal',
      'Nick Lau',
      // Mark Behn is last so his face sits at the far right of the
      // Fieldwork headshots.
      { name: 'Prof. Mark Behn', role: 'Master’s advisor' },
    ],
  },
  {
    // Not fieldwork teammates, so a group of their own: a small card under
    // Fieldwork teammates on the overview, and a step right after theirs.
    // The group began as an `isolate` step on the Fieldwork row (keep Mark
    // Behn lit, bring the undergrad advisor in beside him); the director
    // then asked for a plain group of the two, so Mark Behn appears here
    // as well as in the Fieldwork row and the isolate-then-join form is no
    // longer used by any group (the code still supports it).
    heading: 'Earlier advisors',
    names: [
      { name: 'Prof. Mark Behn', role: 'Master’s advisor' },
      { name: 'Prof. Aleksandar Diamond-Stanic', role: 'Undergrad thesis advisor' },
      // No profile picture and no link for this entry — an initials tile
      // (headshots.json).
      { name: 'Prof. Hong Lin', role: 'Undergrad academic advisor' },
    ],
    stackUnder: true,
  },
  {
    heading: 'External collaborators',
    // Olivier Gagliardini is also a coauthor — his IGE page gives the
    // affiliation ("Professor at University Grenoble Alpes").
    // Affiliations live in the `affiliation` field, not the name (overview
    // = names only; the step prints them under the faces).
    names: [
      { name: 'Prof. Laura A. Stevens', affiliation: 'U. Oxford' },
      { name: 'Prof. Leigh Stearns', affiliation: 'U. Penn' },
      { name: 'Prof. Ian Hewitt', affiliation: 'U. Oxford' },
      { name: 'Prof. Olivier Gagliardini', affiliation: 'U. Grenoble Alpes' },
    ],
  },
  {
    heading: 'Stanford Research Computing team',
    names: ['Ellianna Abrahams', 'Brian Tempero', 'Bob Clapp'],
  },
  {
    heading: 'Administrative staff',
    // Pandora del Carmen takes the department's spelling (lower-case
    // "del"). Anna Valerio is Princeton AOS's Department and Graduate
    // Administrator; her affiliation prints under her face on the step,
    // not on the overview card. The order is the director's (Pandora
    // between Clark and Cheryl).
    names: [
      'Liliane Pereira',
      'Jeremy Samos',
      'Clark Campagna',
      'Pandora del Carmen',
      'Cheryl Johnson',
      'Daniela Dimitrova',
      { name: 'Anna Valerio', affiliation: 'Princeton AOS' },
    ],
  },
  {
    // Replaces an earlier "Funding and facilities" placeholder. Sentence
    // case like the other headings (the overview's CSS upper-cases every
    // group head; the split-out title prints the heading as written).
    heading: 'Post-doc mentors',
    names: [
      'Ellianna Abrahams',
      'Yongji Wang',
      'Facu Sapienza',
      'Fiona Clerc',
      'Yue (Olivia) Meng',
      'Jonas Kloeckner',
      'Riley Culberg',
    ],
  },
]

/**
 * Under the Princeton AOS card on the Research-groups split-out step: a
 * small list of people, each with a small round headshot to the left of
 * the name in place of the bullet point. Keyed
 * by the Research-groups name line the list sits under; the faces come
 * from ACK_HEADSHOTS like everyone else's.
 */
export const ACK_GROUP_PEOPLE: Record<string, AckName[]> = {
  'Princeton AOS': ['Prof. Howard Stone', 'Prof. Jeroen Tromp', 'Prof. Stephen Griffies', 'Ming-Ruey Chou', 'Dr. Olga Sergienko'],
}

// No closing line sits under the groups: an earlier quotation there was
// removed at the director's request.

// ── THE SPLIT-OUT STEPS ───────────────────────────────────────────────────
// The director asked for a split-out phase of the acknowledgements that
// steps through with the NEXT button: each group in turn, with a publicly
// available professional headshot of each person. The page is a beat
// page on the site path (config/sitePath.ts BEAT_SECTIONS); the shared
// pills walk:
//
//   0 overview          the full page
//   1…n group-<i>       one group per NEXT, in PUBLIC_GROUPS order — every
//                       group with people (a `placeholder` group gets no
//                       step until it is written); the `stepLast` groups
//                       come after all the others. An `isolate` group's
//                       step is the isolate-then-join beat.
//   n+1 closing         the full page again; NEXT leaves along the path
//                       (the Repos page; Additional Work comes before
//                       this page)
//
// `?beat=N` deep-links to step N; `?beat=last` (BACK from Repos)
// lands on `closing`. The faces live in config/ackHeadshots.gen.ts, written
// by cinematic/scene_acks/build_headshots.py from headshots.json.

/** PUBLIC_GROUPS indices that get a split-out step, in page order — the
 *  `stepLast` groups after all the others. */
const ACK_STEP_GROUPS_ALL: number[] = PUBLIC_GROUPS.flatMap((g, i) =>
  g.placeholder || g.names.length === 0 ? [] : [i],
)
export const ACK_SPLIT_GROUPS: number[] = [
  ...ACK_STEP_GROUPS_ALL.filter((i) => !PUBLIC_GROUPS[i].stepLast),
  ...ACK_STEP_GROUPS_ALL.filter((i) => PUBLIC_GROUPS[i].stepLast),
]

export type AckStep =
  | { kind: 'overview' }
  | { kind: 'group'; group: number }
  | { kind: 'closing' }

export const ACK_STEPS: AckStep[] = [
  { kind: 'overview' },
  ...ACK_SPLIT_GROUPS.map((group) => ({ kind: 'group' as const, group })),
  { kind: 'closing' },
]

export type AckPerson = {
  /** As the page prints it (an AckName's `name`, minus a role prefix). */
  display: string
  /** The role under the face: an AckName's `role`, or a "Role: Name" prefix. */
  role?: string
  /** The affiliation under the face: an AckName's `affiliation`. */
  affil?: string
  /** Bare-name key into ACK_HEADSHOTS: no title, no middle initials. */
  slug: string
  /** Two letters for the initials tile. */
  initials: string
}

/**
 * Split one PUBLIC_GROUPS name line into what the split-out tile shows.
 * The affiliation is the structured `affiliation` field (it used to be a
 * trailing "(U. Oxford)" in the name string). A nickname inside the name
 * stays in it — "Yue (Olivia) Meng" prints as written and keys as
 * `yue-olivia-meng`. "David Zhen Yin" keys as
 * `david-zhen-yin` (its R2 object is still zhen-david-yin.jpg — headshots.json `file`).
 */
export function parseAckName(line: AckName): AckPerson {
  let s = ackNameText(line).trim()
  let role: string | undefined = ackNameRole(line)
  const affil: string | undefined = ackNameAffiliation(line)
  const roleM = /^([^:]+):\s*(.+)$/.exec(s)
  if (roleM) {
    role ??= roleM[1].trim()
    s = roleM[2].trim()
  }
  const bare = s.replace(/^(Prof\.|Dr\.)\s+/, '')
  // Middle initials ("Laura A. Stevens") are not part of the key.
  const words = bare.split(/\s+/).filter((w) => !/^[A-Z]\.$/.test(w))
  const slug = words
    .join(' ')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  const initials = (words[0]?.[0] ?? '') + (words.length > 1 ? words[words.length - 1][0] : '')
  return { display: s, role, affil, slug, initials: initials.toUpperCase() }
}
