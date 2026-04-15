---
title: "output / tools / whatsmyname"
aliases: ["whatsmyname output", "whatsmyname signal registry"]
tags: [zima, research, outputs, signal-registry, tools, whatsmyname, graph_exclude]
type: provider_research_output
provider: whatsmyname
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: whatsmyname.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---


# A. Tool/API Surface Appendix

- **Dataset Format (`wmn-data.json`)**: WhatsMyName’s core is a JSON dataset. It has top-level keys **`license`**, **`authors`**, **`categories`**, and **`sites`**. The **`sites`** entry is an array of site-definition objects. Each site object includes:

    - `name` (string): site display name.
    - `uri_check` (string): URL template containing `{account}`, used to check for the username’s presence (e.g. `"https://github.com/{account}"`).
    - _Optional_ `uri_pretty` (string): friendly profile URL template (if different from `uri_check`).
    - `e_code` (int): expected HTTP status code when the account **exists** (found).
    - `m_code` (int): expected HTTP status code when the account is **missing** (not found).
    - `e_string` (string): text snippet expected in the response body when the account exists.
    - `m_string` (string): text snippet expected when the account is missing.
    - `known` (list of strings): example usernames known to exist on that site (for validation).
    - `cat` (string): category tag (from the allowed list).
    - _Optional_ `headers` (object): HTTP request headers (e.g. `{ "User-Agent": "...", "Accept": "application/json" }`).
    - _Optional_ `post_body` (string): if the check is a POST request, the body template (with `{account}`).
    - _Optional_ `protection` (list): labels like `"cloudflare"` indicating anti-bot barriers.
    - (No other special fields like cookies or auth are documented.)

    The repository also contains `wmn-data-schema.json` describing these fields (not easily viewable via browser). Example excerpt of a site entry:

    json

    Copy

    ```
    {
      "name": "21buttons",
      "uri_check": "https://www.21buttons.com/buttoner/{account}",
      "e_code": 200,
      "e_string": "profile-info__profile-data__name",
      "m_string": "This is not the page you're looking for",
      "m_code": 404,
      "known": ["patricialmendro","ginamariahoffmann","espeworkout"],
      "cat": "social"
    }
    ```

    (For an example with POST/headers: AniList uses `uri_pretty`, `post_body`, and custom headers.)

- **Sites Covered & Categories**: As of August 2022, the dataset lists _424 sites_ (according to the CLI tool output). The `cat` field can be one of: _archived, art, blog, business, coding, dating, finance, gaming, health, hobby, images, misc, music, news, political, search, shopping, social, tech, video, xx NSFW xx_. (These are the same as the top-level `"categories"` array in the JSON.)

- **Maintenance Cadence**: WhatsMyName is community-maintained. Contributors submit pull requests to add or update sites. The `wmn-data.json` file is updated irregularly as volunteers work on it. A client tool can “update” to fetch the newest version from GitHub. (Micah Hoffman notes the project started in 2015 and has been expanded since, e.g. “over 160 websites” as of 2016, and now hundreds.)

- **Detection Methods**: For each site, the checker performs an HTTP request to `uri_check` (GET by default, or POST if `post_body` is specified). It then compares the HTTP status and response body to the expected values. Specifically:

    - **Status Code Matching**: If the response status equals `e_code`, the account is likely present; if it equals `m_code`, it’s absent. (Some sites deliberately use 301/302 redirects for present or missing accounts.)
    - **Content Matching**: The checker also looks for the presence of `e_string` in the body (to confirm existence) or `m_string` for absence. This helps avoid false positives (for example, GitHub’s user page contains a known profile layout string).
    - **Redirects**: If a site responds with a redirect status (e.g. 301/302) not matching `e_code` or `m_code`, the result may be ambiguous; by default the tool likely follows or respects `m_code`. (The dataset entries simply set `e_code`/`m_code` to 3xx where needed.)
    - **Timeouts/Errors**: The project does not document special error-handling. In practice, timeouts or connection errors should be caught by the caller (e.g. the Python script) and treated as “no result” for that site.
    - **False Positives**: The author specifically designed the project to reduce false hits. By requiring matching text (`e_string`/`m_string`) in addition to status, many generic pages are filtered out. However, false positives still vary by site. For example, if `e_string` or `m_string` is too generic, it could misclassify. The community relies on testing (`known` examples) to tune each site definition.
