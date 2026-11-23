<script>
  let { link = null, botUsername = null } = $props();
</script>

<div class="card">
  <p>
    Задачи хранятся отдельно для каждого пользователя Telegram, поэтому приложение нужно
    открыть внутри Telegram.
  </p>
  {#if link}
    <a class="button" href={link}>Открыть в Telegram</a>
  {:else if botUsername}
    <a class="button" href={`https://t.me/${botUsername}`}>Открыть бота @{botUsername}</a>
  {:else}
    <p class="hint">Откройте приложение через бота в Telegram.</p>
  {/if}
</div>
