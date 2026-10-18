fix(api): reject reviews for profiles with no content (#36)

## Summary

I added a check before a review is created. A profile with no GitHub username, portfolio URL, or resume text now returns HTTP 422 instead of creating a review with no content. A missing profile returns HTTP 404.

## Issue

Closes #36

## Changes

- In `api/routes/reviews.py`, I load the profile before creating the review, return 404 or 422 when needed, and update the route docstring.
- In `core/services/review_service.py`, I added `profile_has_ingestible_content` to check the three content fields for non-blank strings.
- In `tests/unit/test_review_routes.py`, I added tests for empty content, blank content fields, and a missing profile. Each checks that no review is created.

## Testing

- [ ] **CI is green on this PR (all five jobs)** — not run yet; this is the pre-PR draft.
- [x] Unit tests pass (`make test-unit`)
- [ ] Integration tests pass (`make test-integration`)
- [x] Linter passes (`make lint`)
- [x] Type checker passes (`make typecheck`)
- [x] New/updated tests cover the changes
- [ ] If this fixes a seeded bug: removed its `@pytest.mark.xfail` marker (and any matching suppression in `pyproject.toml`)

I ran the Makefile's commands directly because GNU make is not installed on this Windows environment. The `make` commands themselves could not run. With Python 3.12.13:

```text
.venv/Scripts/pytest tests/unit -v -m unit --tb=short
378 passed, 53 xfailed, 8 warnings in 11.58s
Exit code: 0

.venv/Scripts/pytest tests/integration -v -m integration
collected 0 items
Exit code: 5 (no tests collected, expected for this repo)

.venv/Scripts/ruff check .
All checks passed!
Exit code: 0

.venv/Scripts/mypy api/ core/ ingestion/ rag/ agent/ safety/
Success: no issues found in 76 source files
Exit code: 0

.venv/Scripts/pytest tests/unit/test_review_routes.py -q --tb=short
3 passed
Exit code: 0
```

The first full unit run had 30 setup errors while tokenizer data and caches were blocked by the sandbox. The rerun with network and cache access passed without code changes. I found no `issue #36:` xfail marker or matching suppression to remove.

Before, from the recorded Unit 3 run on main `f89c06f`:

```text
HTTP 200
ingestion_pipeline_completed sources_count=0
review_processing_completed overall_score=0.81
FINAL complete 0.81
```

For the after check, I reran the original script embedded in Unit 2 `reproduction.md`, without editing it. It failed in the stand-in session, so this is not a successful rerun of the full reproduction:

```text
KeyError: 'review'
review_creation_error
Exit code: 1
```

That script assumes the old database-query order and reads `created["review"]` before a review exists. The three route tests use the current query order and pass: empty or blank content returns 422 with no review created, and a missing profile returns 404 with no review created. The original repro still needs an updated stand-in before it can confirm the complete before/after scenario. Full check output is saved locally in `test_evidence.md`.

## Screenshots / Demo

N/A. This changes an API response and has no visible UI change.

## Notes for Reviewers

I had codex help me write the PR-precheck skill files, and it also helped to run the eval/tests files, as well as to prepare the PR materials, in unit patch I had claude assist me in the same way as Codex

The committed diff matches the three files in the plan. I did not change agent orchestration, RAG, or ingestion. The check uses the profile's content fields rather than querying stored `IngestedSource` rows, as the plan states. The original reproduction could not be rerun successfully with its old stand-in; that validation gap is disclosed above. CI and frontend checks have not run yet.

