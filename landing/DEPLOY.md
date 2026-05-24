# Deploy the landing page

Static landing for `gold-mcp`. Three files, ~30 KB total. Drop them on
any web server — Apache, nginx, GitHub Pages, Netlify, Vercel, S3, or
a directory on your existing VPS.

```
landing/
  index.html
  styles.css
  script.js
```

## Option A — drop into an existing site at /mcp

If `pthaicapital.io.vn` already serves files from a directory on your
VPS, just put the three files in a new subdirectory:

```
/var/www/pthaicapital.io.vn/public/
  index.html              # your existing site
  mcp/
    index.html            # gold-mcp landing
    styles.css
    script.js
```

Then visit `https://pthaicapital.io.vn/mcp` to verify.

No additional config needed. nginx / Apache will serve the static
files directly.

### nginx (only if you don't already have a default static handler)

```nginx
location /mcp/ {
    alias /var/www/pthaicapital.io.vn/public/mcp/;
    try_files $uri $uri/ $uri/index.html =404;
}
```

### Apache `.htaccess`

```
DirectoryIndex index.html
```

## Option B — GitHub Pages (free, no VPS)

```bash
# from the repo root
cd landing
git checkout -b gh-pages
git add .
git commit -m "Add landing page"
git push origin gh-pages
```

Then in **Settings → Pages**, select branch `gh-pages` and folder
`/ (root)`. URL: `https://thaitrevor.github.io/gold-mcp/`.

## Option C — Netlify / Vercel (free)

Both auto-detect static sites. Connect the repo, point the publish
directory at `landing/`, deploy.

## Wire up the email waitlist

The form in `index.html` posts to a Formspree placeholder. To make it
work:

1. Create a free account at https://formspree.io (50 submissions/month).
2. Create a new form, copy the form endpoint (looks like
   `https://formspree.io/f/xyzabc123`).
3. Edit `index.html`, find the line:
   ```html
   <form class="waitlist-form" action="https://formspree.io/f/YOUR_FORMSPREE_ID" method="POST">
   ```
4. Replace `YOUR_FORMSPREE_ID` with your real form ID.
5. Re-upload `index.html`.

Alternative providers (all free tier, same drop-in pattern): Tally,
Buttondown, ConvertKit landing pages.

## Customize

- **Brand color** — edit `--accent` and `--accent-soft` in `styles.css`.
- **GitHub URL** — search-replace `ThaiTrevor/gold-mcp` if you fork.
- **Pricing** — edit the `.pricing` section in `index.html`.
- **OG image** — add `og-image.png` (1200x630) next to `index.html`
  and add `<meta property="og:image" content="og-image.png">` in the
  head. Improves Twitter / Discord link previews.
