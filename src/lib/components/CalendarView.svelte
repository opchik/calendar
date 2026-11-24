<script>
  import EventCard from './EventCard.svelte';
  import {
    buildMonthCells,
    dayKey,
    eventsByDay,
    formatDayTitle,
    isSameDay,
  } from '#lib/utils/date.js';

  let { events = [], onopen = () => {} } = $props();

  const today = new Date();
  let cursor = $state(new Date(today.getFullYear(), today.getMonth(), 1));
  let selected = $state(today);
  let pickerOpen = $state(false);
  let pickerYear = $state(today.getFullYear());

  const MONTHS = [
    'Январь',
    'Февраль',
    'Март',
    'Апрель',
    'Май',
    'Июнь',
    'Июль',
    'Август',
    'Сентябрь',
    'Октябрь',
    'Ноябрь',
    'Декабрь',
  ];
  const weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  const cells = $derived(buildMonthCells(cursor.getFullYear(), cursor.getMonth()));
  const map = $derived(eventsByDay(events));
  const selectedEvents = $derived(map.get(dayKey(selected)) ?? []);
  const monthLabel = $derived(
    new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })
      .format(cursor)
      .replace(/^./, (char) => char.toUpperCase()),
  );

  function moveMonth(delta) {
    const next = new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1);
    cursor = next;
    selected = new Date(next.getFullYear(), next.getMonth(), 1);
    pickerOpen = false;
  }

  function openPicker() {
    pickerYear = cursor.getFullYear();
    pickerOpen = !pickerOpen;
  }

  function selectMonth(index) {
    const now = new Date();
    const year = Math.min(
      2100,
      Math.max(2000, Number(pickerYear) || cursor.getFullYear()),
    );
    const next = new Date(year, index, 1);
    cursor = next;
    selected =
      now.getFullYear() === year && now.getMonth() === index ? now : next;
    pickerOpen = false;
  }

  function goToday() {
    const now = new Date();
    cursor = new Date(now.getFullYear(), now.getMonth(), 1);
    selected = now;
    pickerYear = now.getFullYear();
    pickerOpen = false;
  }
</script>

<div class="calendar">
  <div class="calendar__head">
    <button class="icon-button" type="button" aria-label="Предыдущий месяц" onclick={() => moveMonth(-1)}>‹</button>
    <button
      class="calendar__month"
      type="button"
      aria-expanded={pickerOpen}
      onclick={openPicker}
    >
      {monthLabel}
      <span class="calendar__month-arrow" class:calendar__month-arrow--open={pickerOpen}>▾</span>
    </button>
    <button class="icon-button" type="button" aria-label="Следующий месяц" onclick={() => moveMonth(1)}>›</button>
  </div>

  {#if pickerOpen}
    <div class="calendar__picker">
      <div class="calendar__picker-head">
        <button class="icon-button" type="button" aria-label="Год назад" onclick={() => (pickerYear -= 1)}>‹</button>
        <label class="calendar__year">
          <span>Год</span>
          <input type="number" min="2000" max="2100" bind:value={pickerYear} />
        </label>
        <button class="icon-button" type="button" aria-label="Год вперёд" onclick={() => (pickerYear += 1)}>›</button>
      </div>
      <div class="month-grid">
        {#each MONTHS as month, index}
          <button
            class="month-cell"
            class:month-cell--active={cursor.getFullYear() === pickerYear && cursor.getMonth() === index}
            type="button"
            onclick={() => selectMonth(index)}
          >
            {month}
          </button>
        {/each}
      </div>
      <button class="button button--ghost button--wide" type="button" onclick={goToday}>
        Перейти к сегодня
      </button>
    </div>
  {/if}

  <div class="calendar__weekdays">
    {#each weekdays as weekday}
      <span>{weekday}</span>
    {/each}
  </div>

  <div class="calendar__grid">
    {#each cells as cell}
      {#if cell}
        {@const dayEvents = map.get(dayKey(cell)) ?? []}
        <button
          class="calendar__day"
          class:calendar__day--selected={isSameDay(cell, selected)}
          class:calendar__day--today={isSameDay(cell, today)}
          type="button"
          onclick={() => (selected = cell)}
        >
          <span>{cell.getDate()}</span>
          <span class="calendar__dots">
            {#each dayEvents.slice(0, 3) as event (event.id)}
              <i style={`--dot:${event.circle?.color || 'var(--accent)'}`}></i>
            {/each}
          </span>
        </button>
      {:else}
        <span class="calendar__day calendar__day--empty"></span>
      {/if}
    {/each}
  </div>

  <div class="calendar__selected">
    <div class="section-heading">
      <h2>{formatDayTitle(selected)}</h2>
      <span>{selectedEvents.length}</span>
    </div>
    {#if selectedEvents.length}
      <div class="feed__list">
        {#each selectedEvents as event (event.id)}
          <EventCard {event} {onopen} />
        {/each}
      </div>
    {:else}
      <p class="muted">На этот день планов нет. Самое время что-нибудь придумать.</p>
    {/if}
  </div>
</div>
