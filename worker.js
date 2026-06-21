const PUBLIC_ACK_MESSAGE = `✅ ROM Link Received Successfully

Your ROM link has been sent to MEZO for processing.

⏳ Estimated build time: 40–60 minutes
Please wait until the process is completed.

━━━━━━━━━━━━━━

 DeadZone Lite is now being prepared for you.

Looking for something more powerful?

 DeadZone GamingPlus
 DeadZone Legend
 DeadZone Ninja

These premium systems include more advanced features, stronger optimization, and a more exclusive experience.

 Premium ROMs are paid systems.
 For details, contact MEZO:
\${MEZO_CONTACT_LINK}

━━━━━━━━━━━━━━

 Updates Channel
\${UPDATES_GROUP_LINK}

 Screenshots Channel
\${SCREENSHOTS_GROUP_LINK}

 Community Chat
\${CHAT_GROUP_LINK}

✨ Thank you for choosing DeadZone.`;

const INVALID_USAGE_MESSAGE = "⚠️ Usage:\n`/mezo <ROM_LINK>`\n\nPlease send a valid ROM download link.";
const DISPATCH_FAILURE_MESSAGE = "❌ Failed to submit your request. Please contact MEZO.";
const HEALTH_RESPONSE = "MEZO Lite Telegram webhook is running.";

export default {
  async fetch(request, env) {
    try {
      if (request.method !== "POST") {
        return new Response(HEALTH_RESPONSE, {
          status: 200,
          headers: { "content-type": "text/plain; charset=UTF-8" },
        });
      }

      const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
      if (!secretHeader || secretHeader !== env.TELEGRAM_WEBHOOK_SECRET) {
        return new Response("Forbidden", { status: 403 });
      }

      let update;
      try {
        update = await request.json();
      } catch {
        return new Response("Bad Request", { status: 400 });
      }

      const message = update?.message;
      if (!message || typeof message.text !== "string") {
        return new Response("OK", { status: 200 });
      }

      const chatId = String(message.chat?.id ?? "");
      if (chatId !== String(env.TELEGRAM_CHAT_GROUP_ID)) {
        return new Response("OK", { status: 200 });
      }

      const parsed = parseMezoCommand(message.text);
      if (!parsed.isCommand) {
        return new Response("OK", { status: 200 });
      }

      if (!parsed.romLink) {
        await sendTelegramMessage(env, chatId, INVALID_USAGE_MESSAGE, message.message_id);
        return new Response("OK", { status: 200 });
      }

      await sendTelegramMessage(env, chatId, renderPublicAck(env), message.message_id);

      const builderName = getBuilderName(message.from);
      const builderId = String(message.from?.id ?? "");
      const dispatched = await dispatchWorkflow(env, parsed.romLink, builderName, builderId);

      if (!dispatched) {
        await sendTelegramMessage(env, chatId, DISPATCH_FAILURE_MESSAGE, message.message_id);
      }

      return new Response("OK", { status: 200 });
    } catch {
      return new Response("OK", { status: 200 });
    }
  },
};

function parseMezoCommand(text) {
  const trimmed = text.trim();
  const match = trimmed.match(/^\/mezo(?:@[\w_]+)?(?:\s+(.+))?$/i);
  if (!match) {
    return { isCommand: false, romLink: null };
  }

  const romLink = match[1]?.trim() ?? "";
  if (!isValidHttpUrl(romLink)) {
    return { isCommand: true, romLink: null };
  }

  return { isCommand: true, romLink };
}

function isValidHttpUrl(value) {
  if (!value) {
    return false;
  }

  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function getBuilderName(from) {
  if (typeof from?.username === "string" && from.username.trim()) {
    return from.username.trim();
  }

  if (typeof from?.first_name === "string" && from.first_name.trim()) {
    return from.first_name.trim();
  }

  return "Telegram User";
}

function renderPublicAck(env) {
  return PUBLIC_ACK_MESSAGE
    .replace("${MEZO_CONTACT_LINK}", env.MEZO_CONTACT_LINK ?? "")
    .replace("${UPDATES_GROUP_LINK}", env.UPDATES_GROUP_LINK ?? "")
    .replace("${SCREENSHOTS_GROUP_LINK}", env.SCREENSHOTS_GROUP_LINK ?? "")
    .replace("${CHAT_GROUP_LINK}", env.CHAT_GROUP_LINK ?? "");
}

async function sendTelegramMessage(env, chatId, text, replyToMessageId) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json; charset=UTF-8" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "Markdown",
      disable_web_page_preview: true,
      ...(replyToMessageId ? { reply_to_message_id: replyToMessageId } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error("telegram_send_failed");
  }
}

async function dispatchWorkflow(env, romLink, builderName, builderId) {
  try {
    const response = await fetch(
      `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW_FILE}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GH_WORKFLOW_TOKEN}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "mezo-lite-telegram-worker",
          "Content-Type": "application/json; charset=UTF-8",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            rom_link: romLink,
            request_source: `telegram:${builderName}:${builderId}`,
          },
        }),
      },
    );

    return response.ok;
  } catch {
    return false;
  }
}
