<script>
  import EventCard from './EventCard.svelte';
  import { groupUpcoming } from '#lib/utils/date.js';

  let { events = [], onopen = () => {}, oncreate = () => {} } = $props();

  const groups = $derived(groupUpcoming(events));
</script>

{#if groups.length}
  <div class="feed">
    {#each groups as group (group.key)}
      <section class="feed__section">
        <div class="section-heading">
          <h2>{group.title}</h2>
          <span>{group.events.length}</span>
        </div>
        <div class="feed__list">
          {#each group.events as event (event.id)}
            <EventCard {event} {onopen} />
          {/each}
        </div>
      </section>
    {/each}
  </div>
{:else}
  <div class="empty-state">
    <div class="empty-state__art">🗓️</div>
    <h2>Пока пусто</h2>
    <p>Создайте первый план — ужин, прогулку, поездку или встречу с друзьями.</p>
    <button class="button button--primary" type="button" onclick={oncreate}>
      Создать событие
    </button>
  </div>
{/if}
