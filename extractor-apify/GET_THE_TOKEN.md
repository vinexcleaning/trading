# GET_THE_TOKEN.md — the one thing only he can do

**Five minutes. No payment details at any point. If any screen asks for a card,
stop and say so — that is not this.**

The account exists. What is missing is an **API key**: the code that lets a
script use the account. It is not the password and it is not the login.

⚠ **Verified against Bright Data's current documentation on 2026-08-18**, not
written from memory. `CLAUDE.md` §3 exists because instructions written from
memory have already cost an afternoon here. **If a screen does not match what is
written below, stop and describe what you see — do not hunt for it.** Bright
Data moves this page.

---

## The steps

1. Go to **https://brightdata.com/cp/setting/users** and sign in if it asks.

   *You should see:* a settings page with a list of users on the account.

2. Find the section headed **"API key"** on that page.

   *If there is no "API key" section:* you are not signed in as the admin of the
   account. Switch to the admin account — only an admin can create one. **If you
   only have one account, you are the admin and it is there; scroll.**

3. Click the button **"Add API key"** in the **top right** of that section.

   *You should see:* a small form asking for User, Permissions and Expiration.

4. Fill it in:
   - **User** — leave it as yourself.
   - **Permissions** — choose the **read / lowest** option that is offered. We
     only ever read data. **If you are unsure which one, pick the least
     powerful.** It can be replaced in two minutes if it turns out to be too
     little.
   - **Expiration** — set **"Unlimited"** if offered, otherwise the longest.

5. Click **Save**.

6. **The key appears once and never again.** Copy it immediately.

7. Make a folder and a file, **outside this project**, and paste the key in:

   - Open **File Explorer**
   - Go to **`C:\Users\vinig`**
   - Make a new folder called exactly **`keys`** (if it is not already there)
   - Inside it, make a new text file called exactly **`brightdata.txt`**
   - **Paste the key in, nothing else — no quotes, no label, no spaces.** One
     line.
   - Save and close.

8. Reply here with the words **`token is in`**. **Do not paste the key into this
   chat.** If it has already been pasted into a chat anywhere, say so — it has
   to be deleted and replaced, and that is a two-minute job, not a disaster.

---

## Why the file goes there and not here

**This repository is public.** Anything inside it can be read by anyone. The
folder `C:\Users\vinig\keys\` is outside it.

`tests/test_no_secrets.py` **fails the build** if anything shaped like a
credential appears anywhere in this project folder — including in a note, a
comment, or a Markdown file, because the thing that went wrong last time was a
key pasted into a chat, and chats look like Markdown. The test knows Bright
Data's key shape specifically and has a planted example proving it still fires.

## What happens next, and what it can cost

**Nothing can be spent by accident.** In order:

```bash
py -3 extractor-apify\src\brightdata.py preflight
```

That **spends nothing**. It reads the account, prints which scraper it would use
for X, TikTok and Instagram and why, prints the exact request it would send, and
stops. **If two scrapers match, or none does, it refuses to continue** rather
than guessing and spending.

Then, only if the preflight is clean:

```bash
py -3 extractor-apify\src\brightdata.py run
```

That uses **at most 5,000 records — the free monthly allowance, and nothing
beyond it.** The limit is enforced in the code before each request, not checked
afterwards, and there is a test that plants a spent allowance and proves the
run stops without sending anything.

**Expected cost: $0.** If a bill is ever possible, the preflight will have said
so first.
