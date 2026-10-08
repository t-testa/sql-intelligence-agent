# Private source publication audit

October 8, 2026. The owner created
[`t-testa/sql-intelligence-agent`](https://github.com/t-testa/sql-intelligence-agent)
and explicitly approved connecting and pushing this existing project after a credential audit.
This approval covers the PRIVATE source repository only. Azure deployment, public application access,
public showcase creation, collaborator invitations and new access grants remain unapproved.

## Repository verification

An authenticated, read-only GitHub API request returned `private: true`, `visibility: private`,
`has_pages: false`, default branch `main`, and push permission for the existing credential.
The repository was empty before publication. The GitHub connector could not see the new repository;
verification used the existing Git Credential Manager identity instead. Credentials stayed in memory
and were excluded from command output, reports and project files.

The intended destination is `origin/main`; the existing local `codex/m1-local-mvp` branch and original
commit history are preserved. No forced update, visibility change or collaborator grant is needed.
Recheck repository privacy immediately before and after the push, and compare the remote branch SHA
with the local commit. The final push receipt belongs in ignored local artifacts, not in this document's
own commit. Visibility is a point-in-time observation, not a guarantee against future owner changes.

## Audit scope and results

- **Gitleaks 8.30.1:** official Windows binary downloaded from the upstream release; archive verified
  against the published SHA-256 checksum. Full existing Git history, including all refs/reflogs, and
  the complete intended file snapshot passed with **zero findings**. Inline suppression comments were
  ignored and reports were redacted. The final committed history must pass the same scan before push.
- **Independent configured-secret check:** all four populated local credential values (Azure API key,
  SQL administrator/runtime passwords and local API bearer token), including URL/base64 variants,
  were checked against candidate files and every local blob, commit and tag object. **Zero matches.**
  Only variable names, object IDs and pass/fail counts are reported; values remain in memory.
- **Exclusions:** `.env` is ignored and untracked, with no `.env` in history. `.env.example` contains
  empty credential fields and is intentionally tracked. `.local/`, `artifacts/`, virtual environments,
  caches, local database/backup files, logs, temporary outputs and private key files are excluded.
  No tracked file is accidentally covered by those exclusion rules.
- **Reviewed evidence:** deterministic fixtures, reference outputs, recorded live cases and the two
  private screenshots remain intentional project files. Both screenshots were visually inspected;
  they contain synthetic application data, no credentials and no EXIF metadata. They are not approved
  public showcase assets. Synthetic test tokens are test fixtures, not configured runtime credentials.
- **Final staging gate:** scan the exact index snapshot, confirm its file manifest and preserve the
  evidence hashes below before committing. There are 118 intended files including this audit record.

These checks found no exposed secrets in their defined scope. Pattern/entropy and known-value scans
cannot prove that every possible unknown secret is absent. Repeat the audit before future pushes;
never commit raw local reports, environment files or authentication output.

## Regression and preservation

The prepublication regression run passed **443/443 tests**, zero skipped, against the existing local
synthetic SQL Server. This includes Learning Mode, the security gateway, recorded live replay and
database permission denials. No live inference calls were made. Ruff lint/format and strict mypy
also passed. One upstream Starlette/AnyIO deprecation warning remains; there were no test failures.

The sandbox initially could not reach local SQL; rerunning with local database access passed in
7.62 seconds. The earlier live model evaluation remains **61/61 on the finite supported corpus**;
it was not rerun or represented as new cloud evidence in this publication task.

Preserved SHA-256 evidence:

| File | SHA-256 |
|---|---|
| `evaluation/cases.json` | `a0d9d4c0920c7cc6047bf1dc7a9ccf85d3d4251940e24e8fe3994a571e46cc1b` |
| `evaluation/recordings/accepted.json` | `8200b990442f10e655536240d4579983beff78e0ce2f571cbc2b8393d4a6a856` |

Git attributes preserve the original bytes of the evaluation evidence on Windows and Linux. The
application, permanent SQL Learning Mode, mock regression mode and original 218-test baseline remain
included. No application behavior was changed for this publication task.

Private local evidence is under `artifacts/`: repository metadata, redacted Gitleaks reports,
publication manifests/configured-secret checks and `github-publication-tests.xml`. CI requires a
private repository, uses read-only repository permissions and contains no Azure deployment step.
The remaining Azure authentication and deployment gates are in
[private verification](PRIVATE_VERIFICATION.md).
