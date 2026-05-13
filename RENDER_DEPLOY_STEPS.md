# JYOTISH 3.0 Render Deployment Steps

## 1. Fix The Mobile Google Login Error

Your screenshot shows:

```text
Error 400: redirect_uri_mismatch
```

That means Google blocked the phone login because the callback URL sent by the app is not listed in Google Cloud OAuth settings.

This project now uses one fixed mobile callback page:

```text
https://jyotish-astro-app.onrender.com/google-mobile-callback.html
```

If your Render URL is different, use your real URL with `/google-mobile-callback.html`.

## 2. Prepare GitHub

Run:

```bat
PREPARE_RENDER_DEPLOY.bat
```

This stages the app, copies `backend\astro.db` to `backend\astro_seed.db` for first Render deploy, commits, and pushes to GitHub.

## 3. Create Render Services

Best option:

1. Open `https://dashboard.render.com/`
2. Login using the account connected to `devanand2008@gmail.com`
3. Click `New +`
4. Click `Blueprint`
5. Connect the GitHub repository
6. Select branch `main`
7. Confirm blueprint file `render.yaml`
8. Click `Apply`

Render creates:

```text
jyotish-astro-app
jyotish-video-signaling
```

If you create the Python service manually, use these exact values:

```text
Root Directory: leave blank
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

If Render shows this error:

```text
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'
```

it means Render is building from the repo root while your old command was looking for `requirements.txt` in the wrong folder. Use:

```text
pip install -r backend/requirements.txt
```

not:

```text
pip install -r requirements.txt
```

For the video service, use:

```text
Root Directory: leave blank
Build Command: cd backend-video && npm ci
Start Command: cd backend-video && npm start
Health Check Path: /health
```

## 4. Google Cloud OAuth

Open Google Cloud Console:

```text
https://console.cloud.google.com/apis/credentials
```

Open OAuth Client:

```text
1055510399803-bv8vphrhlam8cn5uljii5cs8ghubcuvl.apps.googleusercontent.com
```

Add Authorized JavaScript origins:

```text
http://localhost:8080
https://jyotish-astro-app.onrender.com
```

Add Authorized redirect URIs:

```text
https://jyotish-astro-app.onrender.com/google-mobile-callback.html
```

Save. Wait 2-5 minutes, then test on mobile again.

## 4A. If The Same Error Repeats

If mobile still shows:

```text
Error 400: redirect_uri_mismatch
```

do this exact check:

1. On the Google error page, tap `error details`.
2. Find the value named `redirect_uri`.
3. Copy that full URL exactly.
4. Paste it into Google Cloud Console under `Authorized redirect URIs`.
5. Save and wait 2-5 minutes.

The value must match character-for-character. These are different URLs to Google:

```text
https://jyotish-astro-app.onrender.com/google-mobile-callback.html
https://jyotish-astro-app.onrender.com/login.html
https://jyotish-astro-app.onrender.com/
http://192.168.1.5:8080/google-mobile-callback.html
```

For production/mobile testing, use the Render HTTPS URL. Avoid phone LAN URLs like `http://192.168.x.x:8080` for Google login; use Render or an HTTPS tunnel.

Do not paste private IP URLs into Google Cloud OAuth:

```text
http://10.60.238.176:8080/login.html
http://192.168.1.5:8080/login.html
```

Google will reject them with:

```text
Invalid redirect: Must end with a public top-level domain
Invalid Redirect: must use a domain that is a valid top private domain
```

That is expected. Private network IPs are not valid OAuth redirect domains for mobile Google login. Use one of these instead:

```text
https://jyotish-astro-app.onrender.com/google-mobile-callback.html
https://YOUR-NGROK-NAME.ngrok-free.app/google-mobile-callback.html
https://YOUR-CLOUDFLARE-TUNNEL.trycloudflare.com/google-mobile-callback.html
```

Also check these common mistakes:

- You edited the wrong Google Cloud project or wrong OAuth Client ID.
- The OAuth Client ID in Google Cloud is not the same as `GOOGLE_CLIENT_ID` in Render.
- You added the callback under `Authorized JavaScript origins` only. It must be in `Authorized redirect URIs`.
- The app is still deployed with old code. Redeploy Render after pushing GitHub changes.
- Your Render service URL is different from `jyotish-astro-app.onrender.com`.
- You added a trailing slash or a different path.

## 5. Test

Open:

```text
https://jyotish-astro-app.onrender.com/login.html
```

Use Google login with:

```text
devanand2008@gmail.com
```

That account becomes Admin automatically.

## 6. Existing DB Data

Local DB file:

```text
backend\astro.db
```

First Render deploy seed file:

```text
backend\astro_seed.db
```

On first start, Render copies `astro_seed.db` into the persistent disk at:

```text
/opt/render/project/src/data/astro.db
```

After that, Render keeps database changes on the persistent disk.
