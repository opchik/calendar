<script>
  import { errorMessage, clearError } from '#lib/stores/tasks.js';

  let timer;

  // Ошибка висит 6 секунд и закрывается нажатием.
  $effect(() => {
    if (!$errorMessage) return;
    timer = setTimeout(clearError, 6000);
    return () => clearTimeout(timer);
  });
</script>

{#if $errorMessage}
  <button class="app__error" type="button" onclick={clearError}>{$errorMessage}</button>
{/if}
