const INVALID_USAGE_MESSAGE = "⚠️ <b>Usage:</b>\n<code>/mezo &lt;ROM_LINK&gt;</code>\n\nPlease send a valid ROM download link.";
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
        await sendTelegramMessage(env, chatId, INVALID_USAGE_MESSAGE, message.message_id, "HTML");
        return new Response("OK", { status: 200 });
      }

      await sendTelegramMessage(env, chatId, renderPublicAckHtml(env), message.message_id, "HTML");

      const builderName = getBuilderName(message.from);
      const builderId = String(message.from?.id ?? "");
      const dispatched = await dispatchWorkflow(env, parsed.romLink, builderName, builderId);

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

function renderPublicAckHtml(env) {
  const mezoContactLink = toSafeTelegramLink(env.MEZO_CONTACT_LINK);
  const updatesGroupLink = toSafeTelegramLink(env.UPDATES_GROUP_LINK);
  const screenshotsGroupLink = toSafeTelegramLink(env.SCREENSHOTS_GROUP_LINK);
  const chatGroupLink = toSafeTelegramLink(env.CHAT_GROUP_LINK);

  return (
    `✅ <b>ROM Link Received Successfully</b>\n\n` +
    `📨 Your ROM link has been sent to <b>MEZO</b> for processing.\n\n` +
    `⏳ <b>Estimated build time:</b> 40–60 minutes\n` +
    `Please wait until the process is completed.\n\n` +
    `━━━━━━━━━━━━━━\n\n` +
    `🚀 <b>DeadZone Lite</b> is now being prepared for you.\n\n` +
    `✨ Looking for something more powerful?\n\n` +
    `🎮 <b>DeadZone GamingPlus</b>\n` +
    `👑 <b>DeadZone Legend</b>\n` +
    `⚔️ <b>DeadZone Ninja</b>\n\n` +
    `⚡ These premium systems include more advanced features, stronger optimization, and a more exclusive experience.\n\n` +
    `💎 <b>Premium ROMs are paid systems.</b>\n` +
    `For details, contact <a href="${mezoContactLink}">MEZO</a>.\n\n` +
    `━━━━━━━━━━━━━━\n\n` +
    `📢 <a href="${updatesGroupLink}">Updates Channel</a>\n\n` +
    `🖼️ <a href="${screenshotsGroupLink}">Screenshots Channel</a>\n\n` +
    `💬 <a href="${chatGroupLink}">Community Chat</a>\n\n` +
    `✨ Thank you for choosing <b>DeadZone</b>.`
  );
}

function toSafeTelegramLink(value) {
  try {
    const parsed = new URL(value ?? "");
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return escapeHtmlAttribute(parsed.toString());
    }
  } catch {
    return "#";
  }
  return "#";
}

function escapeHtmlAttribute(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
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
