# Search Gap Radar — v5 Free-Only Delta

> Apply on top of `SEARCH_GAP_RADAR_MASTER_PLAN_v4.md`. Where this file and v4 disagree, **v5 wins**.
> **Hard rule:** no paid APIs, no paid hosting, no paid SERP or Trends providers. Free accounts and free API keys are allowed. Anything that asks for a payment method beyond a free-tier signup is out.

---

## 1. What is free and what is not

| Need in v4 | v4 choice | v5 choice | Cost |
|---|---|---|---|
| Runner | Unspecified VPS | **Oracle Cloud Always Free Arm VM** (2 OCPU, 12 GB RAM total in 2026), fallback: Google Cloud e2-micro (1 GB, US regions) | $0 while within Always Free limits |
| Trends batches | Browser batch on runner | Same, on the runner, with breakers. Official Trends alpha if Google accepts you. | $0 (alpha application is free) |
| Screening SERP | Brave Search API | **None.** Replaced by free evidence sources (§2). | $0 |
| Verifying SERP | Licensed SERP API | **Human check** of the final 5–10 briefs, using a link in each brief (§3). | $0 |
| Dev signals | GitHub, SE, HN, npm, PyPI, RSS | Same, all free. Free GitHub token and free Stack Exchange key recommended. | $0 |
| Demand history | Wikipedia pageviews etc. | Same, all free. | $0 |
| Domain popularity | Tranco | Same, free. | $0 |
| LLM judge / embeddings | Local model | Local, free models only (see §5). | $0 |
| Dashboard | Datasette | Same, free. | $0 |

**Things that are free but come with a catch**
* **Oracle Always Free** requires a card at signup, has regional capacity limits, and reclaims idle instances. Oracle also cut Ampere A1 limits in 2026 (from 4 OCPU / 24 GB to 2 OCPU / 12 GB). Stay inside the Always Free shapes and set a billing alert.
* **Google Trends browser scraping** is free, but it is against Google's terms, and Google rate-limits datacenter IPs quickly. Treat it as the least reliable source. Keep the breaker and the fallback.

---

## 2. Replacing the SERP audit with free evidence

No free service returns reliable Google results at this scale. The audit is redesigned around sources that have free official APIs, and it is honestly weaker than the paid version. Each item is labelled with its evidence level so you can judge it.

### 2.1 Free evidence sources per vector

| v4 vector | Free replacement | Source | Evidence level |
|---|---|---|---|
| **1. Unresolved thread** | Search Stack Overflow for the query's words; count open, unaccepted questions and their age. Search GitHub issues the same way. | Stack Exchange `/search/advanced` API, GitHub search API | Strong |
| **2. Title void** | Count existing **answered** questions and existing repos whose titles or names already cover the query. A query with many answered matches is saturated. | Stack Exchange search API, GitHub repo search | Medium |
| **3. URL depth mismatch** | Only for an **allowlist of docs and blog domains** you choose: check whether a dedicated page exists at a matching path. | Direct HTTP to allowlisted sites (respect robots.txt) | Medium |
| **4. Document leaks** | Skip in automatic mode. Covered by your human check. | — | Human only |
| **5. Free subdomain leaks** | Skip in automatic mode. Covered by your human check. | — | Human only |
| **6. Content obsolescence** | Dates of the answered Stack Overflow matches and of the newest GitHub repos. Fast-moving tags with no answer in 2+ years count as stale. | Stack Exchange and GitHub `creation_date` / `last_activity` | Medium |

**Scoring impact.** The Gap score (0–70) stays the same, but vectors 4 and 5 are no longer computed automatically, so their points are set to **0 with a flag `unverified_by_human`**. A candidate can reach Gold only after your human check confirms the gap. Without that check, the maximum status is High.

### 2.2 Demand is unchanged

Demand still uses Trends (if available), Wikipedia pageviews, npm and PyPI download changes, GitHub activity, Stack Exchange volume and Hacker News. The Demand gate from v4 still applies.

---

## 3. Human verification step (free and required for Gold)

For every item in the daily brief, the brief includes a **pre-filled search link** (for example, `https://www.google.com/search?q=<query>`). You open it in your normal browser and mark it in Datasette:

* `confirmed_gap`: the top results do not satisfy the query. Status becomes **Gold** if the score allows.
* `already_served`: the top results satisfy it. Recorded as reject, with this reason fed back to the learner.
* `unclear`: keep for a later check.

**Why this is allowed:** you are doing ordinary manual browsing, which is not crawling. It is limited to about 10 queries a day. The pipeline itself never requests a search results page.

This step also serves as the **ground truth for calibration** (v4 Component G4). Your decisions are the labels.

---

## 4. Runner setup (free)

**Primary: Oracle Cloud Always Free Arm VM**
* Shape: `VM.Standard.A1.Flex` with 2 OCPU and 12 GB RAM, one instance. Ubuntu 24.04 aarch64.
* Keep the instance inside the Always Free allowance. In the OCI console, check the "Always Free" label on the shape and the Limits, Quotas and Usage page.
* Keep it active: the scheduler's regular jobs count as activity. Check it weekly.
* Create the account with a billing alert at $1 so any accidental charge shows up immediately.
* Capacity can be unavailable in some regions. Try another availability domain, or use the fallback.

**Fallback: Google Cloud `e2-micro`** (1 GB RAM, US regions only).
* 1 GB is too small for a headless browser plus an embedding model. Use it only for the signal ingestors and the SQLite database, and run the Trends browser batch on Oracle.

