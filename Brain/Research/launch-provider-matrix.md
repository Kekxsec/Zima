---
title: "launch provider matrix"
tags: [zima, research, launch, providers, matrix]
type: launch_provider_matrix
created: 2026-03-22
updated: 2026-03-22
kind: canonical
status: active
llm_include: true
code_scope: cross_repo
---

[[../Zima|Zima]] · [[research|Research]]

# Launch Provider Matrix

This note maps the full provider inventory to the launch direction currently under consideration:

- primary launch pillars: `identity`, `accounts`, `device`, `browser`
- secondary / optional launch support: `privacy` lite, `backup` lite
- mostly out of launch: `domain`, `infrastructure`, broad `threat_intel`, `cloud`, `compliance`, `supply_chain`

The goal is not to build every provider at launch. The goal is to know where every provider belongs so launch prioritization stays disciplined.

## Launch Pillars

| launch pillar  | purpose                                                                      | strongest provider groups                                                                 |
| -------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `identity`     | breached identities, compromised credentials, aliases, phone-linked exposure | `breach`, selected `reputation`, selected `social`, selected `phone`, selected `darkweb`  |
| `accounts`     | MFA posture, recovery, connected apps, account inventory                     | selected `social`, selected `tools`, selected `cloud`                                     |
| `device`       | OS baseline, patching, encryption, firewall, vulnerable software             | `tools/device_posture_and_host_security`, selected `cloud`                                |
| `browser`      | extension risk, browser configuration, update posture, privacy settings      | `tools/browser_posture_and_extension_analysis`, selected `threat_intel`, selected `cloud` |
| `privacy` lite | public oversharing and people-search exposure                                | selected `social`, selected `search`, selected `phone`                                    |
| `backup` lite  | backup presence / recency checks                                             | selected `cloud`                                                                          |

## Complete Inventory Matrix

