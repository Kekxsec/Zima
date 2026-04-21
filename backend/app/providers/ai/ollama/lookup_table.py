# backend/app/providers/ai/ollama/lookup_table.py
"""
Static domain-to-service lookup table.

Resolves known sender domains to (service_slug, display_name) with 100%
confidence, bypassing Ollama inference entirely for recognised senders.

Lookup strategy:
  1. Exact match on the normalised sender domain.
  2. Single leading-label strip (e.g. email.amazon.com → amazon.com).

This handles the vast majority of newsletter/transactional senders whose
From: domain is a subdomain of the brand domain, without adding complexity.
"""

from __future__ import annotations

from backend.app.providers.ai.ollama.schemas import OllamaAccountInterpretation

# ---------------------------------------------------------------------------
# Domain registry  (domain → (service_slug, display_name))
# ---------------------------------------------------------------------------

_KNOWN_DOMAINS: dict[str, tuple[str, str]] = {
    # ── E-commerce ──────────────────────────────────────────────────────────
    "amazon.com": ("amazon", "Amazon"),
    "amazon.co.uk": ("amazon", "Amazon"),
    "amazon.de": ("amazon", "Amazon"),
    "amazon.fr": ("amazon", "Amazon"),
    "amazon.ca": ("amazon", "Amazon"),
    "amazon.com.au": ("amazon", "Amazon"),
    "amazon.it": ("amazon", "Amazon"),
    "amazon.es": ("amazon", "Amazon"),
    "amazon.in": ("amazon", "Amazon"),
    "amazon.co.jp": ("amazon", "Amazon"),
    "ebay.com": ("ebay", "eBay"),
    "ebay.co.uk": ("ebay", "eBay"),
    "etsy.com": ("etsy", "Etsy"),
    "shopify.com": ("shopify", "Shopify"),
    "aliexpress.com": ("aliexpress", "AliExpress"),
    "wish.com": ("wish", "Wish"),
    "walmart.com": ("walmart", "Walmart"),
    "target.com": ("target", "Target"),
    "bestbuy.com": ("bestbuy", "Best Buy"),
    "costco.com": ("costco", "Costco"),
    "newegg.com": ("newegg", "Newegg"),
    "asos.com": ("asos", "ASOS"),
    "zalando.com": ("zalando", "Zalando"),
    "zara.com": ("zara", "Zara"),
    "hm.com": ("hm", "H&M"),
    "uniqlo.com": ("uniqlo", "Uniqlo"),
    "wayfair.com": ("wayfair", "Wayfair"),
    "chewy.com": ("chewy", "Chewy"),
    "overstock.com": ("overstock", "Overstock"),
    "rakuten.com": ("rakuten", "Rakuten"),
    # ── Tech / Cloud / Dev ──────────────────────────────────────────────────
    "google.com": ("google", "Google"),
    "gmail.com": ("google", "Gmail"),
    "googlemail.com": ("google", "Gmail"),
    "microsoft.com": ("microsoft", "Microsoft"),
    "outlook.com": ("microsoft", "Outlook"),
    "hotmail.com": ("microsoft", "Hotmail"),
    "live.com": ("microsoft", "Microsoft"),
    "apple.com": ("apple", "Apple"),
    "icloud.com": ("apple", "iCloud"),
    "github.com": ("github", "GitHub"),
    "gitlab.com": ("gitlab", "GitLab"),
    "bitbucket.org": ("bitbucket", "Bitbucket"),
    "atlassian.com": ("atlassian", "Atlassian"),
    "digitalocean.com": ("digitalocean", "DigitalOcean"),
    "linode.com": ("linode", "Linode"),
    "vultr.com": ("vultr", "Vultr"),
    "hetzner.com": ("hetzner", "Hetzner"),
    "cloudflare.com": ("cloudflare", "Cloudflare"),
    "vercel.com": ("vercel", "Vercel"),
    "netlify.com": ("netlify", "Netlify"),
    "heroku.com": ("heroku", "Heroku"),
    "railway.app": ("railway", "Railway"),
    "render.com": ("render", "Render"),
    "fly.io": ("flyio", "Fly.io"),
    "stripe.com": ("stripe", "Stripe"),
    "braintree.com": ("braintree", "Braintree"),
    "twilio.com": ("twilio", "Twilio"),
    "sendgrid.com": ("sendgrid", "SendGrid"),
    "mailgun.com": ("mailgun", "Mailgun"),
    "postmarkapp.com": ("postmark", "Postmark"),
    "hubspot.com": ("hubspot", "HubSpot"),
    "salesforce.com": ("salesforce", "Salesforce"),
    "zendesk.com": ("zendesk", "Zendesk"),
    "intercom.io": ("intercom", "Intercom"),
    "datadog.com": ("datadog", "Datadog"),
    "newrelic.com": ("newrelic", "New Relic"),
    "pagerduty.com": ("pagerduty", "PagerDuty"),
    "sentry.io": ("sentry", "Sentry"),
    # ── Social / Messaging ──────────────────────────────────────────────────
    "twitter.com": ("twitter", "Twitter"),
    "x.com": ("twitter", "X (Twitter)"),
    "facebook.com": ("facebook", "Facebook"),
    "instagram.com": ("instagram", "Instagram"),
    "linkedin.com": ("linkedin", "LinkedIn"),
    "discord.com": ("discord", "Discord"),
    "slack.com": ("slack", "Slack"),
    "telegram.org": ("telegram", "Telegram"),
    "whatsapp.com": ("whatsapp", "WhatsApp"),
    "reddit.com": ("reddit", "Reddit"),
    "pinterest.com": ("pinterest", "Pinterest"),
    "tiktok.com": ("tiktok", "TikTok"),
    "snapchat.com": ("snapchat", "Snapchat"),
    "mastodon.social": ("mastodon", "Mastodon"),
    "threads.net": ("threads", "Threads"),
    # ── Streaming / Entertainment ────────────────────────────────────────────
    "netflix.com": ("netflix", "Netflix"),
    "spotify.com": ("spotify", "Spotify"),
    "youtube.com": ("youtube", "YouTube"),
    "hulu.com": ("hulu", "Hulu"),
    "disneyplus.com": ("disney-plus", "Disney+"),
    "hbomax.com": ("hbomax", "Max (HBO)"),
    "max.com": ("hbomax", "Max (HBO)"),
    "paramountplus.com": ("paramount-plus", "Paramount+"),
    "peacocktv.com": ("peacock", "Peacock"),
    "twitch.tv": ("twitch", "Twitch"),
    "vimeo.com": ("vimeo", "Vimeo"),
    "pandora.com": ("pandora", "Pandora"),
    "soundcloud.com": ("soundcloud", "SoundCloud"),
    "deezer.com": ("deezer", "Deezer"),
    "tidal.com": ("tidal", "TIDAL"),
    "audible.com": ("audible", "Audible"),
    "applemusic.com": ("apple-music", "Apple Music"),
    # ── Finance / Payments ───────────────────────────────────────────────────
    "paypal.com": ("paypal", "PayPal"),
    "venmo.com": ("venmo", "Venmo"),
    "cash.app": ("cashapp", "Cash App"),
    "revolut.com": ("revolut", "Revolut"),
    "wise.com": ("wise", "Wise"),
    "monzo.com": ("monzo", "Monzo"),
    "starlingbank.com": ("starling", "Starling Bank"),
    "square.com": ("square", "Square"),
    "coinbase.com": ("coinbase", "Coinbase"),
    "binance.com": ("binance", "Binance"),
    "kraken.com": ("kraken", "Kraken"),
    "chase.com": ("chase", "Chase"),
    "barclays.com": ("barclays", "Barclays"),
    "barclaycard.co.uk": ("barclaycard", "Barclaycard"),
    "hsbc.com": ("hsbc", "HSBC"),
    "lloydsbank.com": ("lloydsbank", "Lloyds Bank"),
    "lloydsbank.co.uk": ("lloydsbank", "Lloyds Bank"),
    "lloydsbankbusiness.com": ("lloydsbank", "Lloyds Bank Business"),
    "natwest.com": ("natwest", "NatWest"),
    "natwestonline.co.uk": ("natwest", "NatWest"),
    "onlineservices.natwest.com": ("natwest", "NatWest"),
    "santander.co.uk": ("santander", "Santander"),
    "santander.com": ("santander", "Santander"),
    "hsbc.co.uk": ("hsbc", "HSBC"),
    "business.hsbc.co.uk": ("hsbc", "HSBC"),
    "barclays.co.uk": ("barclays", "Barclays"),
    "home.barclays": ("barclays", "Barclays"),
    "halifax.co.uk": ("halifax", "Halifax"),
    "halifax-online.co.uk": ("halifax", "Halifax"),
    "nationwide.co.uk": ("nationwide", "Nationwide"),
    "tsb.co.uk": ("tsb", "TSB"),
    "virginmoney.com": ("virginmoney", "Virgin Money"),
    "americanexpress.com": ("amex", "American Express"),
    "capitalone.com": ("capitalone", "Capital One"),
    "wellsfargo.com": ("wellsfargo", "Wells Fargo"),
    "transferwise.com": ("wise", "Wise"),
    # ── Travel / Transport ───────────────────────────────────────────────────
    "airbnb.com": ("airbnb", "Airbnb"),
    "booking.com": ("booking", "Booking.com"),
    "expedia.com": ("expedia", "Expedia"),
    "hotels.com": ("hotels", "Hotels.com"),
    "trivago.com": ("trivago", "Trivago"),
    "uber.com": ("uber", "Uber"),
    "lyft.com": ("lyft", "Lyft"),
    "bolt.eu": ("bolt", "Bolt"),
    "ryanair.com": ("ryanair", "Ryanair"),
    "easyjet.com": ("easyjet", "easyJet"),
    "britishairways.com": ("british-airways", "British Airways"),
    "delta.com": ("delta", "Delta Air Lines"),
    "united.com": ("united", "United Airlines"),
    "tripadvisor.com": ("tripadvisor", "TripAdvisor"),
    "kayak.com": ("kayak", "KAYAK"),
    "skyscanner.net": ("skyscanner", "Skyscanner"),
    # ── Food / Delivery ──────────────────────────────────────────────────────
    "doordash.com": ("doordash", "DoorDash"),
    "grubhub.com": ("grubhub", "Grubhub"),
    "deliveroo.com": ("deliveroo", "Deliveroo"),
    "instacart.com": ("instacart", "Instacart"),
    "hellofresh.com": ("hellofresh", "HelloFresh"),
    "gousto.co.uk": ("gousto", "Gousto"),
    # ── Productivity / Work ──────────────────────────────────────────────────
    "notion.so": ("notion", "Notion"),
    "airtable.com": ("airtable", "Airtable"),
    "asana.com": ("asana", "Asana"),
    "monday.com": ("monday", "monday.com"),
    "trello.com": ("trello", "Trello"),
    "linear.app": ("linear", "Linear"),
    "clickup.com": ("clickup", "ClickUp"),
    "basecamp.com": ("basecamp", "Basecamp"),
    "zoom.us": ("zoom", "Zoom"),
    "webex.com": ("webex", "Webex"),
    "dropbox.com": ("dropbox", "Dropbox"),
    "box.com": ("box", "Box"),
    "docusign.com": ("docusign", "DocuSign"),
    "adobe.com": ("adobe", "Adobe"),
    "canva.com": ("canva", "Canva"),
    "figma.com": ("figma", "Figma"),
    "miro.com": ("miro", "Miro"),
    "loom.com": ("loom", "Loom"),
    "calendly.com": ("calendly", "Calendly"),
    "typeform.com": ("typeform", "Typeform"),
    # ── Security / Password Managers ─────────────────────────────────────────
    "1password.com": ("1password", "1Password"),
    "lastpass.com": ("lastpass", "LastPass"),
    "bitwarden.com": ("bitwarden", "Bitwarden"),
    "dashlane.com": ("dashlane", "Dashlane"),
    "okta.com": ("okta", "Okta"),
    "auth0.com": ("auth0", "Auth0"),
    "nordvpn.com": ("nordvpn", "NordVPN"),
    "expressvpn.com": ("expressvpn", "ExpressVPN"),
    "proton.me": ("proton", "Proton"),
    "protonmail.com": ("proton", "ProtonMail"),
    "protonvpn.com": ("protonvpn", "ProtonVPN"),
    "haveibeenpwned.com": ("hibp", "Have I Been Pwned"),
    # ── News / Media ─────────────────────────────────────────────────────────
    "nytimes.com": ("nytimes", "The New York Times"),
    "theguardian.com": ("guardian", "The Guardian"),
    "bbc.com": ("bbc", "BBC"),
    "bbc.co.uk": ("bbc", "BBC"),
    "cnn.com": ("cnn", "CNN"),
    "medium.com": ("medium", "Medium"),
    "substack.com": ("substack", "Substack"),
    "wordpress.com": ("wordpress", "WordPress"),
    "mailchimp.com": ("mailchimp", "Mailchimp"),
    "constantcontact.com": ("constantcontact", "Constant Contact"),
    # ── Health / Fitness / Dating ─────────────────────────────────────────────
    "myfitnesspal.com": ("myfitnesspal", "MyFitnessPal"),
    "strava.com": ("strava", "Strava"),
    "fitbit.com": ("fitbit", "Fitbit"),
    "peloton.com": ("peloton", "Peloton"),
    "calm.com": ("calm", "Calm"),
    "headspace.com": ("headspace", "Headspace"),
    "hinge.co": ("hinge", "Hinge"),
    "tinder.com": ("tinder", "Tinder"),
    "bumble.com": ("bumble", "Bumble"),
    # ── Education ────────────────────────────────────────────────────────────
    "coursera.org": ("coursera", "Coursera"),
    "udemy.com": ("udemy", "Udemy"),
    "skillshare.com": ("skillshare", "Skillshare"),
    "duolingo.com": ("duolingo", "Duolingo"),
    "khanacademy.org": ("khanacademy", "Khan Academy"),
    "stackoverflow.com": ("stackoverflow", "Stack Overflow"),
    "codecademy.com": ("codecademy", "Codecademy"),
    "pluralsight.com": ("pluralsight", "Pluralsight"),
    "udacity.com": ("udacity", "Udacity"),
    # ── Gaming ───────────────────────────────────────────────────────────────
    "steampowered.com": ("steam", "Steam"),
    "epicgames.com": ("epicgames", "Epic Games"),
    "ea.com": ("ea", "EA"),
    "ubisoft.com": ("ubisoft", "Ubisoft"),
    "nintendo.com": ("nintendo", "Nintendo"),
    "xbox.com": ("xbox", "Xbox"),
    "playstation.com": ("playstation", "PlayStation"),
    "battlenet.com": ("battlenet", "Battle.net"),
    "blizzard.com": ("blizzard", "Blizzard"),
    "gog.com": ("gog", "GOG"),
    "itch.io": ("itchio", "itch.io"),
}


def _to_interpretation(
    service_name: str, display_name: str
) -> OllamaAccountInterpretation:
    result: OllamaAccountInterpretation = {
        "service_name": service_name,
        "display_name": display_name,
        "confidence": 100,
        "reason": "domain-lookup",
    }
    return result


def lookup(sender_domain: str) -> OllamaAccountInterpretation | None:
    """
    Return a high-confidence interpretation for a known sender domain.

    Tries exact match first, then single leading-label strip
    (e.g. email.amazon.com → amazon.com). Returns None if unknown.
    """
    if not sender_domain:
        return None

    normalized = sender_domain.strip().lower().rstrip(".")
    if not normalized:
        return None

    # 1. Exact match
    match = _KNOWN_DOMAINS.get(normalized)
    if match:
        return _to_interpretation(*match)

    # 2. Strip one leading subdomain label
    parts = normalized.split(".")
    if len(parts) >= 3:
        parent = ".".join(parts[1:])
        match = _KNOWN_DOMAINS.get(parent)
        if match:
            return _to_interpretation(*match)

    return None


__all__ = ["lookup"]