**Not allowed:** your home machine, any paid instance, any free trial that converts to paid automatically.

**Free accounts used:** GitHub (token), Stack Exchange (app key), Oracle Cloud, Google Cloud (fallback only). No credit card is used beyond what those free tiers require.

---

## 5. Free models and compute

* **Embeddings:** a small open model run locally on the VM (CPU is enough for clustering a few thousand short queries per day).
* **Intent judge / archetype adjudicator:** optional. A small open model via Ollama on a 12 GB VM is workable but slow. If it is too slow, the classifier uses keyword priors and the free SERP features from §2 only. Close calls go to the human check.
* **Antigravity:** use its free tier and free-quota models only. If you switch to a paid model tier, the cost is yours; avoid it while this project runs on $0.

---

## 6. Rule updates (replaces the paid-API parts of the rules file)

Replace the "Search data comes only from…" bullet in `.agents/rules/radar-core.md` with:

```markdown
- Search evidence comes only from free official sources: Stack Exchange API, GitHub API, Hacker News Algolia,
  npm and PyPI public stats, Wikipedia Pageviews, Tranco, and allowlisted docs domains (robots.txt respected).
- Google Trends: browser batch on the runner behind a circuit breaker, OR the official alpha if accepted. No managed Trends providers.
- Do NOT add any paid API, paid SERP service, paid proxy, or paid hosting. Do NOT add Brave Search API, SerpApi, DataForSEO,
  Bright Data, or any service that requires a payment method. If a task seems to need one, stop and write an ADR.
- Google search results are NEVER requested by the pipeline. Human verification happens in the user's own browser (see SPEC v5 §3).
- Free API keys (GitHub, Stack Exchange) are stored only in `.env`.
```

---

## 7. Phase changes

| Phase | Change |
|---|---|
| 0 — Spikes | S2 (Brave) and S3 (licensed SERP) are **removed**. Add **S5: free-evidence recall**: for 30 queries you already checked by hand, does the free evidence (SE, GitHub, allowlisted docs) agree with your judgment at least 70% of the time? |
| 3 — Shield and screening | Replace the Brave provider with the free evidence providers from §2. Rate controller and cache unchanged. |
| 4 — Scoring | Vectors 4 and 5 default to `unverified_by_human`. Gold requires a human `confirmed_gap`. |
| 5 — Verification and outputs | Replace licensed-SERP verification with the human-check links and Datasette decision buttons (§3). |
| 6 — Operations | Oracle Always Free runner setup, billing alert, and the weekly activity check. |

---

## 8. Updated phase prompts (paste these in place of the v4 versions for the changed phases)

### Phase 0 — Spikes (replaces v4 Phase 0)
```text
/phase Phase 0 — spikes on the free runner only. Nothing runs from the developer's home machine, and nothing requests a search results page.

S1 (Trends batch): as in SPEC v4 §3 Component A, 1 anchor + 7 seeds, 50 batches max, stop on any 429 or CAPTCHA page. Pass: ≥ 90% of batches return Top and Rising for 7 of 8 terms.

S4 (free official signals): run the Stack Exchange, GitHub, Hacker News, npm, PyPI and Wikipedia ingestors for 3 days. Pass: ≥ 1,000 canonical candidates per day, zero unhandled errors.

S5 (free-evidence recall): for 30 queries that the developer has already checked by hand, run the free evidence checks from SPEC v5 §2 and report the agreement rate with the developer's judgment. Pass: ≥ 70%.

Write each result to docs/spike_*.md with GO or CHANGE-DESIGN. Stop before any step that needs a paid service or a key not in the free list.
```

### Phase 3 — Shield and free screening (replaces v4 Phase 3)
```text
/phase Phase 3 — Shield and free screening (SPEC v5 §2, v4 §3 Component C).
Implement the exclusion shield with allow-list overrides, the free evidence providers (Stack Exchange search, GitHub repo and issue search,
allowlisted docs checks with robots.txt), the shared rate controller with circuit breakers, the cache (7–14 day TTL), and vectors 1, 2, 3 and 6 computed from that evidence.
Vectors 4 and 5 are set to unverified_by_human.
Acceptance: 500 queries screened with under 5% of requests blocked; every vector value reproducible from its stored evidence; zero requests to any search results page.
```

### Phase 5 — Verification and outputs (replaces v4 Phase 5)
```text
/phase Phase 5 — Human verification and outputs (SPEC v5 §3, v4 Component H, I).
Build the daily brief with pre-filled search links for each item, the Datasette decision buttons (confirmed_gap, already_served, unclear), and `radar decide`.
Confirmed gaps become Gold. Unverified items are capped at High. Decisions feed the reward updates.
Acceptance: seven days of briefs, each with 5–10 items and working search links, and the decision records update the arm and source rewards correctly in a test database.
```

---

## 9. Free-only success criteria

* Monthly spend: **$0**. Any charge triggers the billing alert and a review.
* Brief produced daily with no manual steps other than the human check.
* Repeat pulls on the same day: zero.
* Human-confirmed Gold rate: track it. If it stays below about 30% after four weeks, the screening is too loose and the thresholds need tuning.

---

## 10. What you give up compared with the paid version

* Automatic SERP checks for document leaks and free-subdomain leaks. Covered by your manual check.
* Automatic AI Overview detection. Look at the Google results yourself during the human check, or drop the AIO factor from scoring.
* Breadth of automatic SERP coverage. Expect fewer, better-checked candidates.

This trade-off is deliberate. It keeps the pipeline running on $0 and limits how often it touches third-party services.
