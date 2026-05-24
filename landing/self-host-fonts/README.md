# Self-host fonts (privacy + perf)

Replaces the Google Fonts external link on your landing page with
local woff2 files. Saves a third-party round-trip on every visit and
keeps visitor IPs out of Google's logs (relevant for GDPR if any EU
visitor lands on the page).

## Why

The default Google Fonts setup loads CSS from `fonts.googleapis.com`
and font files from `fonts.gstatic.com`. Every visitor:

- Performs DNS resolution + TLS handshake to two extra domains
- Has their IP logged by Google as part of the font request
- Gets blocked from the page render until the font CSS arrives

Self-hosting the fonts:

- Removes the two DNS+TLS round-trips
- Keeps visitor IPs on your origin only
- Lets Cloudflare cache the woff2 files like everything else

## What this folder produces

- `fonts/*.woff2` — JetBrains Mono (400/500/700) and Space Grotesk
  (400/500/600/700), latin + latin-ext + vietnamese subsets only.
  About 150-200 KB total across ~15 small files.
- `fonts.css` — `@font-face` rules pointing at the local files,
  identical typography to the Google Fonts version.

## Run it

Requirements: `bash`, `curl`, `python3` (any modern Python).

```bash
cd landing/self-host-fonts
bash download.sh
```

The script:

1. Fetches the current Google Fonts CSS with a Chrome user-agent
   (otherwise Google serves TTF instead of woff2).
2. Filters to the three subsets your landing actually needs.
3. Downloads each woff2 to `fonts/`.
4. Writes `fonts.css` with the local URLs.

Re-run any time to refresh — it skips files that already exist.

## Deploy

1. Upload `fonts/` and `fonts.css` to your web root so they're served
   from `/fonts/*` and `/fonts.css` respectively. With the example
   layout used by `pthaicapital.io.vn`, that means:

   ```
   /var/www/pthaicapital.io.vn/public/
     fonts.css
     fonts/
       jetbrains-mono-400-latin.woff2
       ...
   ```

2. In your landing HTML, replace the Google Fonts links:

   ```html
   <!-- delete these two preconnect lines -->
   <link rel="preconnect" href="https://fonts.googleapis.com" />
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />

   <!-- delete this stylesheet -->
   <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono..." rel="stylesheet" />

   <!-- add this -->
   <link rel="stylesheet" href="/fonts.css">
   ```

3. (Optional) Add a long-cache header for `/fonts/`:

   ```nginx
   location /fonts/ {
       expires 1y;
       add_header Cache-Control "public, immutable";
       try_files $uri =404;
   }
   ```

## Verify

After deploy:

- Open the page in DevTools → Network → filter by `woff2`. Requests
  should go to your domain only, not `fonts.gstatic.com`.
- `curl -I https://yourdomain/fonts.css` should return 200 + a
  long `Cache-Control` header (if you added it).
- Run the page through Lighthouse — "Eliminate render-blocking
  resources" should improve.

## CSP impact

If your CSP currently has `font-src 'self' https: data:`, you can
tighten to `font-src 'self' data:` after self-hosting — drop the
broad `https:` allowance for fonts.
