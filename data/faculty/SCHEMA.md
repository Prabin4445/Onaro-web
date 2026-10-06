# Faculty Data Schema (stable — backend importer contract)

> This schema is STABLE. The coordinator will not change field names, shapes, or
> file layout without bumping the version note below. Backend importers may rely
> on this document.

**Schema version:** 1.0 (2026-09-30)

## Files

- `data/faculty/index.json` — the registry. The app resolves campuses ONLY through this file.
- `data/faculty/<slug>.json` — one file per institution, named by the canonical slug.
- `data/faculty/master-list.json` — collection bookkeeping (statuses per institution).
- `data/faculty/ATTRIBUTION.txt` — human-readable per-batch source log.
- `data/faculty/_batch-*.json` — worker manifests (provenance, not needed by the app).

## index.json

```json
{
  "colleges": [
    {
      "slug": "mcneese-state-university",
      "name": "McNeese State University",
      "country": "US",
      "match": ["mcneese-state-university", "McNeese State University", "McNeese"],
      "source": "https://www.mcneese.edu/directory",
      "retrieved": "2026-09-29",
      "count": 243
    }
  ]
}
```

| field | type | notes |
|---|---|---|
| `slug` | string | canonical, kebab-case, unique; matches `<slug>.json` filename |
| `name` | string | official institution name |
| `country` | string | one of `US`, `CA`, `MX`, `AU` |
| `match` | string[] | alias list for forgiving campus matching; always includes slug + name |
| `source` | string | exact official directory URL the data came from |
| `retrieved` | string | `YYYY-MM-DD` collection date |
| `count` | integer | MUST equal `len(professors)` in `<slug>.json` (file truth wins on conflict) |

## <slug>.json

```json
{
  "college": "McNeese State University",
  "country": "US",
  "professors": [
    {"name": "Jane A. Smith", "title": "Associate Professor", "dept": "Biology", "courses": ["BIOL 101"]}
  ]
}
```

| field | type | notes |
|---|---|---|
| `college` | string | official institution name (mirrors index entry) |
| `country` | string | one of `US`, `CA`, `MX`, `AU` |
| `professors` | object[] | every record has non-empty `name`; `title`/`dept` may be `""` when the directory doesn't publish them; `courses` is a string array, often `[]` |

## Data guarantees

- Every name comes from the institution's own public directory. Never fabricated, never from third-party aggregators.
- `count` in index.json is reconciled to file truth before every merge.
- Reviews/ratings are NOT in these files — they live in the app's user-data layer, anonymous by product rule.
- Profanity filtering applies to user-generated content, not directory data.
