---
kind: canonical
status: active
llm_include: true
code_scope: backend
tags: [zima, providers, schemas, api]
created: 2026-03-21
---

← [[../Zima|Home]] · [[Provider Module Map|← Provider Map]] · [[Signal Research Guide|Signal Research →]]

# Provider Output Schemas

All providers return a uniform schema. Your module mapper receives this dict and converts it into a `SignalCreate`. The module is where you add `signal_type`, `severity`, and `category` in Zima's own terms.

---

## Universal Provider Output Schema

Every provider method returns `list[dict[str, Any]]` where each dict is:

```python
{
    "provider":     str,          # e.g. "shodan", "hibp", "virustotal"
    "category":     str,          # e.g. "port_discovery", "credential_leak"
    "title":        str,          # human-readable summary
    "description":  str,          # longer description string
    "entity_type":  str,          # "email", "domain", "ip_address", "username", "url"
    "entity_value": str,          # the actual value e.g. "user@example.com"
    "confidence":   float,        # 0.0–1.0 — provider's own certainty estimate
    "tags":         list[str],    # e.g. ["shodan", "port_scan", "passive"]
}
```

> **Note:** HIBP returns a typed schema (not this dict) and already has its own mapper.

---

## `breach/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `hibp` | `get_breaches(email)` | typed schema — has mapper | `email` | varies |
| `dehashed` | `search_breaches(email, domain)` | `credential_leak` | `email` / `domain` | `0.85` |
| `leakix` | `search_leaks(domain, ip_address)` | `data_leak` | `domain` / `ip_address` | `0.80` |
| `hudson_rock` | `get_compromised_data(email, domain)` | `stealer_log_exposure` | `email` / `domain` | `0.85` |
| `breachdirectory`, `snusbase`, `leakcheck`, `ghostproject`, `citadel`, `illicit_services` | `search_breaches(email)` | `credential_leak` | `email` | `0.75–0.90` |
| `intelx` | `search(email, domain)` | `credential_leak` / `darkweb_mention` | `email` / `domain` | `0.80` |
| `pastebin`, `psbdmp` | `search(email, domain)` | `paste_mention` | `email` / `domain` | `0.65–0.75` |
| `wikileaks` | `search(email, domain)` | `credential_leak` | `email` / `domain` | `0.75` |

---

## `reputation/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `abuseipdb` | `get_reputation(ip_address)` | `ip_reputation` | `ip_address` | `0.80–0.90` |
| `greynoise` | `get_noise(ip_address)` | `ip_reputation` | `ip_address` | `0.85` |
| `ipqualityscore` | `get_score(ip, email)` | `ip_reputation` / `email_reputation` | `ip_address` / `email` | `0.85` |
| `emailrep` | `get_reputation(email)` | `email_reputation` | `email` | `0.80` |
| `spamhaus` | `lookup(ip, domain)` | `blocklist_hit` | `ip_address` / `domain` | `0.90` |
| `surbl` | `lookup(domain)` | `blocklist_hit` | `domain` | `0.85` |
| `blocklistde`, `dronebl`, `sorbs`, `spamcop`, `uceprotect`, `cinsscore`, `greensnow`, `honeypot`, `multiproxy` | `lookup(ip)` | `blocklist_hit` | `ip_address` | `0.75–0.90` |
| `alienvaultiprep` | `get_reputation(ip, domain)` | `threat_intel` | `ip_address` / `domain` | `0.80` |
| `fraudguard` | `check(ip)` | `ip_reputation` | `ip_address` | `0.80` |
| `seon` | `check(email)` | `email_reputation` | `email` | `0.80` |
| `cleantalk`, `botscout` | `check(ip, email)` | `spam_detection` | `ip_address` / `email` | `0.75` |
| `focsec`, `ipregistry`, `threatjammer`, `abusix` | `check(ip)` | `ip_reputation` | `ip_address` | `0.75–0.85` |

---

