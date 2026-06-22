const INVALID_USAGE_MESSAGE = "<b>Usage:</b>\n<code>/dz &lt;ROM_LINK&gt;</code>\n\nPlease send a valid ROM download link.";
const DISPATCH_FAILURE_MESSAGE = "Build request could not be submitted. Please contact MEZO.";
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
        await sendTelegramMessage(env, chatId, INVALID_USAGE_MESSAGE, message.message_id, "HTML");
        return new Response("OK", { status: 200 });
      }

      await sendTelegramMessage(env, chatId, renderPublicAckHtml(), message.message_id, "HTML");

      const dispatched = await dispatchWorkflow(env, parsed.romLink);
      if (!dispatched) {
        await sendTelegramMessage(env, chatId, DISPATCH_FAILURE_MESSAGE, message.message_id, "HTML");
      }

      return new Response("OK", { status: 200 });
    } catch {
      return new Response("OK", { status: 200 });
    }
  },
};

function parseMezoCommand(text) {
  const trimmed = text.trim();
  const match = trimmed.match(/^\/(?:mezo|dz)(?:@[\w_]+)?(?:\s+(.+))?$/i);
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

function renderPublicAckHtml() {
  return (
    "<b>DeadZone Lite build queued.</b>\n\n" +
    "Your ROM link was received and sent for processing.\n" +
    "Estimated build time: 40-60 minutes.\n" +
    "If another build is running, your request will wait safely in queue."
  );
}

async function sendTelegramMessage(env, chatId, text, replyToMessageId, parseMode = "HTML") {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json; charset=UTF-8" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: parseMode,
      disable_web_page_preview: true,
      ...(replyToMessageId ? { reply_to_message_id: replyToMessageId } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error("telegram_send_failed");
  }
}

async function dispatchWorkflow(env, romLink) {
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
            request_source: "telegram",
            publish_release: "true",
          },
        }),
      },
    );

    return response.ok;
  } catch {
    return false;
  }
}
