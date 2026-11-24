<script>
  import Avatar from './Avatar.svelte';
  import { coverStyle } from '#lib/utils/covers.js';
  import {
    formatMonthShort,
    formatTime,
    formatWeekday,
    participantsLabel,
    STATUS_LABELS,
  } from '#lib/utils/date.js';

  let { event, onopen = () => {} } = $props();

  const date = $derived(new Date(event.startsAt));
  const participants = $derived(event.participants?.slice(0, 4) ?? []);
</script>

<button class="event-card" type="button" onclick={() => onopen(event)}>
  <div class="event-card__cover" style={coverStyle(event.cover)}>
    <span class="event-card__date">
      <strong>{date.getDate()}</strong>
      <span>{formatMonthShort(date)}</span>
    </span>
    {#if event.circle}
      <span class="event-card__circle" style={`--circle:${event.circle.color}`}>
        {event.circle.name}
      </span>
    {/if}
    {#if event.myStatus && event.myStatus !== 'going'}
      <span class="event-card__status">{STATUS_LABELS[event.myStatus]}</span>
    {/if}
  </div>

  <div class="event-card__body">
    <p class="event-card__meta">
      {formatWeekday(date)} · {formatTime(date)}
    </p>
    <h3 class="event-card__title">{event.title}</h3>
    {#if event.locationText || event.locationUrl}
      <p class="event-card__location">📍 {event.locationText || event.locationUrl}</p>
    {/if}

    <div class="event-card__footer">
      <div class="avatar-stack">
        {#each participants as participant (participant.user.id)}
          <Avatar user={participant.user} size={26} />
        {/each}
      </div>
      <span class="event-card__people">
        {participantsLabel(event.participants?.length ?? 0)}
        · {event.commentCount} 💬
      </span>
    </div>
  </div>
</button>
