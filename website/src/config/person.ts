// The presenter's own links: the three icon buttons in the
// top-right of the splash. Kept here rather than inline so the People
// registry can point at the same URLs. The avatar is the GitHub
// profile picture — the same image the personal site features — pulled
// straight from GitHub so it follows the profile if that changes.
export interface PersonalLink {
  id: 'linkedin' | 'github' | 'site'
  label: string
  href: string
}

export const PERSONAL_LINKS: PersonalLink[] = [
  { id: 'linkedin', label: 'LinkedIn', href: 'https://www.linkedin.com/in/joshua-h-rines/' },
  { id: 'github', label: 'GitHub', href: 'https://github.com/jharlanr' },
  { id: 'site', label: 'jharlanr.github.io', href: 'https://jharlanr.github.io/' },
]

/** GitHub avatar (user id 31021692 = jharlanr), served at 160 px. */
export const AVATAR_URL = 'https://avatars.githubusercontent.com/u/31021692?v=4&s=160'
