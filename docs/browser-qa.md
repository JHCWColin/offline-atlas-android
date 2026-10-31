# Offline browser QA

`tools/qa_modeldial.cjs` runs the unmodified captured Radar HTML and all its
dependencies from the manifest in a desktop Chromium browser. It starts a
temporary server on `127.0.0.1:18092`, following the Android container's exact-URL
then pathname lookup. Every request to an external origin is fulfilled from
the local manifest through Playwright interception. Uncaptured requests get
HTTP 404; there is no online fallback.

This verifies snapshot dependency coverage and modern-browser interactions.
It does **not** replace APK testing on Android 8.1 or directly test GeckoView's
WebExtension implementation. Desktop Chromium and GeckoView are different
engines.

## Requirements and execution

Install Node.js, the `playwright` Node package, and Chrome or another compatible
Chromium browser. The package must be resolvable by Node (local `node_modules`
or `NODE_PATH`). This script uses the installed browser rather than downloading
Playwright's browser. On Windows, its default browser path is
`C:\Program Files\Google\Chrome\Application\chrome.exe`.

```powershell
# Set only if the installed browser is at another path.
$env:CHROME_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
# Optional: use another loopback port if 18092 is occupied.
$env:OFFLINE_QA_PORT = '18092'
node tools/qa_modeldial.cjs
```

In the Codex desktop runtime used to create this snapshot, Playwright was
provided by the bundled dependency directory reported by
`load_workspace_dependencies`. Set `NODE_PATH` to that returned
`dependencies\node\node_modules` directory when using the bundled package.

Outputs:

- `qa/modeldial-desktop.json`: browser version, requested URLs, interaction
  results, missing resources, console errors and uncaught page exceptions.
- `qa/modeldial-radar-desktop.png`: initial 1280×720 landscape view.
- `qa/modeldial-chart-desktop.png`: performance/cost view at the same size.

The command returns a nonzero status if resources are missing, page/console
errors occur, or any required interaction fails. The covered interactions are
all six score axes, the performance/cost chart, model search, and switching
from Chinese to English while retaining the view state.

## Actual Firefox WebExtension routing

`tools/qa_modeldial_gecko.py` loads the application's actual `bridge/` extension
as a temporary add-on in a separate headless desktop Firefox profile. This
uses Firefox's real `webRequest.onBeforeRequest` redirect implementation rather
than Playwright's request fulfillment.

It deliberately sets a dead proxy at `127.0.0.1:9` for all non-loopback traffic.
Successful cross-origin JSON requests therefore require the extension to
redirect them to the local server. It checks all six Radar axes, explicitly
fetches the two `reference.modeldial.com` JSON endpoints, and records actual
`/_remote/https/...` server hits. The default local server port is 18082 to
match the application's extension configuration; keep that port available.

Install Firefox and download Mozilla's `geckodriver` for your operating system
from <https://github.com/mozilla/geckodriver/releases>. The Python package
`requests` is also required. No browser or driver is downloaded by the script.

```powershell
python tools/qa_modeldial_gecko.py --driver C:\tools\geckodriver.exe
```

Use `--firefox` if Firefox is installed at another path. The default Windows
path is `C:\Program Files\Mozilla Firefox\firefox.exe`. The script can also
use a driver cached at `tools/.cache/geckodriver.exe` (this binary is ignored
by Git).

Outputs are `qa/modeldial-firefox.json` and `qa/modeldial-firefox.png`.
This test passed with desktop Firefox 154.0, including the actual extension
redirects, with no missing resources and external network traffic blocked.
It provides additional Gecko evidence, while Android GeckoView 140 still
requires its own APK installation and runtime check.

## Static integrity

```powershell
python tools/verify_offline.py --strict
```

The static checker verifies hashes and dependency references. Browser QA is
also necessary because runtime URL construction cannot always be inferred
from source text alone.

## Refreshing the ModelDial snapshot

```powershell
python tools/mirror_modeldial.py --help
# Keep the existing snapshot after validating all resource hashes (no network).
python tools/mirror_modeldial.py
# Explicitly replace the snapshot with a fresh download.
python tools/mirror_modeldial.py --refresh
```

Re-run integrity and browser QA after an explicit refresh. Original captured
HTML, CSS and JavaScript stay byte-for-byte intact; routing belongs to the
application container.
