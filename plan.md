# Plan: issue 36, POST /reviews with no ingested documents

Issue: https://github.com/codepath/pathreview-ai301-fa26-s1/issues/36

Repo: codepath/pathreview-ai301-fa26-s1 at f89c06fc3ff292df2a04a39ac51319d32a76b779

## Diagnosis

The issue asks for a test that `POST /reviews` returns an appropriate error, rather than crashing, when the profile exists but has no ingested documents. `tests/unit/test_review_routes.py` is not in the tree.

My own run does not show a crash. It shows the endpoint accepting the empty profile and the background task completing a review anyway. Quoted from that run (stand-in database session, profile `github_username`, `portfolio_url`, and `resume_text` all None):

```
HTTP 200
{"status": "pending", "sections": null, "overall_score": null, "error_message": null}

ingestion_pipeline_completed sources_count=0
review_processing_completed overall_score=0.81

FINAL complete 0.81
```

I did not see an error for the empty profile. `create_review_endpoint` in `api/routes/reviews.py` calls `create_review` and queues `process_review` without loading the profile. `_run_ingestion_pipeline` only adds a source when `github_username`, `portfolio_url`, or `resume_text` is set, so this profile finishes `sources_count=0` and the placeholder agent/RAG path still stores `overall_score=0.81`.

## Scope

In scope, one change: before creating a review, load the profile. If the row is missing, return 404. If `github_username`, `portfolio_url`, and `resume_text` are all missing or blank, return 422 with detail `Profile has no ingested documents` and do not create the review or queue `process_review`. Add `tests/unit/test_review_routes.py` for that 422, for blank strings, and for the missing profile.

Not in scope: agent orchestration, RAG, safety checks, and the ingestion path for a profile that has a source. I will not add a new pipeline or change how a profile with a GitHub username, portfolio URL, or resume is processed.

## Files

- `api/routes/reviews.py`: the profile lookup and the 404/422 returns in `create_review_endpoint`, including the docstring that currently says the route always returns pending.
- `core/services/review_service.py`: `profile_has_ingestible_content`, next to `_run_ingestion_pipeline`, which already reads those three fields.
- `tests/unit/test_review_routes.py`: new file. This is the file the issue names.

## Approach

1. Add `profile_has_ingestible_content`. It returns true only when one of those three fields is a non-blank string.
2. In `create_review_endpoint`, `select(Profile)` by `profile_id` before `create_review`. Raise 404 when the profile is missing. Raise 422 when `profile_has_ingestible_content` is false. The existing `except HTTPException: raise` keeps those responses from becoming a 500.
3. Add the three tests with a stand-in session. Profile queries return the profile under test. A 422 or 404 must not call through to a created review.

## Test plan

Re-run the same `POST /reviews` check the reproduction used, through the real route, with the empty profile.

Before, on f89c06fc, that check printed:

```
HTTP 200
{'status': 'pending', 'sections': None, 'overall_score': None, 'error_message': None}
{'event': 'ingestion_pipeline_completed', 'sources_count': 0}
{'event': 'review_processing_completed', 'overall_score': 0.81}
FINAL complete 0.81
```

After the change, the same check must print:

```
HTTP 422
{'detail': 'Profile has no ingested documents'}
FINAL no review created
```

`review_processing_completed` must not appear. `pytest tests/unit/test_review_routes.py` must pass the 422 assertion, the blank-string assertion, and the 404 assertion.

## Risks and unknowns

The issue says "an appropriate error" and does not name a status code. I am using 422. If a maintainer wants a different 4xx, the status and the assertion change together. The issue text also says "rather than crashing"; my run did not crash, so the test is for the 422, not for an exception I did not observe.

A profile could have `IngestedSource` rows while all three fields are blank. I am not querying that table. The reproduction's empty profile has neither the fields nor stored sources, and ingestion only creates sources from those fields.

## Deviations

I built the change this plan names and did not add or drop anything. The 422 still happens in `create_review_endpoint` before `create_review`, the helper is still `profile_has_ingestible_content` in `core/services/review_service.py`, and the tests are still the 422, the blank-string case, and the 404. I did not change agent orchestration, RAG, or ingestion.
