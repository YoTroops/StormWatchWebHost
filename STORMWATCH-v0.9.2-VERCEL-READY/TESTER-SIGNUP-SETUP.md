# STORMWATCH tester signup — email delivery

The **Join Testing** button opens a form on the dashboard. Submissions are POSTed to `/api/testers/signup` and emailed to **mattsails07@gmail.com**, using Resend from the FastAPI backend. Nothing is saved in a database.

## Vercel setup

1. Create a Resend account at https://resend.com and verify a sending domain you control (for instance `stormwatch.site`). Configure the DNS records requested by Resend.
2. Create a Resend API key with permission to send emails.
3. In Vercel → Project → Settings → Environment Variables (Production), add **Secret** `RESEND_API_KEY` with the key, and **Config** `TESTER_NOTIFICATION_FROM` with an address under your verified sending domain, for example `STORMWATCH <testers@stormwatch.site>`. Both are read server-side only.
4. Redeploy Vercel. Open STORMWATCH, close What's New, click Join Testing, and make a test submission using your own email. Confirm it arrives in the Gmail inbox (or check spam).

**Important:** Resend's `onboarding@resend.dev` test sender may only send to the Resend account's own email. Verify a domain for reliable real-world submissions. Your OpenAI API key is unrelated; it does not send form emails.

## User privacy & abuse

The form asks for an email address and optional name, test focus and notes. Consent is required. Submissions are emailed to the site owner, with the submitter's email as the reply-to. No server-side database is used, and form data is not included in application logs. The site owner should delete the emails when no longer needed for testing. A honeypot and best-effort per-instance rate limiting are included; use edge rate limiting, CAPTCHA, or Turnstile for larger public traffic. HTTP 503 is returned if the email provider is not configured or is unavailable, rather than falsely claiming delivery.
