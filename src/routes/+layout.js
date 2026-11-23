// Приложение рендерится один раз на этапе сборки (prerender), а вся работа
// (Telegram SDK, API) идёт в браузере — SSG + SPA-гидратация.
export const prerender = true;
export const csr = true;
