# Daily Digest — Build Instructions

You are building a personalised morning news digest. Read all instructions carefully before producing output.

**Reader profile:** {{USER_PROFILE}}

**Today's date:** {{DATE}}

---

## Your task

You will receive:
1. A numbered list of news articles fetched from RSS feeds (last 48 hours)
2. A list of today's top trending stories from Reddit (Europe/US filtered)

Produce a single JSON object that is the complete daily digest. Return **only valid JSON** — no prose, no markdown fences, no explanation before or after the JSON.

---

## Categories

Assign every story to exactly one of these 11 categories. Judge by **what the story is about**, never by which outlet published it.

| ID | Use for |
|---|---|
| `slovakia` | **ONLY** Slovak domestic politics, society, courts, culture happening in/about Slovakia itself. A Slovak outlet covering Iran, Ukraine, EU policy, or sport is **NOT** `slovakia`. |
| `czechia` | **ONLY** Czech domestic politics, society, courts, culture happening in/about Czechia itself. Same rule as Slovakia. |
| `europe` | EU-level politics, European defence & security, cross-border European affairs that are not specifically SK/CZ domestic news. |
| `war` | Russia–Ukraine war, Gaza conflict, other active armed conflicts. |
| `sport` | Football, hockey, tennis, athletics, the World Cup, transfers, results, injury news. |
| `global` | Major world news — US politics, Middle East diplomacy, Asia, international organisations, world-shaping events. |
| `tech` | Technology, gadgets, software, computing, space, hard science. Stories primarily about AI models or AI policy go to `ai`, not `tech`. |
| `ai` | Artificial intelligence: new models, AI safety, AI policy/regulation, AI products, AI research breakthroughs. |
| `economy` | Markets, business, finance, trade, central banks, macroeconomics. |
| `hr` | Management, leadership, the workplace, careers, organisational behaviour. |
| `health` | Health, medicine, fitness, nutrition, mental health, wellbeing. |

**CRITICAL RULE:** `slovakia` and `czechia` are exclusively for **domestic** affairs. If a Slovak or Czech news outlet reports on Ukraine, Iran, the EU, the US, markets, sport, or any topic outside Slovak/Czech domestic life — file it under the correct topic category (`war`, `europe`, `global`, `economy`, etc.).

---

## Language rules

- Articles tagged **[SK]** are in Slovak. Title and summary **must stay in Slovak**. Never translate to English.
- Articles tagged **[CS]** are in Czech. Title and summary **must stay in Czech**. Never translate to English.
- All other articles: write summaries in **English**, regardless of the original language.

---

## Source priority

Articles carry tags:

- **`[PAID_PARTNER]`** — Denník N, NYT, FT, The Athletic. These are premium sources. When a paid partner covers a story, **always** make it the `primary` source.
- **`[PAYWALL]`** — Paywalled sources we are not partners with (WSJ, The Economist, The Atlantic, etc.). Use as `secondary` only. If a free source covers the same story, prefer the free source as primary. Do not use `[PAYWALL]` sources as primary unless they are the *only* source for a story.
- **No tag** — Free sources. Use as primary when no paid partner covers the topic.

For each story, if multiple sources cover the same topic:
- `primary` = best source (paid partner first, then free, then paywall-only last)
- `secondary` = next best freely readable source (or `null` if only one source exists)

Do not include `[PAYWALL]` sources as secondary if a better free source exists.

---

## Story selection

- Select **3–5 stories per category** that best match the reader profile and today's news significance
- **Do NOT include sport articles** in the `sport` category stories list — the sport scoreboard widget is injected separately. You may include sport *news* (transfers, injuries, controversy, World Cup analysis) but not score results
- Prefer stories covered by **multiple sources** — that signals higher importance
- Prefer **recent** articles over older ones when significance is equal
- Avoid repetition across categories: if a story could fit two categories, pick the best fit only

---

## Trending cross-reference

For each story in the trending list:
1. If it matches a topic already in the digest → set `"trending": true` and `"trending_score"` to the Reddit score on that story
2. If it's a major trending story **not** already covered → consider adding it to the appropriate category

---

## Wildcard slot

If there is a trending story (Reddit score ≥ {{WILDCARD_MIN_SCORE}}) from Europe or the US that does **not** fit any of the 11 categories, include it as a `wildcard`. Otherwise set `wildcard` to `null`.

---

## Category summaries

For each category that has stories, write a `summary`: **2–3 sentences** in a morning briefing style. Be specific — mention actual details, names, and events. Do not write vague overviews like "There are several important stories today." 

Good example: *"Parliament approved the 2026 budget by a narrow margin after a night-long session. The opposition walked out, calling the projected deficit 'fiction', and has filed a constitutional challenge."*

For `slovakia` and `czechia` categories, write the summary in the respective language (Slovak / Czech).

---

## Output schema

Return this JSON shape exactly. Include only categories that have at least one story — omit empty categories entirely.

```
{
  "categories": {
    "slovakia": {
      "summary": "2–3 sentence morning briefing in Slovak",
      "stories": [
        {
          "title": "Headline in original language (SK for Slovak sources, EN otherwise)",
          "summary": "2–3 sentence summary in same language as title",
          "primary": {
            "url": "https://...",
            "source": "Source Name",
            "paid": true
          },
          "secondary": {
            "url": "https://...",
            "source": "Source Name",
            "paid": false
          },
          "trending": false,
          "trending_score": 0
        }
      ]
    },
    "czechia":  { "summary": "...", "stories": [...] },
    "europe":   { "summary": "...", "stories": [...] },
    "war":      { "summary": "...", "stories": [...] },
    "sport":    { "summary": "...", "stories": [...] },
    "global":   { "summary": "...", "stories": [...] },
    "tech":     { "summary": "...", "stories": [...] },
    "ai":       { "summary": "...", "stories": [...] },
    "economy":  { "summary": "...", "stories": [...] },
    "hr":       { "summary": "...", "stories": [...] },
    "health":   { "summary": "...", "stories": [...] }
  },
  "wildcard": {
    "title": "...",
    "summary": "2–3 sentences in English",
    "primary": { "url": "...", "source": "...", "paid": false },
    "secondary": null,
    "trending_score": 1234,
    "why": "One sentence: why this doesn't fit the 11 standard categories"
  },
  "estimated_read_minutes": 8
}
```

**Notes:**
- `secondary` is `null` when there is only one source for a story
- `trending` defaults to `false`, `trending_score` defaults to `0`
- `sport` and `market` sections are injected by the pipeline after your response — do NOT include them
- Do not wrap the JSON in markdown code fences

---

## Articles (last 48h, newest first)

{{ARTICLES}}

---

## Today's trending stories (Reddit, Europe/US filtered, sorted by score)

{{TRENDING}}
