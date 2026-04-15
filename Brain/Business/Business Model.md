---
tags: [zima, business, pricing, revenue]
created: 2026-03-21
---

# Business Model

← [[../Zima|Zima Home]]

---

## Goal

**£500/month by Month 6** → £5K/month within 18 months.
Path: 50 customers × £10/month. 2% free → paid conversion.

---

## Pricing

| Tier | Price | Target |
|---|---|---|
| **Free** | £0 | Lead generation, demonstrate value |
| **Core** | £10/month or £50/year | Individuals — essential hygiene |
| **Plus** | TBD | Advanced users |
| **Pro** | TBD | Freelancers |
| **Business** | TBD | Small businesses |

### Free Tier (Lead Generation)
- One-time security audit
- Basic breach check
- Security score (0–100)
- Top 5 critical findings
- 3 core playbooks (read-only)

### Core / Pro Tier: £10/month
- Continuous monitoring (weekly scans)
- Email alerts for new breaches/findings
- Full playbook library
- Domain security scanning
- PDF report export
- Priority email support

---

## Revenue Math

```
Path A (Monthly): 50 × £10/month = £500 MRR
Path B (Mixed):   30 monthly (£300) + 48 annual (£200/month equiv) = £500 MRR
First year goal:  75 total paying customers
```

**Unit economics:**
- Revenue per customer: £10/month
- Variable cost: ~£0.89/month (infra, Stripe fees)
- Gross margin: ~91%

**At 50 customers:**
- Revenue: £500
- Fixed costs: ~£50
- Variable costs: £45
- **Profit: ~£405/month**

---

## Target Market

**Primary:** Freelancers and micro-businesses (UK)
**TAM:** 5.5M freelancers in UK alone

### Personas

| Persona | Profile | Pain |
|---|---|---|
| Sarah, Freelance Designer | Handles client files, low security knowledge | Worried about data breaches damaging reputation |
| James, Solo Consultant | Custom domain email, moderate tech knowledge | Needs professional security posture |
| Emma, Online Store Owner | Processes payments, low security knowledge | PCI compliance, customer data protection |

---

## Growth Strategy

| Phase | Approach |
|---|---|
| Month 1–3 | Organic: SEO content, Reddit, Indie Hackers, ProductHunt |
| Month 4–6 | Partnerships: freelance communities, domain registrars |
| Month 7–12 | Paid acquisition if LTV:CAC > 3:1 |

### Free → Paid Conversion Triggers
1. New breach detected (email alert → upgrade for monitoring)
2. After viewing 3+ playbooks (paywall)
3. Domain scan requested (Pro feature)
4. PDF export attempt (Pro feature)
5. Day 7 drip email

---

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Low willingness to pay | Validate with landing page, offer annual discount |
| High churn after fixing issues | Continuous monitoring value, expand playbook library |
| HIBP API dependency | Abstraction layer, multiple breach sources (LeakCheck next) |
| GDPR liability | Minimal data retention, clear ToS, consent at signup |
| Competitor undercutting | Focus on UX simplicity, community, ship fast |

---

## Validation Checklist (Pre-Launch)

- [ ] 50+ email signups from landing page
- [ ] 10+ user interviews confirm pain point
- [ ] 5+ people commit to paying
- [ ] Conversion funnel defined and tested

---

## See Also

- [[Market & GTM]] — channels, content strategy, launch plan
- [[MVP Master]] — current build status
- [[threat-model]] — threat actors and mitigations
- [[../Architecture/Design Principles]] — platform rules
