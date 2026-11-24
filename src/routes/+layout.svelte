<script>
  import { onMount } from 'svelte';
  import '../app.css';
  import { bootstrap } from '#lib/stores/app.js';
  import { initTelegram } from '#lib/telegram.js';

  onMount(async () => {
    const tg = await initTelegram();
    await bootstrap(tg);
  });
</script>

<slot />
