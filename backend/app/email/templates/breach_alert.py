# backend/app/email/templates/breach_alert.py
import html as _html


def breach_alert_html(
    monitored_email: str,
    breach_title: str,
    breach_date: str,
    data_classes: list[str],
    dashboard_url: str = "https://yourdomain.com/dashboard",
) -> str:
    safe_email = _html.escape(monitored_email)
    safe_title = _html.escape(breach_title)
    safe_date = _html.escape(breach_date)
    # dashboard_url is always an internal value from settings.frontend_base_url,
    # but escape it too for defence-in-depth.
    safe_url = _html.escape(dashboard_url, quote=True)
    data_items = "".join(
        f"<li style='margin-bottom:4px'>{_html.escape(d)}</li>" for d in data_classes
    )
    return f"""<!DOCTYPE html>
<html>
<body
  style="font-family: sans-serif; max-width: 560px; margin: 0 auto;
         padding: 24px; color: #0f172a;"
>
  <h2 style="margin-bottom: 8px;">New breach detected</h2>
  <p style="color: #475569; margin-bottom: 24px;">
    A monitored email address was found in a data breach.
  </p>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
    <tr>
      <td
        style="padding: 10px 12px; font-weight: 600; background: #f8fafc;
               width: 35%; border: 1px solid #e2e8f0;"
      >Email</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{safe_email}</td>
    </tr>
    <tr>
      <td
        style="padding: 10px 12px; font-weight: 600; background: #f8fafc;
               border: 1px solid #e2e8f0;"
      >Breach</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{safe_title}</td>
    </tr>
    <tr>
      <td
        style="padding: 10px 12px; font-weight: 600; background: #f8fafc;
               border: 1px solid #e2e8f0;"
      >Date</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{safe_date}</td>
    </tr>
    <tr>
      <td
        style="padding: 10px 12px; font-weight: 600; background: #f8fafc;
               border: 1px solid #e2e8f0; vertical-align: top;"
      >Data exposed</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">
        <ul style="margin: 0; padding-left: 18px;">{data_items}</ul>
      </td>
    </tr>
  </table>
  <a href="{safe_url}"
     style="display: inline-block; background: #0f172a; color: #ffffff;
            padding: 12px 24px; border-radius: 6px; text-decoration: none;
            font-weight: 600; margin-bottom: 32px;">
    View your dashboard →
  </a>
  <p
    style="color: #94a3b8; font-size: 13px; border-top: 1px solid #e2e8f0;
           padding-top: 16px;"
  >
    You're receiving this because you monitor this email address with Zima.
  </p>
</body>
</html>"""


def breach_alert_text(
    monitored_email: str,
    breach_title: str,
    breach_date: str,
    data_classes: list[str],
    dashboard_url: str = "https://yourdomain.com/dashboard",
) -> str:
    data_list = ", ".join(data_classes) if data_classes else "unknown"
    return (
        f"New breach detected\n"
        f"{'=' * 40}\n\n"
        f"Email:        {monitored_email}\n"
        f"Breach:       {breach_title}\n"
        f"Date:         {breach_date}\n"
        f"Data exposed: {data_list}\n\n"
        f"View your dashboard: {dashboard_url}\n\n"
        f"You're receiving this because you monitor this email address with Zima."
    )
