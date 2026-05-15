export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { 'cf-turnstile-response': token, ...fields } = req.body;

  if (!token) {
    return res.status(400).json({ error: 'Missing CAPTCHA token' });
  }

  // Verify Turnstile token with Cloudflare
  const verify = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      secret: process.env.TURNSTILE_SECRET,
      response: token,
    }),
  });
  const { success } = await verify.json();

  if (!success) {
    return res.status(400).json({ error: 'CAPTCHA verification failed' });
  }

  // Forward to Formspree
  const fp = await fetch('https://formspree.io/f/mdabqnkw', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(fields),
  });

  if (!fp.ok) {
    return res.status(500).json({ error: 'Submission failed' });
  }

  return res.status(200).json({ ok: true });
}
