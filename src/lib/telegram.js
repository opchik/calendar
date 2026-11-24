const SDK_URL = 'https://telegram.org/js/telegram-web-app.js';
const SDK_TIMEOUT_MS = 3000;
const SDK_POLL_MS = 50;

export const getTelegram = () =>
  typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined;

const isTelegramContext = () =>
  typeof window !== 'undefined' &&
  Boolean(
    window.TelegramWebviewProxy ||
      window.location.hash.includes('tgWebAppData') ||
      window.location.search.includes('tgWebAppData')
  );

const waitForTelegram = (timeout) =>
  new Promise((resolve) => {
    const started = Date.now();
    const check = () => {
      const tg = getTelegram();
      if (tg) return resolve(tg);
      if (Date.now() - started >= timeout) return resolve(undefined);
      setTimeout(check, SDK_POLL_MS);
    };
    check();
  });

/** Скрипт грузится только внутри Telegram, поэтому локальный браузер не ждёт telegram.org. */
function loadSdk() {
  if (typeof document === 'undefined' || getTelegram()) return;
  if (document.querySelector('script[data-telegram-sdk]')) return;

  const script = document.createElement('script');
  script.src = SDK_URL;
  script.async = true;
  script.dataset.telegramSdk = 'true';
  document.head.appendChild(script);
}

export async function initTelegram() {
  let tg = getTelegram();

  if (!tg && isTelegramContext()) {
    loadSdk();
    tg = await waitForTelegram(SDK_TIMEOUT_MS);
  }

  if (!tg) return undefined;

  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('secondary_bg_color');
  tg.setBackgroundColor?.('secondary_bg_color');
  return tg;
}

export function getStartParam() {
  const tg = getTelegram();
  if (tg?.initDataUnsafe?.start_param) return tg.initDataUnsafe.start_param;
  if (typeof window === 'undefined') return null;

  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  return (
    search.get('startapp') ||
    search.get('tgWebAppStartParam') ||
    hash.get('tgWebAppStartParam') ||
    null
  );
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand('copy');
    textarea.remove();
    return ok;
  }
}

export async function shareLink(url, text) {
  const tg = getTelegram();
  if (tg?.openTelegramLink) {
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    tg.openTelegramLink(shareUrl);
    return 'telegram';
  }

  if (navigator.share) {
    await navigator.share({ title: text, url });
    return 'native';
  }

  await copyText(url);
  return 'copied';
}

export const haptic = {
  light: () => getTelegram()?.HapticFeedback?.impactOccurred('light'),
  success: () => getTelegram()?.HapticFeedback?.notificationOccurred?.('success'),
  selection: () => getTelegram()?.HapticFeedback?.selectionChanged?.(),
};
