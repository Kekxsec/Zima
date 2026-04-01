# scripts/generate_test_mbox.py
"""
Generates a synthetic mbox file for testing the email account identifier.

Usage:
    python -m scripts.generate_test_mbox          # writes tests/fixtures/sample.mbox
    python -m scripts.generate_test_mbox --out /tmp/test.mbox
"""

import argparse
from pathlib import Path

# Each tuple: (from_addr, subject, date_str)
# Covers all source_type classifications + unknown domains + skip-list domains
SAMPLE_EMAILS = [
    # --- Account confirmations ---
    (
        "noreply@github.com",
        "Welcome to GitHub! Please verify your email address",
        "Mon, 01 Jan 2024 10:00:00 +0000",
    ),
    (
        "no-reply@spotify.com",
        "Confirm your email address for Spotify",
        "Tue, 02 Jan 2024 11:00:00 +0000",
    ),
    (
        "noreply@netflix.com",
        "Verify your Netflix account",
        "Wed, 03 Jan 2024 12:00:00 +0000",
    ),
    (
        "no-reply@discord.com",
        "Welcome to Discord! Activate your account",
        "Thu, 04 Jan 2024 09:00:00 +0000",
    ),
    (
        "no-reply@notion.so",
        "Thanks for signing up for Notion",
        "Fri, 05 Jan 2024 08:00:00 +0000",
    ),
    (
        "welcome@slack.com",
        "Welcome to Slack — confirm your email",
        "Sat, 06 Jan 2024 07:00:00 +0000",
    ),
    (
        "noreply@dropbox.com",
        "Thanks for creating a Dropbox account",
        "Sun, 07 Jan 2024 06:00:00 +0000",
    ),
    # --- Password resets ---
    (
        "no-reply@spotify.com",
        "Reset your Spotify password",
        "Mon, 08 Jan 2024 10:00:00 +0000",
    ),
    (
        "noreply@github.com",
        "Forgot your GitHub password?",
        "Tue, 09 Jan 2024 11:00:00 +0000",
    ),
    (
        "security@paypal.com",
        "Recover your PayPal password",
        "Wed, 10 Jan 2024 12:00:00 +0000",
    ),
    # --- Receipts ---
    (
        "receipts@stripe.com",
        "Your receipt from Stripe — $19.99",
        "Thu, 11 Jan 2024 09:00:00 +0000",
    ),
    (
        "orders@amazon.com",
        "Order Confirmation #112-3456789",
        "Fri, 12 Jan 2024 08:00:00 +0000",
    ),
    (
        "receipts@uber.com",
        "Your Friday trip with Uber",
        "Sat, 13 Jan 2024 07:00:00 +0000",
    ),
    (
        "noreply@doordash.com",
        "Your DoorDash order is confirmed!",
        "Sun, 14 Jan 2024 06:00:00 +0000",
    ),
    # --- Security alerts ---
    (
        "security@google.com",
        "Security alert: New sign-in from Chrome on Mac",
        "Mon, 15 Jan 2024 10:00:00 +0000",
    ),
    (
        "security@facebook.com",
        "We noticed an unusual sign-in to your Facebook account",
        "Tue, 16 Jan 2024 11:00:00 +0000",
    ),
    (
        "noreply@linkedin.com",
        "New device sign-in to your LinkedIn account",
        "Wed, 17 Jan 2024 12:00:00 +0000",
    ),
    # --- Newsletters (should be classified as newsletter, low signal) ---
    (
        "newsletter@medium.com",
        "Your weekly reading digest from Medium",
        "Thu, 18 Jan 2024 09:00:00 +0000",
    ),
    (
        "news@substack.com",
        "The Substack weekly newsletter",
        "Fri, 19 Jan 2024 08:00:00 +0000",
    ),
    # --- Unknown domains with account-confirmation subjects (should still be captured) ---
    (
        "noreply@acmecorp-saas.io",
        "Welcome to AcmeCorp — verify your account",
        "Sat, 20 Jan 2024 07:00:00 +0000",
    ),
    (
        "no-reply@startup-xyz.com",
        "Confirm your email address",
        "Sun, 21 Jan 2024 06:00:00 +0000",
    ),
    # --- Should be SKIPPED (generic email providers in skip list) ---
    (
        "noreply@gmail.com",
        "Google Account security alert",
        "Mon, 22 Jan 2024 10:00:00 +0000",
    ),
    (
        "bounce@sendgrid.net",
        "Delivery Status Notification",
        "Tue, 23 Jan 2024 11:00:00 +0000",
    ),
    # --- More registry-matched services ---
    (
        "noreply@steampowered.com",
        "Welcome to Steam! Verify your email address",
        "Wed, 24 Jan 2024 12:00:00 +0000",
    ),
    (
        "no-reply@epicgames.com",
        "Thanks for creating an Epic Games account",
        "Thu, 25 Jan 2024 09:00:00 +0000",
    ),
    (
        "noreply@twitter.com",
        "Confirm your Twitter account",
        "Fri, 26 Jan 2024 08:00:00 +0000",
    ),
    (
        "noreply@reddit.com",
        "Welcome to Reddit! Verify your email",
        "Sat, 27 Jan 2024 07:00:00 +0000",
    ),
    (
        "no-reply@zoom.us",
        "Please activate your Zoom account",
        "Sun, 28 Jan 2024 06:00:00 +0000",
    ),
    (
        "noreply@adobe.com",
        "Please verify your Adobe ID email address",
        "Mon, 29 Jan 2024 10:00:00 +0000",
    ),
    (
        "noreply@atlassian.com",
        "Welcome to Atlassian — confirm your account",
        "Tue, 30 Jan 2024 11:00:00 +0000",
    ),
]


def build_mbox(recipient: str = "testuser@example.com") -> bytes:
    lines: list[bytes] = []
    for from_addr, subject, date_str in SAMPLE_EMAILS:
        # mbox separator line
        lines.append(f"From {from_addr} {date_str}\n".encode())
        # Headers
        lines.append(f"From: {from_addr}\n".encode())
        lines.append(f"To: {recipient}\n".encode())
        lines.append(f"Subject: {subject}\n".encode())
        lines.append(f"Date: {date_str}\n".encode())
        lines.append(f"Message-ID: <test-{len(lines)}@zima.test>\n".encode())
        lines.append(b"\n")
        # Minimal body (never stored by our parser, but needed for valid mbox format)
        lines.append(b"This is a test email body.\n")
        lines.append(b"\n")
    return b"".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="tests/fixtures/sample.mbox",
        help="Output path for the generated mbox file",
    )
    parser.add_argument(
        "--recipient",
        default="testuser@example.com",
        help="Recipient email address to embed in To: headers",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_mbox(args.recipient)
    out_path.write_bytes(data)

    print(f"Written {len(data):,} bytes ({len(SAMPLE_EMAILS)} messages) to {out_path}")
    print(f"Recipient: {args.recipient}")
    print("\nUpload with:")
    print("  curl -X POST http://localhost:8000/api/v1/email-accounts/uploads \\")
    print("    -H 'Authorization: Bearer <your-token>' \\")
    print(f"    -F 'file=@{out_path}'")


if __name__ == "__main__":
    main()
