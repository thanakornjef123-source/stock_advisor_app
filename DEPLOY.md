# Publishing the terminal as a website

Streamlit Community Cloud hosts this for free and gives it a permanent public
URL, so anyone with the link can use it — no install, no account.

The repository content is verified and ready: **62 files, 24 MB**, nothing over
GitHub's limits. A clean checkout with no local state was tested and all
thirteen pages rendered. `.gitignore` keeps the virtual environment and your
personal `user_data.json` off the internet.

Two steps need your own credentials — signing in to GitHub, and signing in to
Streamlit. Nobody else can do those for you.

---

## Step 0 · Move the project out of OneDrive first

**Do not skip this.** The project currently lives under
`C:\Users\Asus\OneDrive - KMITL\Desktop\`. OneDrive syncs every file write to
the cloud, and Git writes hundreds of small internal files very quickly. The two
fight each other. This already happened during setup: an attempt to create the
repository in place produced a `.git\config` filled entirely with null bytes and
a half-built folder Git refused to open.

In File Explorer:

1. Create a folder outside OneDrive, for example `C:\Projects`.
2. Copy the whole `stock_advisor_app` folder into it, giving you
   `C:\Projects\stock_advisor_app`.
3. In the **new copy**, turn on `View` → `Show` → `Hidden items` and delete the
   `.git` folder if it came across. It is not a working repository and will only
   confuse GitHub Desktop.

Keep the OneDrive copy as a backup if you like. Just do all Git work in the new
location.

---

## Step 1 · Put the folder on GitHub

Open **GitHub Desktop** and sign in when it asks. This is your account; do it
yourself.

`File` → `Add local repository` → browse to

```
C:\Projects\stock_advisor_app
```

It will say the folder is not a Git repository and offer **create a repository
here**. Click that.

On the create screen set the name to something like `set-equity-terminal`,
leave *Git ignore* as **None** (the project ships its own `.gitignore`), and
press **Create repository**.

Check the Changes tab before anything else. It should list roughly **62 files**.
If you see `.venv`, `__pycache__`, or thousands of files, stop — the
`.gitignore` was not picked up, and pushing that will fail.

Write a summary such as `Initial commit`, press **Commit to main**, then
**Publish repository** at the top.

**About the "Keep this code private" tick box — read this carefully.**

A Streamlit app inherits its visibility from the repository. A public repo gives
a public app that anyone can open with the link. A private repo gives a
*private* app, which only people you invite by email can open — they have to
sign in, and a link alone will not let them in. Community Cloud also allows only
one private app per account at a time.

So there are two sensible choices:

* **Public repo** — simplest. Anyone with the link uses the app instantly. The
  source code and the SET data are also browsable and downloadable by anyone.
* **Private repo, then switch the app to public** — after deploying, open the
  app's settings on Community Cloud and set sharing to public. The link then
  works for everyone while the repository itself stays closed. This is the
  better option here, because the dataset is not yours to redistribute.

The upload takes a couple of minutes for 24 MB.

---

## Step 2 · Deploy

Go to **share.streamlit.io** and sign in with the same GitHub account.

Press **Create app** → **Deploy a public app from GitHub**, then set

| Field | Value |
|---|---|
| Repository | `your-username/set-equity-terminal` |
| Branch | `main` |
| Main file path | `app.py` |

Press **Deploy**. The first build takes three to five minutes while it installs
streamlit, pandas, numpy, plotly and jinja2.

**Then check the sharing setting.** Open the app menu (three dots, top right of
the app page on Community Cloud) → **Settings** → **Sharing**, and confirm it is
set so that anyone with the link can view. If you deployed from a private
repository this will start as invite-only, and your friends will be asked to
sign in and be refused.

You will get a URL of the form

```
https://set-equity-terminal.streamlit.app
```

Anyone with that link can use it. No account, no install.

---

## What behaves differently once it is hosted

**Saved data.** On your own machine the watchlist, holdings and risk profile are
written to `user_data.json`. On a hosted deployment every visitor would share
that one file, so the app detects the hosted environment and keeps everything in
each visitor's browser session instead. Your friends will not see each other's
portfolios, and nothing they enter is stored on the server. The sidebar says so.

**Sleeping.** The app sleeps after a period with no visitors and takes about
thirty seconds to wake. Open it a few minutes before you need to show it.

**Memory.** The free tier allows about 1 GB. Loading the price history uses
roughly 300 MB, so a handful of simultaneous visitors is fine; a large class all
clicking at once may be slow.

---

## Updating it later

Change any file, open GitHub Desktop, write a summary, **Commit to main**, then
**Push origin**. The live site rebuilds itself within a minute or two. There is
nothing to redeploy.

---

## Before you make it public

The dataset came from the Stock Exchange of Thailand under whatever terms you
received it. Publishing it on the open internet is redistribution, which those
terms may not permit. Check before you untick "private", or keep the repository
private and share the app link only with people who need it.

The site carries the disclaimer on every screen, but it is worth repeating: this
is an educational research tool built on historical data ending December 2025.
It is not investment advice.