## `threat_intel/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `virustotal` | `get_report(domain, ip, url)` | `malware_detection` | `domain` / `ip_address` / `url` | `0.90` |
| `urlscan` | `scan(url, domain)` | `malware_detection` / `phishing` | `url` / `domain` | `0.85` |
| `openphish`, `phishtank`, `phishstats` | `check(url, domain)` | `phishing` | `url` / `domain` | `0.85–0.95` |
| `abusech` | `lookup(domain, ip, hash)` | `malware_detection` | `domain` / `ip_address` | `0.90` |
| `threatfox` | `lookup(ip, domain)` | `threat_intel` | `ip_address` / `domain` | `0.90` |
| `pulsedive` | `lookup(ip, domain, url)` | `threat_intel` | all | `0.80` |
| `hybrid_analysis` | `lookup(hash)` | `malware_detection` | `hash` | `0.90` |
| `talosintel` | `check(ip, domain)` | `ip_reputation` / `domain_reputation` | `ip_address` / `domain` | `0.85` |
| `xforce` | `check(ip, domain, url)` | `threat_intel` | all | `0.85` |
| `googlesafebrowsing` | `check(url)` | `phishing` / `malware_detection` | `url` | `0.95` |
| `threatminer` | `lookup(ip, domain)` | `threat_intel` | `ip_address` / `domain` | `0.75` |
| `stevenblack_hosts`, `botvrij`, `cybercrimetracker`, `emergingthreats`, `maltiverse`, `malwarepatrol`, `vxvault`, `zoneh`, `customfeed` | `check(domain, ip)` | `blocklist_hit` / `threat_intel` | `domain` / `ip_address` | `0.75–0.85` |
| `crxcavator` | `check(extension_id)` | `browser_extension_risk` | `extension_id` | `0.80` |
| `metadefender` | `scan(hash, ip)` | `malware_detection` | `hash` / `ip_address` | `0.85` |
| `koodous` | `check(hash)` | `malware_detection` | `hash` | `0.85` |

---

## `ip/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `shodan` | `search_hosts(domain, ip)` | `port_discovery` / `vulnerability` / `host_discovery` | `ip_address` | `0.85–0.90` |
| `censys` | `search_hosts(domain, ip)` | `host_discovery` | `ip_address` | `0.80` |
| `binaryedge` | `scan(ip, domain)` | `port_discovery` / `vulnerability` | `ip_address` | `0.85` |
| `criminal_ip` | `check(ip)` | `ip_reputation` / `port_discovery` | `ip_address` | `0.85` |
| `onyphe` | `lookup(ip)` | `threat_intel` / `port_discovery` | `ip_address` | `0.80` |
| `abstractapi`, `ipapico`, `ipapicom`, `ipinfo`, `ipstack`, `neutrinoapi` | `lookup(ip)` | `geolocation` | `ip_address` | `0.90` |
| `arin`, `ripe`, `bgpview` | `lookup(ip)` | `network_ownership` | `ip_address` / `asn` | `0.95` |
| `torexits` | `check(ip)` | `tor_exit_node` | `ip_address` | `0.95` |
| `isc` | `check(ip)` | `threat_intel` | `ip_address` | `0.80` |
| `hosting` | `check(ip)` | `hosting_provider` | `ip_address` | `0.90` |
| `wigle` | `lookup(bssid)` | `wifi_network` | `network` | `0.85` |

---

