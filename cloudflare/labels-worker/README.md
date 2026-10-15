# labels-worker — SUBMIT for "Label lakes yourself"

The door at `/additional-work/label` lets a visitor label the ESSD
inter-rater 200 and SUBMIT under a name. GitHub Pages cannot write to R2 (and
R2 keys must never ship in the site's bundle), so the page POSTs the labels
to this Cloudflare Worker, which is bound to the `<bucket>` bucket and
keeps ONE CSV per labeler — always their latest full set of lakes:

```
labels/irr/<name-slug>_<16 hex>.csv     e.g. labels/irr/jane-doe_3f9a0c1d7e2b4a65.csv
```

in exactly the lakelabel GUI's format (the six `irr_labels_labeler<k>_CW_<year>.csv`):

```
lake_id,label,p_ND,p_HF,p_MD,p_LD,p_CD,notes,flagged
CW2018_1077,LD,0.25,0.0,0.0,0.75,0.0,"streams out, ""maybe"" a moulin",False
CW2019_1883,MD,0.0,0.0,1.0,0.0,0.0,,False
```

`label` is the hard argmax (a tie goes to the lower class, the paper's rule),
probabilities are quarters summing to 1, CRLF line ends. The CSV is built by
the Worker from `website/src/config/irrCsv.ts` (the page imports the same
file for the name rule). The object's custom metadata: `name` (the full
name, URL-encoded — the key carries only its ASCII slug), `rows`, `saved`
(ISO time of the last write) and `tokenHash`.

**No download, ever** (the director ruled out the browser's save-file box as
an option for the visitor; the button says "submit", not "save"; and a name
entered twice gets the sentence "labeler with that name already exists, use
a different name"). A failed POST leaves the rows on the page
and SUBMIT pressable again (`not submitted · <status>`; a 429 waits out its
`retryAfter` first). With `LABELS_ENDPOINT` empty the door shows no
name/SUBMIT row at all.

## One name, one labeler, one file

- **Names are compared by slug** (`nameSlug`: lower-case, diacritics folded,
  runs of anything else → `-`, ≤ 40 characters), so "Jane Doe", "jane
  doe" and "Jäne-Doe" are the same labeler. A slug has no `_`, so the
  existence check is exact: `list({prefix: 'labels/irr/<slug>_'})` filtered
  to `^<slug>_[0-9a-f]{16}\.csv$` (`jane` never finds `jane-doe_…`).
- **First SUBMIT under a free name** → `200 {key, rows, token}`: a new key, and
  `token` = 32 random hex whose SHA-256 is stored as `tokenHash`.
- **The same name again without that token** (another visitor, or the same
  one after a reload) → **409** `{error: "labeler with that name already
  exists, use a different name", field: "name"}`; the page shows that
  sentence under the name field.
- **The owner again** (`{name, rows, token}`, sha256(token) = the file's
  `tokenHash`) → `200 {key, rows}`: the SAME key overwritten with every row.
  The page keeps the token in memory only (no storage): a reload forgets it,
  and that visitor then needs a new name.
- **A name with no a-z/0-9** (e.g. "李明", "!!!", "anon" — all slug to `anon`)
  → **400** `{field: "name"}` (the page shows the same sentence). Refused
  rather than first-come: one visitor holding `anon` would otherwise block
  every later non-Latin name.
- A same-instant race (two first SUBMITs of one new name within a few ms)
  can leave two files under one slug; each owner's token still finds its
  own file. Not worth a lock at this scale.


## Deploy (one time)

```
cd cloudflare/labels-worker && npx wrangler login && npx wrangler deploy
```

`wrangler login` opens the browser for the Cloudflare account that owns
`<bucket>` — run it in a terminal ON the machine with the browser and click
Allow within ~2 minutes (the OAuth callback goes to `localhost:8976` on the
machine running wrangler; from a remote session it times out). No browser
at hand: create an API token (dash → My Profile → API Tokens → the *Edit
Cloudflare Workers* template) and run `CLOUDFLARE_API_TOKEN=<token>
CLOUDFLARE_ACCOUNT_ID=<your-account-id> npx wrangler deploy`
instead of the login. `deploy` prints the Worker's URL, something like
`https://defense-labels.<your-subdomain>.workers.dev`. Paste it into

```
website/src/config/essdLabel.ts  →  export const LABELS_ENDPOINT: string = 'https://defense-labels.<…>.workers.dev'
```

then commit and push (the site redeploys). That is all: no secrets, no keys
in the bundle — the bucket binding lives in the Worker.

## Reading the submissions

```
rclone lsf r2:<bucket>/labels/irr/                  # one <slug>_<tag>.csv per labeler
rclone copy r2:<bucket>/labels/irr/ ./irr_visitor_labels/
rclone lsjson --metadata r2:<bucket>/labels/irr/    # + name, rows, saved
```

Never run `rclone cat`/`deletefile` on a key you have not validated
(`^labels/irr/[a-z0-9-]+_[0-9a-f]{16}\.csv$`): an EMPTY key is the whole
bucket.

## Local test (no login needed)

```
cd cloudflare/labels-worker
npx wrangler dev --port 8787            # R2 is simulated locally (.wrangler/state)
curl -i -X POST http://127.0.0.1:8787/ \
  -H 'Origin: http://localhost:5174' -H 'Content-Type: application/json' \
  -d '{"name":"Test","rows":[{"lake_id":"CW2018_1077","p_ND":0,"p_HF":0,"p_MD":0,"p_LD":1,"p_CD":0}]}'
#   → {"key":"labels/irr/test_<16 hex>.csv","rows":1,"token":"<32 hex>"}
#   the same again → 409; again with ,"token":"<32 hex>" (after 10 s) → the same key, overwritten
npx wrangler r2 object get <bucket>/labels/irr/<key from the reply> --local --pipe
```

To try the page against it, set `LABELS_ENDPOINT` to `http://127.0.0.1:8787/`
in a local edit (do not commit that). Plain-node checks of the pure parts
(including a byte-for-byte round trip of the labelers' six CSVs) and of the
whole Worker on an in-memory bucket (create → 409 → overwrite with the
token, the slug rules, the limits):

```
npx esbuild test/csv.test.ts --bundle --platform=node --format=esm --outfile=.wrangler/csv.test.mjs && node .wrangler/csv.test.mjs
```

## What it refuses

| status | when |
|---|---|
| 403 | an `Origin` other than `https://jharlanr.github.io` or `http://localhost:<port>` / `http://127.0.0.1:<port>` |
| 405 | anything but `POST` (and the `OPTIONS` preflight) |
| 415 | a body that is not `application/json` |
| 413 | a body over 64 KB |
| 400 | invalid JSON or fields: name 1–60 characters, 1–200 rows, ids from the inter-rater 200 (`src/irr_lake_ids.json`), each id once, probabilities 0 / 0.25 / 0.5 / 0.75 / 1 summing to 1, notes ≤ 200 characters, `flagged` true/false, `token` 32 lower-case hex if present, no other fields; and (`field: "name"`) a name with no a-z/0-9 |
| 409 | the name's slug already has a file and the request carries no token, or the wrong one (`field: "name"`) |
| 429 | a second name lookup from the same IP within 1 s, or a second WRITE within 10 s (`retryAfter` in seconds, also `Retry-After`; remembered per Worker isolate — crude on purpose). A 409 is not a write, and a taken name gets its 409 even inside another write's 10 s |

The Origin check stops other web pages, not a determined script; the
validation, the size cap and the rate limit bound what such a script could
write (≤ 64 KB of well-formed CSV per 10 s per IP) and look up (one R2
list per second per IP). Behind one shared address (a room on one NAT) the
10 s is shared too: a second visitor's SUBMIT inside it shows
`not submitted · 429` and is pressable again after the wait.

Privacy: `<bucket>` is the site's PUBLIC bucket (r2.dev), but r2.dev
never lists objects and every file's name ends in 64 random bits, so a CSV
can be read only by someone who already holds its exact key. What the 409
does reveal, by design, is whether a name has been used. The token is never
stored, only its SHA-256. For a truly private bucket:
`npx wrangler r2 bucket create defense-labels`, change `bucket_name` in
`wrangler.toml`, and read the saves from the Cloudflare dashboard.
