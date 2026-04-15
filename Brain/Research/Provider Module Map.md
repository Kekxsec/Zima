---
kind: canonical
status: active
llm_include: true
code_scope: backend
tags: [zima, providers, modules, mapping]
created: 2026-03-21
---

← [[../Zima|Home]] · [[Extending the Platform|← Extending]] · [[Provider Schemas|Schemas →]]

# Provider → Module Map

Full mapping of all providers to their module domains. Use this as the research scaffold — build a signal table per module per provider before writing any code.

**13 provider categories · 150+ providers**

---

## `breach/` → `modules/identity/`

| Provider | Module | Pattern |
|---|---|---|
| `hibp` | `breach_monitor` | A (1→1) — already built |
| `breachdirectory` | `breach_monitor` | B (aggregate with hibp) |
| `dehashed` | `breach_monitor` + `credential_exposure` | B — richer credential data |
| `leakcheck` | `credential_exposure` | A |
| `leakix` | `credential_exposure` + `stealer_log_exposure` | B |
| `snusbase` | `credential_exposure` | A |
| `intelx` | `stealer_log_exposure` + `darkweb_identity_monitor` | B |
| `hudson_rock` | `stealer_log_exposure` | A — stealer logs specifically |
| `illicit_services` | `stealer_log_exposure` | A |
| `ghostproject` | `credential_exposure` | A |
| `citadel` | `credential_exposure` | A |
| `pastebin` / `psbdmp` | `alias_correlation` + `breach_monitor` | B |
| `wikileaks` | `breach_monitor` | A |

---

## `darkweb/` → `modules/darkweb/`

| Provider | Module | Pattern |
|---|---|---|
| `ahmia` | `darkweb_identity_monitor` | A |
| `darksearch` | `darkweb_identity_monitor` + `threat_actor_mentions` | B |
| `onioncity` | `darkweb_identity_monitor` | A |
| `onionsearchengine` | `darkweb_identity_monitor` | A |
| `torch` | `credential_dump_monitor` | A |

---

## `reputation/` → `modules/identity/` + `modules/threat_intel/` + `modules/infrastructure/`

| Provider | Module | Pattern |
|---|---|---|
| `abuseipdb` | `domain_reputation` + `ip_flagged_threat_intel` | B |
| `abusix` | `domain_reputation` | A |
| `emailrep` | `username_exposure` + `account_enumeration_risk` | A |
| `greynoise` / `greynoise_community` | `exposed_services` + `domain_reputation` | B |
| `ipqualityscore` | `domain_reputation` + `phishing_feed_monitor` | B |
| `spamhaus` | `domain_reputation` + `dmarc_spf_dkim` | B |
| `surbl` | `phishing_detection` | A |
| `alienvaultiprep` | `malware_ioc_monitor` + `domain_ioc_match` | B |
| `fraudguard` | `domain_reputation` | A |
| `spur` | `exposed_services` | A |
| `blocklistde` | `domain_reputation` | A |
| `cleantalk` | `account_enumeration_risk` | A |
| `botscout` | `account_enumeration_risk` | A |
| `seon` | `identity_widely_exposed` | A |
| `adblock`, `dronebl`, `cinsscore`, `uceprotect`, `sorbs`, `spamcop`, `honeypot`, `focsec`, `multiproxy`, `ipregistry`, `threatjammer`, `greensnow` | `domain_reputation` | B (aggregate into one reputation module) |

---

## `threat_intel/` → `modules/threat_intel/`

| Provider | Module | Pattern |
|---|---|---|
| `abusech` | `malware_ioc_monitor` + `emerging_threats` | B |
| `virustotal` | `malware_ioc_monitor` + `domain_ioc_match` | C — rich API, multiple modules |
| `urlscan` | `phishing_feed_monitor` + `domain_ioc_match` | B |
| `openphish` | `phishing_feed_monitor` | A |
| `phishtank` / `phishstats` | `phishing_feed_monitor` | B |
| `pulsedive` | `malware_ioc_monitor` + `threat_actor_mentions` | B |
| `hybrid_analysis` | `malware_ioc_monitor` | A |
| `threatfox` | `malware_ioc_monitor` + `emerging_threats` | B |
| `talosintel` | `malware_ioc_monitor` + `domain_ioc_match` | B |
| `xforce` | `malware_ioc_monitor` + `domain_ioc_match` | B |
| `googlesafebrowsing` | `phishing_feed_monitor` | A |
| `botvrij`, `cybercrimetracker`, `emergingthreats`, `maltiverse`, `malwarepatrol`, `metadefender`, `vxvault`, `zoneh`, `customfeed` | `malware_ioc_monitor` | B (aggregate feed) |
| `openbugbounty` | `domain_ioc_match` | A |
| `crxcavator` | `extension_risk` (browser domain) | A |
| `stevenblack_hosts` | `phishing_feed_monitor` | A |
| `threatminer` | `domain_ioc_match` + `ip_flagged_threat_intel` | B |
| `circllu` | `malware_ioc_monitor` | A |
| `fortinet` | `malware_ioc_monitor` | A |
| `koodous` | `malware_ioc_monitor` | A |

