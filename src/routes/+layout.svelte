<script>
  import { onMount } from 'svelte';
  import '../app.css';
  import { start } from '#lib/stores/tasks.js';
  import { initTelegram, tg } from '#lib/telegram.js';

  onMount(() => {
    initTelegram();
    start(tg);
  });
</script>

<slot />
