# JV Visual Studio

Static Three.js architectural showcase, with English/Kannada, two visual designs, three 3D scenes, rendered films, and WhatsApp enquiries.

## Local development in VS Code

Open this repository folder in VS Code. Install Node.js 22 or newer (including npm) and Python 3. No npm dependencies are required for the website build.

```powershell
npm ci
npm test
npm run dev
```

Open http://127.0.0.1:5173/ and http://127.0.0.1:5173/look-2.html. Stop the server with Ctrl+C. Always use HTTP; opening HTML directly with `file://` prevents module/model loading.

Edit `site/assets` for frontend code and styles, then rerun `npm run build` (or restart `npm run dev`). The build copies these files into `dist/assets`, removes obsolete preview-only module references from page data, checks JavaScript syntax, and validates packaged images, films, models, environments, textures, imports, and filename case. The build uses only Node.js; Python is used solely for the local server.

The two `dist/*.html` files and binary media are committed release inputs. For page copy/layout changes, edit these HTML files directly. Both styles must be updated where applicable. The older root HTML/media files are preserved for history; they are not the deployment output.

## GitHub → Vercel

1. Import this GitHub repository into Vercel and select `codex/vercel-ready` as the production branch if deploying this version without merging into `main`.
2. Use repository root (`.`), framework **Other**, build command `npm run build`, and output directory `dist`. These settings are also in `vercel.json`. Use Node.js 22 or newer.
3. No environment variables, database, backend, or Blender installation are needed. Do not set `site/build.py` as the deployment command.
4. After deployment, test `/` and `/look-2.html`, scroll through all scenes, and check a film and WhatsApp enquiry. Future pushes to the selected production branch trigger production deployments; other branches receive previews according to the Vercel project's Git settings.

GitHub Actions runs `npm ci`, the loading/retry tests, and the deployment build on pushes and pull requests. Missing asset URLs should return 404, not the home page; no catch-all rewrite is configured. Asset names are not fingerprinted, so no long-lived immutable cache policy is applied.

## Browser acceptance checks

- At desktop and mobile widths, check both looks, all three scenes, and the house's plan-to-building sequence.
- Toggle Kannada/English and sound; test orbit drag/zoom and Escape; open/close a film and inspect the prefilled WhatsApp message without sending it.
- Block a scene model or HDR request, reload, and scroll to its chapter. The previous scene must disappear, a failure message and Retry button must appear, and loading must not repeat automatically. Unblock the request and use Retry to recover.
- Block a plant GLB: the building must still render and a plant warning should appear in the console.
- Disable WebGL: rendered images, films, text, and contact actions must remain accessible. Test reduced-motion mode too.

## Offline Blender pipeline

`blender`, `plants`, `pbr`, `site/build.py`, and the GLB postprocessors are retained as offline source material. They still reference the original `/home/claude/jv5` environment. Full regeneration additionally requires missing raw assets, blend files, render/bake outputs, material-library JSON, and the glTF processing dependencies. Restoring that pipeline is separate from deploying the supplied release assets. Do not run it against this deployment until those inputs and paths have been restored.
