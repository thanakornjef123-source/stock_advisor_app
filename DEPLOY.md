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

## Step 0 · Already done for you

The project has been copied out of OneDrive to:

```
C:\Users\Asus\Projects\stock_advisor_app
```

This matters. OneDrive syncs every file write to the cloud, and Git writes
hundreds of small internal files very quickly. The two fight each other — an
attempt to create the repository inside the OneDrive folder produced a
`.git\config` filled entirely with null bytes and a half-built folder Git
refused to open. That broken folder has been removed from the copy.

The OneDrive original is untouched and still runs. From here on, do all Git work
in `C:\Users\Asus\Projects\stock_advisor_app`.

---

## Step 1 · Put the folder on GitHub

Open **GitHub Desktop** and sign in when it asks. This is your account; do it
yourself.

`File` → `Add local repository` → browse to

```
C:\Users\Asus\Projects\stock_advisor_app
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

**The repository is private, and that is the right setting.**

Repository visibility only sets the app's *default* visibility — it is not a
cage. Streamlit's own documentation is explicit: "Your app will inherit
permissions from your GitHub repo... If you want to change that you can simply
do so from the app settings menu."

So the combination to aim for is:

* **Repository private** — the SET data and the source stay closed. The dataset
  came from the exchange and is not yours to redistribute, so this matters.
* **App public** — set in Streamlit after deploying. Anyone with the link opens
  it instantly, no account, no invitation.

This is strictly better than making the repository public. An earlier draft of
this document claimed a private repo locked the app to invited viewers forever.
That was wrong, and it has been corrected against the documentation.

The upload takes a couple of minutes for 24 MB.

---

## Step 2 · Deploy

Go to **share.streamlit.io** and sign in with the same GitHub account.

Press **Create app** → **Deploy a public app from GitHub**, then set

| Field | Value |
|---|---|
| Repository | `thanakornjef123-source/stock_advisor_app` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL | pick anything free, e.g. `set-terminal` |

Press **Deploy**. The first build takes three to five minutes while it installs
streamlit, pandas, numpy, plotly and jinja2. You will get a URL of the form

```
https://stockadvisorapp-di9ewtrmurthsaabwplsgt.streamlit.app
```

---

## Step 3 · Make the app public

The repository is private, so the app starts private too. Right now a friend
opening the link would hit a sign-in wall. One switch fixes it, and the
repository stays closed.

From the running app, click **Share** in the upper-right corner, then
**"Make this app public."**

Or from the workspace: app settings → **Sharing** → under "Who can view this
app" choose **"This app is public and searchable."**

Then verify it properly: open the link in a private / incognito window where
you are not signed in to anything. If the terminal loads there, your friends
can load it.

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
