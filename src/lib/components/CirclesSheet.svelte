<script>
  import {
    createCircle,
    deleteCircle,
    showError,
  } from '#lib/stores/app.js';

  let { circles = [], onclose = () => {} } = $props();

  const COLORS = [
    '#ef4444',
    '#3b82f6',
    '#8b5cf6',
    '#f59e0b',
    '#10b981',
    '#ec4899',
    '#06b6d4',
    '#64748b',
  ];

  let name = $state('');
  let color = $state(COLORS[0]);
  let busy = $state(false);

  async function submit(event) {
    event.preventDefault();
    if (!name.trim() || busy) return;

    busy = true;
    try {
      await createCircle({ name: name.trim(), color });
      name = '';
    } catch (error) {
      showError(error.message);
    } finally {
      busy = false;
    }
  }

  async function remove(circle) {
    if (!confirm(`Удалить круг «${circle.name}»? События останутся без круга.`)) return;
    try {
      await deleteCircle(circle.id);
    } catch (error) {
      showError(error.message);
    }
  }
</script>

<div
  class="sheet-backdrop"
  role="presentation"
  onclick={(event) => event.target === event.currentTarget && onclose()}
>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Круги">
    <div class="sheet__handle"></div>
    <header class="sheet__head">
      <div>
        <p class="eyebrow">Организация</p>
        <h2>Круги</h2>
      </div>
      <button class="icon-button" type="button" aria-label="Закрыть" onclick={onclose}>✕</button>
    </header>

    <p class="muted">
      Круги помогают фильтровать планы и управлять приватностью событий.
    </p>

    <div class="circle-list">
      {#each circles as circle (circle.id)}
        <div class="circle-row">
          <i class="chip__dot chip__dot--large" style={`--dot:${circle.color}`}></i>
          <span>{circle.name}</span>
          <button class="icon-button" type="button" aria-label="Удалить" onclick={() => remove(circle)}>🗑</button>
        </div>
      {/each}
    </div>

    <form class="circle-form" onsubmit={submit}>
      <label class="field">
        <span>Новый круг</span>
        <input bind:value={name} maxlength="50" placeholder="Например, Универ" autocomplete="off" />
      </label>
      <div class="color-grid">
        {#each COLORS as option}
          <button
            class="color-dot"
            class:color-dot--active={color === option}
            type="button"
            style={`--color:${option}`}
            aria-label={`Цвет ${option}`}
            onclick={() => (color = option)}
          ></button>
        {/each}
      </div>
      <button class="button button--primary button--wide" type="submit" disabled={busy || !name.trim()}>
        {busy ? 'Создаём…' : 'Добавить круг'}
      </button>
    </form>
  </div>
</div>
