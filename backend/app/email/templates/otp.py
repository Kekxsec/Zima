# backend/app/email/templates/otp.py


def otp_html(code: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #0f172a; margin-bottom: 8px;">Sign in to Zima</h2>
  <p style="color: #475569; margin-bottom: 24px;">Your sign-in code is:</p>
  <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px;
              padding: 24px; background: #f1f5f9; text-align: center;
              border-radius: 8px; color: #0f172a; margin-bottom: 24px;">
    {code}
  </div>
  <p style="color: #475569; margin-bottom: 8px;">This code expires in 15 minutes.</p>
  <p style="color: #94a3b8; font-size: 13px;">
    If you did not request this code, you can safely ignore this email.
  </p>
</body>
</html>"""


def otp_text(code: str) -> str:
    return (
        f"Your Zima sign-in code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you did not request this code, you can safely ignore this email."
    )