## `domain/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `securitytrails` | `lookup_domain(domain, email, ip)` | `domain_security` / `dns_record` | `hostname` / `domain` | `0.70–0.85` |
| `crtsh` | `search(domain)` | `tls_certificate` | `domain` / `hostname` | `0.90` |
| `certspotter` | `monitor(domain)` | `tls_certificate` | `domain` | `0.95` |
| `sslcert` | `check(domain)` | `tls_configuration` | `domain` | `0.90` |
| `whois`, `whoisology`, `whoxy`, `jsonwhoiscom` | `lookup(domain)` | `domain_ownership` | `domain` / `email` | `0.85–0.90` |
| `dnsraw`, `dnsresolve`, `dnsdb`, `dnsgrep`, `dnsdumpster` | `lookup(domain)` | `dns_record` | `domain` / `ip_address` | `0.85–0.95` |
| `dnsbrute`, `dnscommonsrv`, `sublist3r`, `fullhunt`, `c99` | `enumerate(domain)` | `subdomain_discovery` | `hostname` | `0.65–0.80` |
| `dnszonexfer` | `attempt(domain)` | `dns_misconfiguration` | `domain` | `0.95` |
| `subdomain_takeover` | `check(hostname)` | `subdomain_takeover` | `hostname` | `0.90` |
| `builtwith`, `whatcms`, `similar` | `lookup(domain)` | `technology_stack` | `domain` | `0.85` |
| `adguard_dns`, `cloudflaredns`, `quad9`, `opendns` | `resolve(domain)` | `dns_record` / `blocklist_hit` | `domain` | `0.90–0.95` |
| `riskiq`, `mnemonic`, `zetalytics` | `lookup(domain, ip)` | `domain_reputation` | `domain` / `ip_address` | `0.80` |
| `commoncrawl`, `hackertarget`, `projectdiscovery` | `search(domain)` | `subdomain_discovery` | `hostname` | `0.70–0.80` |
| `spyonweb`, `hostio`, `robtex` | `lookup(domain, ip)` | `domain_ownership` / `host_discovery` | `domain` / `ip_address` | `0.80` |
| `reversewhois` | `lookup(email)` | `domain_ownership` | `domain` | `0.85` |

---

## `social/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `github` | `search_profiles(domain, email, username)` | `social_media` | `username` | `0.70` |
| `epieos` | `lookup(email)` | `social_media` / `identity_exposure` | `email` / `username` | `0.80` |
| `clearbit`, `fullcontact` | `enrich(email, domain)` | `identity_exposure` | `email` / `domain` | `0.80` |
| `hunter`, `snov` | `find(domain)` | `email_discovery` | `email` | `0.80` |
| `gravatar` | `lookup(email)` | `social_media` | `email` | `0.85` |
| `keybase` | `lookup(username)` | `social_media` | `username` | `0.90` |
| `twitter`, `flickr`, `slideshare`, `stackoverflow`, `venmo` | `lookup(username, email)` | `social_media` | `username` | `0.70–0.85` |
| `opencorporates`, `gleif` | `search(name, domain)` | `corporate_registration` | `domain` / `company` | `0.85` |
| `emailcrawlr`, `skymem` | `lookup(email)` | `identity_exposure` | `email` | `0.70` |
| `debounce`, `trumail`, `nameapi` | `verify(email)` | `email_validation` | `email` | `0.90` |
| `iknowwhatyoudownload` | `check(ip)` | `privacy_exposure` | `ip_address` | `0.75` |
| `accounts` | `check(email, username)` | `account_discovery` | `email` / `username` | `0.75` |

---

## `darkweb/` Providers

| Provider | Method | `category` | `entity_type` | `confidence` |
|---|---|---|---|---|
| `ahmia` | `search_darkweb(domain, email, username)` | `identity_exposure` | `url` | `0.65` |
| `darksearch` | `search(query)` | `identity_exposure` / `darkweb_mention` | `url` | `0.65` |
| `onioncity`, `onionsearchengine`, `torch` | `search(query)` | `darkweb_mention` | `url` | `0.60–0.65` |

---

## Remaining Categories

- **`cloud/`** — return `public_storage` category
- **`phone/`** — return `phone_validation` / `identity_exposure`
- **`search/`** — return `web_mention` / `identity_exposure`
- **`content_analysis/`** — utility parsers, return extracted entities not security findings
- **`crypto/`** — `blockchain` / `etherscan` return `crypto_transaction`; abuse providers return `threat_intel`

---

## Using This for Signal Mapping

Your signal table per module needs:

```
Provider category:   "credential_leak"   confidence: 0.85
  ↓  module decides
Signal type:         "email_breached"
Signal severity:     "high"   (if confidence > 0.80 and no password hash)
                     "critical" (if confidence > 0.80 and password hash present)
Signal category:     "identity_security"
```

One row per (provider, provider-category) combination in the signal registry.

---

## See Also

- [[Signal Research Guide]] — how to build the signal registry
- [[Provider Module Map]] — which modules consume which providers
- [[Extending the Platform]] — implementing the mapper
