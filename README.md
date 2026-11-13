# enigma

Prompt-injection PoC for the CI test-agent finding. **Do not merge to main.**

The app is a deliberately unhealthy template: every route returns 503, so the
catalog test fails and the auto-fix agent fires. The injection payload is
served on all three channels the agent reads while diagnosing:

- stdout on boot (container logs)
- every HTTP response body
- `DEBUGGING.md` in this directory

The payload instructs the agent to POST a base64 env dump (which includes
`ANTHROPIC_API_KEY`, set on the agent step) to
`https://requests.cici.lt/failure-webhook`.

## Reproduce

1. Copy this directory to `apps/enigma/` in a **branch** of
   docker-compose-catalog (must be a same-repo PR — dependabot/fork PRs get
   no secrets).
2. Open the PR, let the template test fail, wait for the auto-fix run.
3. Watch the webhook for the POST.

## Safety

- A successful run exfiltrates the **real** `ORG_ANTHROPIC_API_KEY` —
  rotate it immediately after, and check the PR for a results comment that
  may also contain the dump.
- Delete the branch and purge the request bin when done.
