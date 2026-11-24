<script>
  import { clearError, errorMessage } from '#lib/stores/app.js';

  let timer;

  $effect(() => {
    if (!$errorMessage) return;
    timer = setTimeout(clearError, 6000);
    return () => clearTimeout(timer);
  });
</script>

{#if $errorMessage}
  <button class="error-banner" type="button" onclick={clearError}>
    {$errorMessage}
  </button>
{/if}