- **Programmatic Usage**: WhatsMyName is primarily a **dataset** (not a hosted API). Usage options:

    - **Python Library**: There is a PyPI package `what-is-my-name` (2022) that includes the JSON and scripts. Installing it (`pip install what-is-my-name`) provides scripts like `web_accounts_list_checker.py` and `check_online_presence.py`.
    - **CLI Tools**: The repository includes Python scripts. For example, `web_accounts_list_checker.py -u USERNAME` iterates all sites with `USERNAME`. A sample run shows “424 sites found in file” and then prints each URL lookup, culminating in found results. Flags allow outputting JSON vs text, filtering by category, etc. Example usage (from PyPI docs):

        csharp

        Copy

        ```
        python3 web_accounts_list_checker.py -u maxim
        - 424 sites found in file.
        > Looking up https://www.anime-planet.com/users/maxim
        > Looking up ...
        ... Searching for sites with username (maxim) > Found 159 results:
        [+] Found user at https://coderwall.com/maxim/
        [+] Found user at https://dev.to/maxim
        ```

        (By default it prints found/not-found; flags `-a`/`-n` control verbosity.)
    - **Update Command**: A community client (`wmnc.py`) provides an `update` command to download the latest `wmn-data.json` from GitHub. It can also `list-sites` and `list-categories` for reference.
    - **Raw HTTP Implementation**: One can ignore the provided scripts and simply fetch the JSON (e.g. from [raw GitHub](https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json)) and code the logic. For each site in `sites[]`, replace `{account}` in `uri_check`, perform GET or POST (depending on `post_body`), and check status/content against `e_code/e_string` or `m_code/m_string`.
    - **Output Format**: The Python scripts can emit either JSON or text. In JSON mode the output likely includes fields like `site`, `username`, and a boolean or message for found/not-found. In text mode (as above) it shows “Found user at <URL>” for each positive hit. The raw data itself provides no standardized “API” fields beyond the site definitions.
- **Comparison with Similar Tools**:

    - _Maigret_: Another username OSINT tool (written in Rust/Python) supports ~800+ sites (from Sherlock’s list). Maigret is more actively expanded recently and can query APIs (e.g. GitHub GraphQL) with concurrency. By contrast, WhatsMyName has ~424 sites (as of 2022). Both use static site lists, but WhatsMyName’s JSON is easier to extend by community pull requests, whereas Maigret pulls definitions from Sherlock and updates via that project.
    - _Sherlock_: An older Python tool with hundreds of site checks. Its dataset overlaps but is not identical; Sherock’s last updates (v0.15) include ~300 sites. WhatsMyName often covers additional niche/social sites and is maintained under a CC license.
    - _Unique Value_: WhatsMyName’s strength is its curated JSON dataset and simple HTTP-check approach. It is open data (CC BY-SA 4.0) that feeds into many OSINT tools (Recon-ng, SpiderFoot, etc.). Its use of expected strings helps reduce noise. It complements others (e.g. holehe does email checks, Maigret/Sherlock do broader enumeration). For Zima, WhatsMyName is useful for **utility/enrichment**: rapidly listing where a given username exists to augment an account inventory (with known false-positive caveats).

**References:** The above is based on the official WhatsMyName documentation and code. The project’s PyPI page describes it as “unified data for user and username enumeration” and shows example CLI output. The `wmn-data.json` schema and entries (examined from GitHub) reveal fields like `e_code`, `e_string`, `m_code`, `m_string`, etc.. The author notes he built it to reduce false positives.

# B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|account_inventory|utility_only|Username enumeration via WhatsMyName|`wmn-data.json` dataset|enrichment_only|username|Requires a username input to check.||Queries each site URL template for presence of username. No auth needed.|
|username_exposure|unknown|_N/A (WhatsMyName not used here)_|_N/A_|out_of_scope|username|_Not consumed_ – site presence ≠ breach.|–|Username-exposure (breach) uses different data. WhatsMyName doesn’t apply.|

- **Notes**: WhatsMyName should feed into **account_inventory** (to enrich which accounts exist on which platforms) but **not** into username_exposure. The output is used as enrichment of account existence, not as a security finding. Each check is “gated” simply by having a target username. The source for account_inventory signals will be the account_inventory module itself (using WhatsMyName data).

# C. Signal Contract Table

_No standalone signals are emitted by this provider._ WhatsMyName only reveals whether a username exists on a site. By policy these are context-only enrichment items (not security issues) and are handled within the `account_inventory` module for building profiles. Thus we do not create any `signal_type` rows. WhatsMyName’s results feed into account_inventory as raw context (e.g. storing “username exists on Site X”), but do not trigger independent signals.

