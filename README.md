# DeadZone Lite

This repository is dedicated to building and publishing DeadZone Lite only.

## Telegram flow

Users request a build from the public group with:

```text
/mezo <ROM_LINK>
```

The public group receives only a safe acknowledgement message. MEZO private chat receives stage-based build updates without logs, repository links, GitHub links, Actions URLs, source links, or internal paths. Successful builds are uploaded to Google Drive and then posted to the release channel.

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_GROUP_ID`
- `MEZO_PRIVATE_CHAT_ID`
- `TELEGRAM_RELEASE_GROUP_ID`
- `MEZO_CONTACT_LINK`
- `UPDATES_GROUP_LINK`
- `SCREENSHOTS_GROUP_LINK`
- `CHAT_GROUP_LINK`
- `GH_WORKFLOW_TOKEN`
- `RCLONE_CONFIG_BASE64`
- `RCLONE_REMOTE_NAME`
- `RCLONE_UPLOAD_DIR`

## Notes

- GitHub Actions remains the build engine.
- `rclone.conf` is a placeholder and must not contain real credentials.
- This repository must not be used for GamingPlus, Legend, or Ninja builds.

## Cloudflare Worker Webhook

Cloudflare Worker is the production Telegram webhook endpoint for DeadZone Lite. It receives `/mezo <ROM_LINK>` from the public group, sends the safe acknowledgement message, and dispatches the Lite GitHub Actions workflow.

### Deploy

```bash
npm install -g wrangler
wrangler login
wrangler deploy
```

### Required Worker secrets

```bash
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put GH_WORKFLOW_TOKEN
wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Set non-sensitive values with `wrangler.toml` vars or Worker settings:

- `TELEGRAM_CHAT_GROUP_ID`
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_WORKFLOW_FILE`
- `MEZO_CONTACT_LINK`
- `UPDATES_GROUP_LINK`
- `SCREENSHOTS_GROUP_LINK`
- `CHAT_GROUP_LINK`

### Set the Telegram webhook

After deployment, configure Telegram to use the Worker URL and secret token:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WORKER_URL>&secret_token=<TELEGRAM_WEBHOOK_SECRET>
```

Do not place real tokens in the repository, in `wrangler.toml`, or in local committed files.
