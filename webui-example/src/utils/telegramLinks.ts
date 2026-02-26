/**
 * Build a Telegram deep link for a message.
 *
 * - Public channel/group with username: https://t.me/{username}/{msgId}
 * - Private channel/group (id starts with -100): https://t.me/c/{adjustedId}/{msgId}
 * - Other negative IDs (regular groups): https://t.me/c/{absId}/{msgId}
 *
 * Returns null when required info is missing.
 */
export function getTelegramLink(
    chatId: number | undefined | null,
    msgId: number | undefined | null,
    username?: string | null,
): string | null {
    if (!chatId || !msgId) return null;

    if (username) {
        return `https://t.me/${username}/${msgId}`;
    }

    const abs = Math.abs(chatId);
    // MeiliSearch stores channel IDs as negative -100XXXXXXXXX
    // Strip the -100 prefix: abs(id) - 1_000_000_000_000
    const adjustedId = abs > 1_000_000_000_000 ? abs - 1_000_000_000_000 : abs;
    return `https://t.me/c/${adjustedId}/${msgId}`;
}