# D. Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|account_inventory|username_presence_enrichment|**Source reliability:** Dataset is community-curated by OSINT contributors. Generally reliable for defined sites, but accuracy varies by site. Some sites change pages, risking false results. Use content checks to improve reliability.|**Freshness:** The dataset is updated irregularly via GitHub. Use the client “update” to refresh before use. If the data is stale, new sites or changed page layouts won’t be detected.|**Corroboration:** Cross-check with other enumeration tools (e.g. Maigret) or direct site/API queries. Verify positive hits by fetching the profile URL (`uri_pretty`) and confirming. Negative results can be double-checked against generic search or related OSINT tools.|**Calibration TODO:** Measure actual false-positive/negative rates by sampling known accounts. Tag sites with poor reliability. Possibly weight confidence by site’s historical success (e.g. test with “known” names).|

- We do not assign final confidence values here. Instead note that the data comes from a volunteer dataset (medium reliability), results should be double-checked, and the freshness depends on regular updates.

# E. Provider Summary

- **Strongest utility:** WhatsMyName excels at **username enumeration** – checking if a username exists on many platforms. It should be used to enrich an account’s profile (account inventory), e.g. listing which sites a given username is registered on. This can help cross-reference with breach data (e.g. if the same username appears in a breach) but in itself is not a breach.
- **Not for:** It should **not** be used to generate “exposure” or risk signals. Finding that a username exists on Site X is not a security finding (only informational). It also does not check for password leaks, malware, or any PII breach – only existence. It should not be used in place of actual breach intelligence or to infer identity beyond account presence.
- **Cautions:** Data comes under **CC BY-SA 4.0** license, so attribution is required if reused. No authentication or API key is needed (it’s a local dataset/tool). There are no explicit rate limits from WhatsMyName itself, but hitting many sites in parallel risks being blocked. The JSON notes when sites have anti-bot protection (e.g. Cloudflare, DDoS-Guard); such sites may fail or require special headers. Many entries include recommended headers (like a browser User-Agent) to avoid blocks. Implementation should respect polite limits (e.g. small concurrency, delays) since some sites might throttle or CAPTCHA.
- **Role:** Overall, WhatsMyName is **utility/enrichment-only** for the `account_inventory` module. It does not produce risk findings and should be handled as supplemental context data. (It can be thought of as a “username existence scanner” with no direct severity.)

# F. Structured JSON

{
  "provider": "whatsmyname",
  "provider_category": "tools",
  "provider_role": "utility_only",
  "module_mappings": [
    {
      "module": "account_inventory",
      "provider_role": "utility_only",
      "provider_method": "WhatsMyName username enumeration dataset lookup",
      "endpoint_or_artifact": "wmn-data.json (GitHub dataset)",
      "classification": "enrichment_only",
      "entity_types": ["username"],
      "gating_logic": "Requires an input username; skip if none",
      "citation_refs": "【34†L156-L163】【44†L1-L4】",
      "notes": "Iterates predefined site URL templates to check for username existence; no auth needed."
    },
    {
      "module": "username_exposure",
      "provider_role": "unknown",
      "provider_method": "N/A",
      "endpoint_or_artifact": "N/A",
      "classification": "out_of_scope",
      "entity_types": ["username"],
      "gating_logic": "Not applicable",
      "citation_refs": "",
      "notes": "WhatsMyName does not feed username_exposure. It only checks account presence, not breaches."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "account_inventory",
      "signal_type_or_use_case": "username_presence_enrichment",
      "source_reliability": "Community-curated JSON dataset (moderate reliability). Provides explicit expected-status/content matches to reduce false hits【4†L279-L284】, but site changes can break checks.",
      "freshness_considerations": "Dataset updates are irregular. Use the provided update mechanism to fetch the latest JSON before use【44†L1-L4】. Stale data may miss new sites or old definitions.",
      "corroboration_rules": "Cross-verify findings with other enumeration tools (e.g. Maigret) or by fetching the profile page (`uri_pretty`). Treat each positive result as a hint rather than proof, especially for sites labeled with protection or ambiguous responses【4†L279-L284】.",
      "calibration_todo": "Assess false-positive/negative rates per site by testing known existing/non-existing usernames. Flag sites with poor detection and adjust or disable them. Incorporate site reliability into confidence scoring."
    }
  ]
}
