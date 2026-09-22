# Moving to a new MacBook

About 15 minutes, most of it waiting on downloads. You don't need Homebrew or an admin password.

1. **Install the Claude desktop app** on the new Mac and sign in.
2. **Open Claude → Code**, pick your Documents folder, and paste this:

   > Clone my GitHub repo `collier-vibe-editing` into ~/Documents/vibe-editing, run `./setup-mac.sh`,
   > then install the plugin from that folder. Read HOUSE-RULES.md and CLAUDE.md before anything else.

   Claude does the rest. If GitHub asks you to sign in, do it in the browser window it opens.
3. **Add your Groq key.** It isn't in the repo, on purpose. Get it from console.groq.com → API Keys
   (or copy it from the old Mac: `plugins/vibe-editing/config/keys.env`) and ask Claude to put it in.
4. **Test.** Drop any video into `00_INBOX` and ask Claude to clip it.

## What comes with the repo
- The whole editing kit, with the fixes made on the old Mac.
- Both brands: `brand/profiles/facility-coach.json` and `collier-buttgen.json`, plus the logos and fonts.
- Every caption preset (`fc-*`, `collier-*`, `room-*`) and all the caption fonts.
- `HOUSE-RULES.md`, every correction you've given Claude, so the new Mac follows the same standards.
- `recipes/`, the exact pipelines behind the webinar ads and the workshop reels.

## What does NOT come with it (on purpose)
- Your footage and finished clips (`00_INBOX/`, `projects/`). They're too big for GitHub and include
  client calls. Copy these over separately (AirDrop or an external drive) if you want them.
- API keys (`keys.env`).
