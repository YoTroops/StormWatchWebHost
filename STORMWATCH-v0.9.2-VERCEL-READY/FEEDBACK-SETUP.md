# STORMWATCH feedback setup (v0.10.2)

Everyone with the website link is a tester. No application, signup, or account is needed. The SEND FEEDBACK button appears on the dashboard (desktop and mobile) and as a link on About and Briefing. The form includes category, required message, optional name and email.

Feedback is emailed to mattsails07@gmail.com by Resend. Set these Vercel environment variables and redeploy:

- RESEND_API_KEY: Resend secret API key (Secret)
- TESTER_NOTIFICATION_FROM: STORMWATCH <feedback@stormwatch.site> (requires a verified sender domain in Resend). Alternatively use FEEDBACK_NOTIFICATION_FROM.

No new API key is needed if you already configured these for v0.10.1. Feedback remains unavailable until email delivery is configured; the form displays an explicit error, not a false success. In-memory rate limiting is best effort per instance. Consider stronger persistent anti-spam controls if the site becomes public.
