# Security policy

## Sensitive configuration

Never include `.env`, `PHPSESSID`, Telegram/Discord bot tokens, chat IDs, server credentials, logs containing personal data, or runtime state in an issue or commit.

If a credential is exposed, revoke or rotate it immediately. Removing it from the latest commit is not sufficient because it may remain in Git history.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that may expose accounts, credentials, or user data. Contact the repository owner privately through the contact method listed on their GitHub profile. Include a concise description and reproduction steps, but redact all real credentials and personal data.