---

## `domain/` → `modules/domain/`

| Provider | Module | Pattern |
|---|---|---|
| `securitytrails` | `dns_security` + `subdomain_enumeration` + `certificate_monitor` | C |
| `crtsh` | `certificate_monitor` + `subdomain_enumeration` | B |
| `certspotter` | `certificate_monitor` | A |
| `sslcert` | `tls_configuration` | A |
| `whois`, `whoisology`, `whoxy`, `jsonwhoiscom`, `reversewhois` | `dns_security` + `domain_reputation` | B |
| `dnsraw`, `dnsresolve`, `dnsdb`, `dnsgrep`, `dnsdumpster` | `dns_security` | B (aggregate) |
| `dnsbrute`, `dnscommonsrv`, `sublist3r`, `fullhunt`, `dnsneighbor` | `subdomain_enumeration` | B |
| `subdomain_takeover` | `subdomain_enumeration` | A — specific risk |
| `dnszonexfer` | `dns_security` | A |
| `builtwith`, `whatcms`, `similar` | `saas_inventory` (saas domain) | B |
| `adguard_dns`, `cleanbrowsing`, `cloudflaredns`, `comodo`, `opendns`, `quad9` | `dns_security` + `phishing_feed_monitor` | B |
| `riskiq`, `mnemonic`, `zetalytics` | `domain_reputation` + `domain_ioc_match` | B |
| `c99`, `zonefiles`, `spyonweb`, `hostio`, `robtex` | `subdomain_enumeration` + `dns_security` | B |
| `commoncrawl`, `hackertarget` | `subdomain_enumeration` | B |
| `projectdiscovery` | `subdomain_enumeration` | A |
| `viewdns`, `tldsearch` | `dns_security` | B |
| `google_tag_manager` | `saas_inventory` | A |

---

## `ip/` → `modules/infrastructure/`

| Provider | Module | Pattern |
|---|---|---|
| `shodan` | `exposed_services` + `port_scanning` + `service_banner_analysis` | C |
| `censys` | `exposed_services` + `cve_correlation` | C |
| `binaryedge` | `exposed_services` | A |
| `criminal_ip` | `exposed_services` + `domain_ioc_match` | B |
| `onyphe` | `exposed_services` | A |
| `abstractapi`, `ipapico`, `ipapicom`, `ipinfo`, `ipstack`, `neutrinoapi` | `exposed_services` (geolocation enrichment) | B |
| `arin`, `ripe`, `bgpview` | `exposed_services` (ASN/ownership) | B |
| `torexits` | `domain_reputation` + `account_enumeration_risk` | B |
| `wigle` | `wifi_security` (network domain) | A |
| `isc` | `malware_ioc_monitor` | A |
| `networksdb` | `exposed_services` | A |

---

## `social/` → `modules/identity/` + `modules/privacy/`

| Provider | Module | Pattern |
|---|---|---|
| `epieos` | `username_exposure` + `alias_correlation` | B |
| `holehe` | `account_enumeration_risk` | A |
| `maigret` | `username_exposure` | A |
| `hunter` | `email_extractor` + `username_exposure` | B |
| `clearbit`, `fullcontact`, `sociallinks`, `socialprofiles` | `public_profile_scan` (privacy domain) | B |
| `github` | `github_secret_scan` (secrets domain) + `public_profile_scan` | C |
| `gravatar`, `skymem`, `emailcrawlr` | `username_exposure` | B |
| `emailformat` | `alias_correlation` | A |
| `debounce`, `trumail`, `nameapi` | `username_exposure` | B |
| `keybase` | `username_exposure` + `alias_correlation` | B |
| `opencorporates`, `gleif` | `public_profile_scan` + `data_broker_exposure` | B |
| `twitter`, `flickr`, `slideshare`, `stackoverflow`, `venmo` | `public_profile_scan` | B |
| `accounts` | `account_inventory` (accounts domain) | A |
| `iknowwhatyoudownload` | `people_search_exposure` (privacy domain) | A |
| `googlemaps`, `openstreetmap` | `data_broker_exposure` | A |

