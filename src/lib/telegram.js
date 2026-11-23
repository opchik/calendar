/** Тонкая обёртка над window.Telegram.WebApp (скрипт подключается в app.html). */
export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined;

export function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('secondary_bg_color');
  tg.setBackgroundColor?.('secondary_bg_color');
}

export const haptic = {
  light: () => tg?.HapticFeedback?.impactOccurred('light'),
  selection: () => tg?.HapticFeedback?.selectionChanged?.(),
};
