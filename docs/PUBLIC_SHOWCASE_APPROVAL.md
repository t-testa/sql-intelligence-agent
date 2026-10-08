# Proposed public showcase — private review plan only

**Nothing is approved for public publication.** This document lives in the private source repository.
No separate showcase repository, site, export bundle or video has been created. Do not create or publish
one until the owner explicitly approves its exact contents. The complete application remains PRIVATE.

## Proposed content set for later review

| Content | Proposed scope | Required sanitation before approval |
|---|---|---|
| Two screenshots | Synthetic analytical result; permanent Learning Mode and independent comparison | Crop browser chrome; remove URLs, account names, deployment/resource identifiers, local paths and tabs; inspect full resolution |
| 60–90 second demo video | Ask the approved synthetic question, inspect SQL/results, explain validation and Learning Mode | Use a clean recording; no sign-in, portals, terminals, environment files, tokens, notifications or address bars; review every frame and audio |
| Architecture overview | Generic Entra → private UI → authorized API → SQL gateway → private SQL/model diagram | No tenant/subscription/resource IDs, hostnames, IP addresses or usable endpoints |
| Technology stack | Azure OpenAI, Azure SQL, Container Apps, Entra, FastAPI, Streamlit, Python | Product names only; no private configuration or executable deployment content |
| Verification summary | Dated finite-set live results, offline regression/security methodology and honest limitations | Approved aggregate facts only; no raw traces/receipts/request IDs, fixtures, logs or test source |

Suggested video sequence: brief project purpose; highest-invoice result with deterministic tie-breaking;
generated SQL display; existing Learning Mode explanation and independent comparison; static summary
of measured results and limitations. This is a storyboard, not a recording request or approval.

The current private screenshots in `docs/images/` are **candidates, not approved public assets**. Their
deployment label/browser details still need a separate sanitation review. Do not copy them to a public
destination automatically. Do not include executable backend/frontend source, notebooks, SQL scripts,
Docker/Bicep files, dependency files, API specifications, container images, raw evaluation recordings,
private environment files, customer data, credentials or usable API endpoints. No live iframe/API calls.

## Approval and publication procedure

When the owner asks to proceed with content review, prepare only the expressly authorized sanitized
copies and final text/video for private inspection. Record filenames, hashes, versions, caption text,
intended destination and owner approval for that exact set. Any subsequent content change needs review.

Only after explicit approval may a **separate** public static showcase be created/published. Start with
new history and only the approved content; never fork, mirror, push or change visibility of the full
source repository. Keep public assets independent of private CI/artifacts and application endpoints.
Inspect the final public file list/history, media metadata and page network requests. No invitations,
GitHub access changes or Azure grants are implied. A public showcase never authorizes app access.

GitHub API metadata confirmed the owner-created source repository `t-testa/sql-intelligence-agent`
is PRIVATE on October 8, 2026, with Pages disabled. The owner authorized an audited push to that private
repository only. This grants no approval to create or publish the separate public showcase.
