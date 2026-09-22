# Caption style references (from Collier, 2026-08-26)

Source: ~19 screenshots pasted into Claude Code. The image files were not saved to disk —
this is the written read of them. Drop the originals into this folder any time to extend it.

## Style families observed

| # | Look | Seen in | Kit support |
|---|---|---|---|
| 1 | Clean lowercase white sans, soft shadow | "if you're going through", "so everyone wants to" | full |
| 2 | White base + **bold** key words | "when you add an **anchor** by", "you need to sell the expensive thing" | full (weight ladder) |
| 3 | Italic for quotes / contrast | "I was *vehemently*", "*make more money*", "Time on list vs Time on brand" | full (`italic_fax` shear) |
| 4 | Heavy condensed UPPERCASE | "YOU MORE", "A BETTER OFFER", "IF 99.999%" | full (Bebas / Anton / Archivo Black) |
| 5 | Multi-line uppercase headline block | "THIS ONE RULE / CHANGED OUR / MARRIAGE" | partial — engine caps at <=3 words & <=18 chars per cue |
| 6 | Colored highlight box behind a word | "Stop `Preaching` The Same Thing" | via `bubble`, but box covers the WHOLE cue — isolate the word into its own cue |
| 7 | Solid box, dark text, colored key phrase | "I MADE $106 MILLION AND THEN MY **MUM DIED**" (red) | box: yes. Per-word color inside: yes |
| 8 | Second-color voice/accent line | yellow "DISCLAIMER:", gold "how do you **decide**" | full (per-voice color) |
| 9 | Handwritten marker + arrow | "SICK OF STARING AT A BLANK SCREEN?" | NOT a caption style — that's a thumbnail/cover treatment. Caveat/Pacifico are bundled if wanted |

## Constraints worth knowing
- Captions are chunked to **<=3 words and <=18 characters**, hard-broken at every `.?!` and `,`.
  Long headline blocks (#5) are a cover-card treatment, not a running caption.
- A **size bump only lands on a single-word cue** — mixed sizes inside one line read broken.
- Bebas Neue and DM Sans ship as **one weight each**, so they cannot drive the bold-emphasis
  ladder. With those, emphasis must come from color / size / box instead.
- Montserrat (10 weights) and Poppins (4) are the only bundled families with a real ladder.
