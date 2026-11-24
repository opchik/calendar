<script>
  import Avatar from '#lib/components/Avatar.svelte';
  import CalendarView from '#lib/components/CalendarView.svelte';
  import CircleFilters from '#lib/components/CircleFilters.svelte';
  import CirclesSheet from '#lib/components/CirclesSheet.svelte';
  import CreateEventSheet from '#lib/components/CreateEventSheet.svelte';
  import ErrorBanner from '#lib/components/ErrorBanner.svelte';
  import EventDetailSheet from '#lib/components/EventDetailSheet.svelte';
  import FeedView from '#lib/components/FeedView.svelte';
  import LoginScreen from '#lib/components/LoginScreen.svelte';
  import Toast from '#lib/components/Toast.svelte';
  import {
    activeEvent,
    appConfig,
    circles,
    clearCircleFilter,
    createEvent,
    events,
    filterEvents,
    loading,
    openEvent,
    selectedCircleIds,
    showError,
    showToast,
    toggleCircle,
    user,
    view,
  } from '#lib/stores/app.js';

  let showCreate = $state(false);
  let showCircles = $state(false);

  const name = $derived($user?.firstName || $user?.username || 'друг');
  const filtered = $derived(filterEvents($events, $selectedCircleIds));

  async function handleOpen(event) {
    try {
      await openEvent(event.id);
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleCreate(payload) {
    const created = await createEvent(payload);
    showToast('Событие создано');
    activeEvent.set(created);
    return created;
  }
</script>

<ErrorBanner />
<Toast />

{#if $loading}
  <div class="splash">
    <div class="splash__logo">п</div>
    <p>Собираем ваши планы…</p>
  </div>
{:else if !$user}
  <LoginScreen config={$appConfig} />
{:else}
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Социальный календарь</p>
        <h1>Привет, {name}</h1>
      </div>
      <button class="avatar-button" type="button" aria-label="Круги" onclick={() => (showCircles = true)}>
        <Avatar user={$user} size={42} ring />
      </button>
    </header>

    <div class="segmented">
      <button
        class="segmented__item"
        class:segmented__item--active={$view === 'feed'}
        type="button"
        onclick={() => view.set('feed')}
      >
        Лента
      </button>
      <button
        class="segmented__item"
        class:segmented__item--active={$view === 'calendar'}
        type="button"
        onclick={() => view.set('calendar')}
      >
        Календарь
      </button>
    </div>

    <CircleFilters
      circles={$circles}
      selected={$selectedCircleIds}
      ontoggle={toggleCircle}
      onall={clearCircleFilter}
      onmanage={() => (showCircles = true)}
    />

    {#if $view === 'feed'}
      <FeedView events={filtered} onopen={handleOpen} oncreate={() => (showCreate = true)} />
    {:else}
      <CalendarView events={filtered} onopen={handleOpen} />
    {/if}

    <button class="fab" type="button" aria-label="Создать событие" onclick={() => (showCreate = true)}>
      ＋
    </button>
  </main>
{/if}

{#if showCreate}
  <CreateEventSheet
    circles={$circles}
    onclose={() => (showCreate = false)}
    oncreated={handleCreate}
  />
{/if}

{#if showCircles}
  <CirclesSheet circles={$circles} onclose={() => (showCircles = false)} />
{/if}

{#if $activeEvent}
  <EventDetailSheet event={$activeEvent} onclose={() => activeEvent.set(null)} />
{/if}
