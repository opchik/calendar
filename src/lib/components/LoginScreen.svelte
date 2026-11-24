<script>
  let { config = {} } = $props();

  const telegramLink = $derived(
    config.botUsername && config.appShortName
      ? `https://t.me/${config.botUsername}/${config.appShortName}`
      : config.botUsername
        ? `https://t.me/${config.botUsername}`
        : null,
  );

  function keycloakLoginUrl() {
    const next =
      typeof window !== 'undefined'
        ? `${window.location.pathname}${window.location.search}`
        : '/';
    return `/api/v1/auth/keycloak/login?next=${encodeURIComponent(next)}`;
  }
</script>

<div class="login-screen">
  <div class="login-screen__art">
    <span>🗓️</span>
    <span>💬</span>
    <span>✨</span>
  </div>

  <h1>Планы, которые не теряются</h1>
  <p>
    Создавайте события, зовите друзей одной ссылкой, собирайте ответы
    «Иду / Думаю / Не смогу» и обсуждайте детали прямо в карточке.
  </p>

  <div class="login-screen__actions">
    {#if config.keycloakEnabled}
      <a class="button button--primary button--wide" href={keycloakLoginUrl()}>
        Войти через email
      </a>
    {/if}

    {#if telegramLink}
      <a class="button button--wide" href={telegramLink}>
        Открыть в Telegram
      </a>
    {/if}

    {#if !config.keycloakEnabled && !telegramLink}
      <p class="muted">Вход не настроен: включите вход по email или откройте приложение через Telegram-бота.</p>
    {/if}
  </div>

  {#if config.dev}
    <p class="login-screen__hint">
      Dev-режим: бэкенд запущен с <code>DEV_BYPASS_AUTH=true</code>.
    </p>
  {/if}
</div>