| inventory group                                      | count | primary pillar/domain alignment                     | launch fit                                             | providers                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------------- | ----: | --------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `breach`                                             |    18 | `identity`                                          | `launch core`                                          | `breachdirectory`, `citadel`, `dehashed`, `enzoic`, `ghostproject`, `hackcheck`, `hibp`, `hudson_rock`, `illicit_services`, `intelx`, `leakcheck`, `leakix`, `pastebin`, `psbdmp`, `spycloud`, `snusbase`, `wikileaks`, `xposedornot`                                                                                                                                                                                                                                                                                                                                                              |
| `reputation`                                         |    27 | mixed: `identity`, `threat_intel`, `infrastructure` | `selective launch support`                             | `abuseipdb`, `abusix`, `adblock`, `alienvaultiprep`, `blocklistde`, `botscout`, `cinsscore`, `cleantalk`, `dronebl`, `emailrep`, `focsec`, `fraudguard`, `greensnow`, `greynoise`, `greynoise_community`, `honeypot`, `ipqualityscore`, `ipregistry`, `multiproxy`, `seon`, `sorbs`, `spamcop`, `spamhaus`, `spur`, `surbl`, `threatjammer`, `uceprotect`                                                                                                                                                                                                                                          |
| `social`                                             |    32 | mixed: `identity`, `accounts`, `privacy`, `secrets` | `selective launch support`                             | `accounts`, `clearbit`, `debounce`, `emailcrawlr`, `emailformat`, `epieos`, `flickr`, `fullcontact`, `github`, `gleif`, `googlemaps`, `gravatar`, `holehe`, `hunter`, `iknowwhatyoudownload`, `keybase`, `maigret`, `nameapi`, `opencorporates`, `openstreetmap`, `peopledatalabs`, `pipl`, `skymem`, `slideshare`, `sociallinks`, `socialprofiles`, `stackoverflow`, `trumail`, `twitter`, `venmo`, `whitepagespro`, `yesitsme`                                                                                                                                                                   |
| `phone`                                              |     5 | `identity`, `privacy`                               | `optional launch support`                              | `callername`, `numverify`, `textmagic`, `truecaller`, `twilio`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `darkweb`                                            |     8 | `darkweb`, `identity` support                       | `optional / post-launch support`                       | `acuris_stolen_identities`, `ahmia`, `constella_intelligence`, `darksearch`, `onioncity`, `onionsearchengine`, `robin`, `torch`                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `tools / identity_and_account_discovery`             |     6 | `identity`, `accounts`                              | `launch support but local-binary dependent`            | `gitfive`, `holehe`, `maigret`, `sherlock`, `theharvester`, `whatsmyname`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `tools / device_posture_and_host_security`           |    20 | `device`                                            | `launch core but local-agent dependent`                | `aide`, `chef_inspec`, `chkrootkit`, `debcvescan`, `debsecan`, `grype`, `linux_native`, `lunar`, `lynis`, `macos_native`, `openscap`, `osquery`, `posture`, `rkhunter`, `syft`, `trivy`, `vuls`, `wazuh_agent`, `windows_native`, `yasat`                                                                                                                                                                                                                                                                                                                                                          |
| `tools / browser_posture_and_extension_analysis`     |     9 | `browser`                                           | `launch core but local-collector dependent`            | `browseraddonsview`, `browser_extension_detector`, `chromium_enterprise_policies`, `extensionhound`, `firefox_enterprise_policies`, `get_browser_extension_info`, `helium`, `hindsight`, `malicious_extension_sentry`                                                                                                                                                                                                                                                                                                                                                                              |
| `cloud`                                              |    19 | mixed: `browser`, `device`, `backup`, `business`    | `selective / mostly later`                             | `azureblobstorage`, `chrome_management_api`, `chrome_policy_api`, `chrome_stats`, `chrome_web_store_api`, `defender_vm_api`, `defender_for_endpoint`, `digitaloceanspace`, `edge_extensions_monitoring`, `firefox_addons_site_api`, `googleobjectstorage`, `grayhatwarfare`, `jamf_pro_api`, `meraki_dashboard_api`, `microsoft_graph_intune`, `s3bucket`, `safari_extension_mdm`, `secureannex`, `unifi_controller_api`                                                                                                                                                                           |
| `threat_intel`                                       |    28 | mixed: `browser`, `threat_intel`, `phishing`        | `mostly later; one or two browser/phishing exceptions` | `abusech`, `botvrij`, `circllu`, `crxcavator`, `customfeed`, `cybercrimetracker`, `emergingthreats`, `fortinet`, `googlesafebrowsing`, `hybrid_analysis`, `koodous`, `maltiverse`, `malwarepatrol`, `metadefender`, `openbugbounty`, `openphish`, `phishstats`, `phishtank`, `pulsedive`, `stevenblack_hosts`, `talosintel`, `threatfox`, `threatminer`, `urlscan`, `virustotal`, `vxvault`, `xforce`, `zoneh`                                                                                                                                                                                     |
| `search`                                             |     7 | `privacy`, `secrets`                                | `optional / later`                                     | `archiveorg`, `bingsearch`, `crossref`, `duckduckgo`, `googlesearch`, `grep_app`, `searchcode`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `content_analysis`                                   |    14 | utility layer for other modules                     | `utility-only`                                         | `bitcoin_finder`, `creditcard_extractor`, `email_extractor`, `ethereum_extractor`, `hashes_extractor`, `iban_extractor`, `intfiles`, `junkfiles`, `names_extractor`, `phone_extractor`, `social_extractor`, `webanalytics`, `webframework`, `webserver`                                                                                                                                                                                                                                                                                                                                            |
| `tools / network_and_wifi_inspection`                |    15 | `network`                                           | `later`                                                | `angry_ip_scanner`, `arp_scan_rs`, `kismet`, `masscan`, `miniupnpc`, `nbtscan`, `netdiscover`, `netsnmp`, `nmap`, `passer`, `portscan_tcp`, `python_iwlist`, `pywifi`, `scapy`, `wifi`                                                                                                                                                                                                                                                                                                                                                                                                             |
| `domain`                                             |    44 | `domain`, `email`, `privacy` support                | `later`                                                | `adguard_dns`, `builtwith`, `c99`, `certspotter`, `cleanbrowsing`, `cloudflaredns`, `commoncrawl`, `comodo`, `crtsh`, `dnsbrute`, `dnscommonsrv`, `dnsdb`, `dnsdumpster`, `dnsgrep`, `dnsneighbor`, `dnsraw`, `dnsresolve`, `dnszonexfer`, `fullhunt`, `google_tag_manager`, `hackertarget`, `hostio`, `jsonwhoiscom`, `mnemonic`, `opendns`, `projectdiscovery`, `quad9`, `reversewhois`, `riskiq`, `robtex`, `securitytrails`, `similar`, `spyonweb`, `sslcert`, `subdomain_takeover`, `sublist3r`, `tldsearch`, `viewdns`, `whatcms`, `whois`, `whoisology`, `whoxy`, `zetalytics`, `zonefiles` |
| `ip`                                                 |    18 | `infrastructure`, `network`, `threat_intel` support | `later`                                                | `abstractapi`, `arin`, `bgpview`, `binaryedge`, `censys`, `criminal_ip`, `ipapico`, `ipapicom`, `ipinfo`, `ipstack`, `isc`, `networksdb`, `neutrinoapi`, `onyphe`, `ripe`, `shodan`, `torexits`, `wigle`                                                                                                                                                                                                                                                                                                                                                                                           |
| `tools / domain_web_and_external_exposure_discovery` |    17 | `domain`, `infrastructure`, `secrets` support       | `later`                                                | `bbot`, `dnstwist`, `dnsx`, `gau`, `github_subdomains`, `gowitness`, `httpx`, `katana`, `nuclei`, `photon`, `snallygaster`, `subfinder`, `testsslsh`, `tlsx`, `uncover`, `wafw00f`, `wappalyzer`                                                                                                                                                                                                                                                                                                                                                                                                   |
| `tools / cloud_and_infrastructure_posture`           |     2 | `cloud`, `infrastructure`, `business`               | `later`                                                | `prowler`, `scoutsuite`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `tools / secrets_and_sensitive_data_exposure`        |     1 | `secrets`                                           | `later`                                                | `trufflehog`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `crypto`                                             |     5 | `threat_intel`, `crypto_exposure`                   | `later`                                                | `bitcoinabuse`, `bitcoinwhoswho`, `blockchain`, `coinblocker`, `etherscan`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

