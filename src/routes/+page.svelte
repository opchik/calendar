<script>
  import { page } from '$app/state';
  import ErrorBanner from '#lib/components/ErrorBanner.svelte';
  import LoginScreen from '#lib/components/LoginScreen.svelte';
  import TaskForm from '#lib/components/TaskForm.svelte';
  import TaskList from '#lib/components/TaskList.svelte';
  import { appConfig, errorMessage, tasks, user } from '#lib/stores/tasks.js';

  // Приложение открывается по адресу, указанному в BotFather
  // (например https://host/tasks-app-bot), поэтому «не корень» — тоже наш экран.
  const isDev = $derived(page.url.pathname !== '/');
  const miniAppLink = $derived(
    $appConfig.botUsername && $appConfig.appShortName
      ? `https://t.me/${$appConfig.botUsername}/${$appConfig.appShortName}`
      : null
  );

  const showError = (message) => errorMessage.set(message);
</script>

<ErrorBanner />

<main class="app">
  <header class="app__header">
    <h1 class="app__title">
      {#if $user}
        Привет, <span>{$user.firstName || 'друг'}</span>!
      {:else}
        Календарь задач
      {/if}
    </h1>
    <p class="app__subtitle">
      {#if isDev && $appConfig.dev}
        Режим разработки — без Telegram
      {:else}
        Добро пожаловать в ваш календарь
      {/if}
    </p>
  </header>

  <section class="app__content">
    {#if $user}
      <TaskForm onerror={showError} />
      <TaskList tasks={$tasks} onerror={showError} />
    {:else}
      <LoginScreen link={miniAppLink} botUsername={$appConfig.botUsername} />
    {/if}
  </section>
</main>
