# Travel Eye — Setup Guide (Step by Step)

You do not need to code. Follow these steps in order.

---

## Step 1: Run the website on your computer

1. Open a terminal.
2. Paste these commands one at a time:

```powershell
cd "C:\Users\asus\OneDrive\Desktop\new project\travel-eye"
npm run dev
```

3. Open your browser to: **http://localhost:3000**

You should see the Travel Eye home page. You can click **Preview Red Fort** without signing up.

---

## Step 2: Create a free Supabase account (for sign-ups)

1. Go to **https://supabase.com** and click **Start your project**.
2. Sign up with GitHub or email.
3. Click **New project**:
   - Name: `travel-eye`
   - Database password: choose something and **save it somewhere safe**
   - Region: pick closest to India (e.g. Singapore or Mumbai if available)
4. Wait ~2 minutes for the project to finish creating.

---

## Step 3: Copy your API keys

1. In Supabase, open your project.
2. Go to **Project Settings** (gear icon) → **API**.
3. Copy:
   - **Project URL**
   - **anon public** key (under Project API keys)

---

## Step 4: Add keys to the project

1. In the `travel-eye` folder, copy the example file:
   - Copy `.env.local.example` → rename the copy to `.env.local`
2. Open `.env.local` and paste your values:

```
NEXT_PUBLIC_SUPABASE_URL=paste-your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=paste-your-anon-key
```

3. **Stop** the dev server (Ctrl+C in terminal) and run `npm run dev` again.

---

## Step 5: Enable email sign-up in Supabase

1. In Supabase: **Authentication** → **Providers** → **Email** → ensure it is **enabled**.
2. For testing, you can disable email confirmation:
   - **Authentication** → **Providers** → **Email** → turn off **Confirm email** (optional for MVP testing only).

---

## Step 6: Run the database schema (optional for cloud sync)

Progress is saved on your phone in the browser for now. To store discoveries in the cloud later:

1. Supabase → **SQL Editor** → **New query**
2. Open the file `supabase/schema.sql` in this project, copy all of it, paste into Supabase, click **Run**.

---

## Step 7: Test on your phone (at Red Fort or at home)

1. On your computer, find your local IP: run `ipconfig` in terminal, note **IPv4 Address** (e.g. `192.168.1.5`).
2. On your phone (same Wi‑Fi), open: `http://YOUR-IP:3000`
3. Allow **location** and **camera** when asked.
4. Go to **Red Fort** → **Open Travel Eye Lens**.

**Tip:** GPS popups work best when you are physically at the fort. At home, use **Scan landmark** with a photo of a monument on your screen, or tap checkpoint markers.

---

## What Travel Eye does in this MVP

| Feature | How it works |
|---------|----------------|
| **Red Fort** | 10 checkpoints with stories (public sources) |
| **GPS popups** | When you walk within range, a discovery popup appears |
| **Lens scan** | Point camera → **Scan landmark** → matches reference photo |
| **Stories + audio** | Tap checkpoint → read story → **Listen to story** (English) |
| **Progress** | Ring shows X of 10 discovered |
| **Sign up** | Saves account via Supabase (when configured) |

---

## When I need your help next

1. **Visit Red Fort** and tell me if popups appear at the right spots (we may adjust GPS coordinates).
2. **Send photos** you take of each spot — we will improve scan accuracy.
3. **Review stories** — flag anything incorrect; we will replace with official/government data later.
4. **Pick the next monument** after Red Fort works well.

---

## Deploy online (later)

When ready, we can put the site on **Vercel** (free) so anyone can open it without your computer running.

Questions? Ask in chat and say which step you are on.
