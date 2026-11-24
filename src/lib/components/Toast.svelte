<script>
  import { toastMessage } from '#lib/stores/app.js';
</script>

{#if $toastMessage}
  <div class="toast">{$toastMessage}</div>
{/if}
