---
name: onboard-client
description: Use this when a new client onboarding request arrives via email or form submission. Do NOT use for existing-client requests or for changing an already-onboarded client's details — use the update-client skill for those.
---

# Client onboarding

## Inputs
- Client contact record from the email or form payload.
- KYC document attachments, if present.

## Procedure
1. Call `lookup_client` with the email address. If a match exists, stop and ask for human confirmation.
2. Call `create_client_record` with the parsed contact fields.
3. For each KYC attachment, call `store_kyc_document` with the document and the new client id.
4. Call `send_welcome_email` with the new client id and the welcome template variant matching the firm.
5. Write a one-line note to the operations log via `append_ops_log`.

## Stop conditions
- Duplicate match in step 1 → escalate to human.
- Any tool returns an error → escalate to human and do not retry silently.
