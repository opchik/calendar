<script>
  import { api } from '#lib/api.js';
  import { COVERS, coverStyle } from '#lib/utils/covers.js';
  import { defaultEventDate, fromDatetimeLocal } from '#lib/utils/date.js';
  import { showToast } from '#lib/stores/app.js';

  let { circles = [], onclose = () => {}, oncreated = async () => {} } = $props();

  let title = $state('');
  let startsAt = $state(defaultEventDate());
  let location = $state('');
  let description = $state('');
  let privacy = $state('link');
  let circleId = $state('');
  let cover = $state(COVERS[0].id);
  let busy = $state(false);
  let uploading = $state(false);
  let error = $state('');

  let fileInput;

  $effect(() => {
    if (!circleId && circles.length) circleId = circles[0].id;
  });

  const selectedCover = $derived(coverStyle(cover));

  async function upload(event) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      error = 'Выберите изображение';
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      error = 'Максимальный размер обложки — 5 МБ';
      return;
    }

    uploading = true;
    error = '';
    try {
      const result = await api.uploadCover(file);
      cover = result.url;
      showToast('Обложка загружена');
    } catch (uploadError) {
      error = uploadError.message;
    } finally {
      uploading = false;
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (busy) return;

    if (!title.trim()) {
      error = 'Придумайте название события';
      return;
    }
    if (privacy === 'circle' && !circleId) {
      error = 'Для приватности «Для круга» выберите круг';
      return;
    }

    busy = true;
    error = '';

    const payload = {
      title: title.trim(),
      startsAt: fromDatetimeLocal(startsAt),
      description: description.trim() || null,
      cover,
      privacy,
      circleId: circleId || null,
    };

    const place = location.trim();
    if (place) {
      if (/^https?:\/\//i.test(place)) payload.locationUrl = place;
      else payload.locationText = place;
    }

    try {
      const created = await oncreated(payload);
      if (created) onclose();
    } catch (submitError) {
      error = submitError.message;
    } finally {
      busy = false;
    }
  }
</script>

<div
  class="sheet-backdrop"
  role="presentation"
  onclick={(event) => event.target === event.currentTarget && onclose()}
>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Новое событие">
    <div class="sheet__handle"></div>
    <header class="sheet__head">
      <div>
        <p class="eyebrow">Новый план</p>
        <h2>Что за событие?</h2>
      </div>
      <button class="icon-button" type="button" aria-label="Закрыть" onclick={onclose}>✕</button>
    </header>

    <form class="sheet__form" onsubmit={submit}>
      <div class="cover-preview" style={selectedCover}>
        <span>{title.trim() || 'Ваша обложка'}</span>
      </div>

      <label class="field">
        <span>Название</span>
        <input
          bind:value={title}
          maxlength="120"
          placeholder="Ужин с друзьями"
          autocomplete="off"
          required
        />
      </label>

      <div class="field-row">
        <label class="field">
          <span>Когда</span>
          <input type="datetime-local" bind:value={startsAt} required />
        </label>
        <label class="field">
          <span>Локация</span>
          <input
            bind:value={location}
            maxlength="500"
            placeholder="Кафе или ссылка"
            autocomplete="off"
          />
        </label>
      </div>

      <label class="field">
        <span>Детали <em>необязательно</em></span>
        <textarea
          bind:value={description}
          rows="2"
          maxlength="4000"
          placeholder="Что взять, где встретимся, что обсудить"
        ></textarea>
      </label>

      <div class="field">
        <span>Круг</span>
        <div class="chips-row chips-row--wrap">
          {#each circles as circle (circle.id)}
            <button
              class="chip"
              class:chip--active={circleId === circle.id}
              type="button"
              onclick={() => (circleId = circle.id)}
            >
              <i class="chip__dot" style={`--dot:${circle.color}`}></i>
              {circle.name}
            </button>
          {/each}
        </div>
      </div>

      <div class="field">
        <span>Приватность</span>
        <div class="segmented segmented--small">
          <button
            type="button"
            class:segmented__item--active={privacy === 'private'}
            class="segmented__item"
            onclick={() => (privacy = 'private')}
          >Только я</button>
          <button
            type="button"
            class:segmented__item--active={privacy === 'link'}
            class="segmented__item"
            onclick={() => (privacy = 'link')}
          >По ссылке</button>
          <button
            type="button"
            class:segmented__item--active={privacy === 'circle'}
            class="segmented__item"
            onclick={() => (privacy = 'circle')}
          >Для круга</button>
        </div>
      </div>

      <div class="field">
        <span>Обложка</span>
        <div class="cover-grid">
          {#each COVERS as preset (preset.id)}
            <button
              class="cover-swatch"
              class:cover-swatch--active={cover === preset.id}
              type="button"
              style={`background:${preset.background}`}
              title={preset.label}
              aria-label={preset.label}
              onclick={() => (cover = preset.id)}
            ></button>
          {/each}
          <button
            class="cover-swatch cover-swatch--upload"
            type="button"
            onclick={() => fileInput?.click()}
            title="Загрузить свою картинку"
          >
            {uploading ? '…' : '＋'}
          </button>
        </div>
        <input
          bind:this={fileInput}
          class="visually-hidden"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onchange={upload}
        />
      </div>

      {#if error}
        <p class="form-error">{error}</p>
      {/if}

      <button class="button button--primary button--wide" type="submit" disabled={busy}>
        {busy ? 'Создаём…' : 'Создать событие'}
      </button>
      <button class="button button--ghost button--wide" type="button" onclick={onclose}>
        Отмена
      </button>
    </form>
  </div>
</div>