## Launch-First Interpretation

If launch is a personal security audit product, the strongest provider groups to prioritize are:

1. `breach`
2. selected `reputation`
3. selected `social`
4. `tools / device_posture_and_host_security`
5. `tools / browser_posture_and_extension_analysis`
6. selected `tools / identity_and_account_discovery`

### Launch-in candidates

- `hibp`
- `dehashed`
- `breachdirectory`
- `leakcheck`
- `hudson_rock`
- `emailrep`
- `accounts`
- `epieos`
- `holehe`
- `maigret`
- `whatsmyname`
- `osquery`
- `lynis`
- `trivy`
- `grype`
- `linux_native`
- `macos_native`
- `windows_native`
- `posture`
- `browser_extension_detector`
- `get_browser_extension_info`
- `malicious_extension_sentry`
- `chromium_enterprise_policies`
- `firefox_enterprise_policies`
- `crxcavator`

### Launch-optional candidates

- `truecaller`
- `numverify`
- `ahmia`
- `darksearch`
- `gravatar`
- `skymem`
- `emailcrawlr`
- `googlemaps`
- `openstreetmap`

### Launch-out / later

- almost all `domain`
- almost all `ip`
- most `threat_intel`
- most `cloud`
- all `crypto`
- most `search`
- most `network` tools
- most `cloud/infrastructure` tools
- `content_analysis` as standalone feature work
