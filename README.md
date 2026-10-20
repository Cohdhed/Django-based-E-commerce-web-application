# DevCircle: Django phone shop (rebuilt)

## Run it locally
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # optional: sample brands and phones built from the photos in seed_assets/ (add --reset to start over)
python manage.py createsuperuser    # for /admin/
python manage.py runserver
```
Open http://localhost:8000. Add your real products, logo, carousel images and banner in `/admin/`.

Your logo is `static/img/logo.png` (the Company profile in `/admin/` overrides it when you upload one). The default profile picture is `static/img/avatar.png`.

## Payments
- **Local development** (DEBUG on, no Paystack key): checkout uses a built-in demo that marks the order paid. It is switched off automatically when DEBUG is off.
- **Real payments**: set environment variables, then in the Paystack dashboard set the webhook URL to `https://YOUR-DOMAIN/paystack/webhook/`.
```
PAYSTACK_SECRET_KEY=sk_live_...
SITE_URL=https://your-domain.com
```
The amount is always calculated on the server, every payment is verified with Paystack before an order is marked paid, and the webhook covers customers who close the tab early.

## Production settings (environment variables)
```
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<long random string>
DJANGO_ALLOWED_HOSTS=your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com
```
Then `python manage.py collectstatic --noinput` (WhiteNoise serves the files). Uploaded images in `media/` need to be served by your web server (nginx etc.).

## Tests
`python manage.py test` runs 20 tests covering sign-up, login redirects, cart rules, totals and VAT, checkout, Paystack verification and webhook signatures, search/sort/pagination and 404 handling.

## Layout
- `home/`: catalogue (brands, phones, search, sort), about, contact, site-wide context
- `userprofile/`: accounts, profile, cart, checkout, payments, orders
- `templates/`, `static/css/style.css`, `static/js/index.js` and `login.js`: front end

## If the page looks unstyled
1. Run the server from inside THIS folder (the one containing `manage.py` and `static/vendor/`), not from an older copy of the project.
2. Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac). Browsers keep old stylesheets for the same address (127.0.0.1:8000).
3. Open DevTools (F12) > Network, reload, and look for red (404) rows. Every `/static/...` file should be 200.
Bootstrap and its icons now ship inside `static/vendor/`, so the site needs no CDN. Only the Google Fonts are fetched online, and the page falls back to a system font without them.
