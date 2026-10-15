// Fracture / stream mapping — the facts and links behind the Additional
// Work card and its door, /additional-work/fracture.
//
// The work: AGU Fall Meeting 2024 poster C41D-0203. Iona Xia led it
// (first author; Stanford CS undergraduate, SESUR summer 2024 in the Icy
// Physics group); the presenter mentored.
//
// PROVENANCE — every number below was read off a notebook OUTPUT in the
// research repository's streams-vs-fractures/notebooks/ (not in this tree):
//   design_train_model.ipynb, cell 8 (0-based), printed:
//     "train size[11543]; val size[1650]; batch size[16]" and
//     "epoch[100/100]"
//   design_train_model.ipynb, cell 23, printed: "AUC =  0.9581615990684065"
//     — the ROC curve of the FRACTURE output on the VALIDATION tiles.
//   design_train_model.ipynb, cell 2 / create_visualization.ipynb, cell 7:
//     UNet(in_channels = 1, out_channels = 2), 256 x 256 tiles.
//   create_visualization.ipynb, cell 8: the training visualisation walks
//     the checkpoints of epochs 1-60 over a 10 x 10 block of tiles
//     (printed "100" per epoch).
// NOT shown, on purpose: the F1 scores (~0.51 fracture, ~0.56 stream).
//   They exist only as numbers typed into cell 30's source, no output
//   prints them, and cell 26's f1_threshold() averages training and
//   validation tiles together.
//
// IMAGERY: WorldView-1 / QuickBird-2 panchromatic, ~0.5 m, Jul-Aug 2012,
// northwest Greenland (the Culberg et al. 2022 GRL scenes) — commercial
// Maxar imagery via the Polar Geospatial Center. Every derivative carries
// "Imagery © Maxar" in its pixels; only web-resolution crops and
// overlays are served, never a raw scene.

import { mediaUrl } from './media'

export const FRACTURE = {
  title:
    'High-resolution mapping of ice surface fractures and streams using a deep convolutional neural network',
  venue: 'AGU Fall Meeting 2024',
  poster: 'C41D-0203',
  authors: ['I. Xia', 'J. H. Rines', 'C.-Y. Lai', 'R. Culberg'],
  boldAuthor: 'J. H. Rines',
  imagery: 'WorldView-1 · QuickBird-2 · northwest Greenland · Jul–Aug 2012',
  credit: 'Imagery © Maxar',
}

/** The two classes, in the colours the visuals are drawn in. */
export const FRACTURE_CLASSES = [
  { name: 'Fractures', color: '#ff3030' },
  { name: 'Streams', color: '#4078ff' },
]

export const FRACTURE_TILES = [
  { value: '0.5 m', label: 'panchromatic imagery' },
  { value: '11,543', label: 'training tiles · 256 × 256' },
  { value: '1,650', label: 'validation tiles' },
  { value: '0.958', label: 'fracture ROC AUC · validation' },
]

/** The training visualisation: 59 frames at 5 fps, checkpoints of epochs 1–60. */
export const FRACTURE_TRAINING = {
  video: mediaUrl('addl/fracture/training_epochs.mp4'),
  poster: mediaUrl('addl/fracture/training_epochs_poster.jpg'),
  label: 'Training · epochs 1–60',
  panel: 'One block · 10 × 10 tiles',
}

/** The whole-scene result: scene → fractures → streams → both. */
export const FRACTURE_SCENE = {
  video: mediaUrl('addl/fracture/scene_maps.mp4'),
  poster: mediaUrl('addl/fracture/scene_maps_poster.jpg'),
  panel: 'One whole scene',
}

export interface FractureLink {
  label: string
  href: string
  primary?: boolean
}

export const FRACTURE_LINKS: FractureLink[] = [
  {
    label: 'AGU abstract',
    href: 'https://agu.confex.com/agu/agu24/meetingapp.cgi/Paper/1598183',
    primary: true,
  },
  // Iona's LinkedIn — matched on name + Stanford + CS + a Stanford Doerr
  // School of Sustainability entry (SESUR's home); Stanford Profiles lists
  // one Iona Xia. No GitHub account could be tied to her (ionaxia,
  // ionaxia2013, ionaxia18 are all blank profiles) — none is linked.
  { label: 'Iona Xia · LinkedIn', href: 'https://www.linkedin.com/in/iona-xia/' },

  // ── DISABLED: the code repository ────────────────────────────────────
  // Do NOT enable until the Labelbox API keys hard-coded in two of the
  // repository's notebooks have been revoked and removed from its
  // history. Then uncomment:
  // { label: 'Code', href: 'https://github.com/<org>/<repo>' },
]