---

## `tools/` → various modules

> **Deferred** — tools require local binaries and need a sidecar container or local agent. Not part of MVP or near-term build plan.

| Tool | Domain | Notes |
|---|---|---|
| `nmap`, `portscan_tcp`, `nbtscan` | infrastructure | needs local binary |
| `nuclei`, `wafw00f`, `wappalyzer` | infrastructure | needs local binary |
| `trufflehog`, `snallygaster` | secrets | needs local binary |
| `holehe`, `maigret` | identity | needs local binary |
| `testsslsh`, `dnstwist` | domain | needs local binary |

---

## `cloud/` → `modules/cloud/`

| Provider | Module |
|---|---|
| `s3bucket`, `azureblobstorage`, `digitaloceanspace`, `googleobjectstorage` | `public_storage_detection` |
| `grayhatwarfare` | `public_storage_detection` |

---

## `phone/` → `modules/identity/`

| Provider | Module |
|---|---|
| `truecaller`, `callername`, `numverify` | `phone_exposure` |
| `twilio`, `textmagic` | alerts only — not scan providers |

---

## `crypto/` → `modules/threat_intel/`

| Provider | Module |
|---|---|
| `bitcoinabuse`, `bitcoinwhoswho` | `malware_ioc_monitor` (ransomware addresses) |
| `blockchain`, `etherscan` | specialist `crypto_exposure` module |
| `coinblocker` | `malware_ioc_monitor` |

---

## `search/` → `modules/privacy/` + `modules/secrets/`

| Provider | Module |
|---|---|
| `googlesearch`, `bingsearch`, `duckduckgo` | `public_profile_scan` + `data_broker_exposure` |
| `archiveorg` | `public_profile_scan` + `config_secret_scan` |
| `grep_app`, `searchcode` | `github_secret_scan` + `config_secret_scan` |
| `crossref` | `public_profile_scan` |

---

## `content_analysis/` — utility providers

These are used **by** other modules to extract and parse content, not their own modules:

| Provider | Used by |
|---|---|
| `email_extractor`, `phone_extractor` | `identity/*` modules |
| `creditcard_extractor`, `iban_extractor` | `darkweb/credential_dump_monitor` |
| `bitcoin_finder`, `ethereum_extractor` | `crypto_exposure` |
| `names_extractor` | `privacy/data_broker_exposure` |
| `hashes_extractor` | `threat_intel/malware_ioc_monitor` |
| `webserver`, `webframework`, `webanalytics` | `infrastructure/service_banner_analysis` |
| `intfiles`, `junkfiles` | `secrets/config_secret_scan` |
| `social_extractor` | `identity/username_exposure` |

---

## Build Priority Order

| Priority | Categories | Tier |
|---|---|---|
| 1 | `breach/` → `identity/` | Core |
| 1 | `reputation/emailrep`, `social/epieos`, `accounts` → `identity/` | Core |
| 2 | `darkweb/` → `darkweb/` | Plus |
| 2 | `reputation/` IP blocklists → `infrastructure/` | Plus |
| 2 | `social/` public profile → `privacy/`, `phone/` → `identity/` | Plus |
| 3 | `domain/` → `domain/` | Pro |
| 3 | `ip/shodan`, `censys`, `binaryedge` → `infrastructure/` | Pro |
| 3 | `threat_intel/` major providers → `threat_intel/` | Pro |
| 3 | `social/github` → `secrets/` | Pro |
| 4 | `cloud/`, remaining `threat_intel/`, `crypto/` | Business |

---

## See Also

- [[Provider Schemas]] — what each provider returns
- [[Signal Research Guide]] — how to build the signal table
- [[Extending the Platform]] — how to implement each new module
- [[../Architecture/section-20-domain-breakdown|§20 Domain Breakdown]] — full module domain catalogue
