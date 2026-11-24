<script>
  import Avatar from './Avatar.svelte';
  import { api } from '#lib/api.js';
  import { coverStyle } from '#lib/utils/covers.js';
  import {
    formatFullDate,
    relativeLabel,
    STATUS_LABELS,
  } from '#lib/utils/date.js';
  import {
    deleteEvent,
    rsvp,
    showError,
    showToast,
  } from '#lib/stores/app.js';
  import { haptic, shareLink } from '#lib/telegram.js';

  let { event, onclose = () => {} } = $props();

  let comments = $state([]);
  let commentsLoading = $state(false);
  let commentText = $state('');
  let sending = $state(false);
  let busy = $state(false);
  let error = $state('');

  const going = $derived(event.participants.filter((item) => item.status === 'going'));
  const shareUrl = $derived(
    event.shareUrl || `${location.origin}?startapp=event_${event.id}`,
  );
  const privacyLabel = $derived(
    event.privacy === 'private'
      ? 'Только для меня'
      : event.privacy === 'circle'
        ? `Для круга «${event.circle?.name || 'без названия'}»`
        : 'По ссылке',
  );

  $effect(() => {
    const id = event?.id;
    if (!id) return;

    let cancelled = false;
    commentsLoading = true;
    api
      .comments(id)
      .then((data) => {
        if (!cancelled) comments = data.comments;
      })
      .catch((loadError) => {
        if (!cancelled) error = loadError.message;
      })
      .finally(() => {
        if (!cancelled) commentsLoading = false;
      });

    return () => {
      cancelled = true;
    };
  });

  async function setStatus(status) {
    if (busy) return;
    busy = true;
    error = '';
    try {
      await rsvp(event.id, status);
      haptic.success();
    } catch (statusError) {
      error = statusError.message;
    } finally {
      busy = false;
    }
  }

  async function share() {
    try {
      const result = await shareLink(
        shareUrl,
        `Присоединяйся: ${event.title}`,
      );
      if (result === 'copied') showToast('Ссылка скопирована');
    } catch {
      showToast('Не удалось поделиться');
    }
  }

  async function submitComment(submitEvent) {
    submitEvent.preventDefault();
    const text = commentText.trim();
    if (!text || sending) return;

    sending = true;
    error = '';
    try {
      const comment = await api.addComment(event.id, text);
      comments = [...comments, comment];
      commentText = '';
      haptic.light();
    } catch (commentError) {
      error = commentError.message;
    } finally {
      sending = false;
    }
  }

  async function remove() {
    if (!confirm('Удалить событие для всех участников?')) return;
    try {
      await deleteEvent(event.id);
      onclose();
    } catch (removeError) {
      showError(removeError.message);
    }
  }
</script>

<div
  class="sheet-backdrop"
  role="presentation"
  onclick={(clickEvent) => clickEvent.target === clickEvent.currentTarget && onclose()}
>
  <div class="sheet sheet--detail" role="dialog" aria-modal="true" aria-label={event.title}>
    <div class="detail-cover" style={coverStyle(event.cover)}>
      <button class="detail-cover__close" type="button" aria-label="Закрыть" onclick={onclose}>✕</button>
      {#if event.circle}
        <span class="detail-cover__circle" style={`--circle:${event.circle.color}`}>
          {event.circle.name}
        </span>
      {/if}
    </div>

    <div class="detail-body">
      <p class="eyebrow">{formatFullDate(event.startsAt)} · {relativeLabel(event.startsAt)}</p>
      <h1>{event.title}</h1>

      {#if event.locationText || event.locationUrl}
        <p class="detail-location">
          📍
          {#if event.locationUrl}
            <a href={event.locationUrl} target="_blank" rel="noreferrer">
              {event.locationText || event.locationUrl}
            </a>
          {:else}
            {event.locationText}
          {/if}
        </p>
      {/if}

      {#if event.description}
        <p class="detail-description">{event.description}</p>
      {/if}

      <div class="detail-meta">
        <span>{privacyLabel}</span>
        <span>·</span>
        <span>Организатор: {event.owner.firstName || event.owner.username || '—'}</span>
      </div>

      {#if event.isOwner}
        <div class="owner-badge">Вы организатор</div>
      {:else}
        <div class="rsvp-row">
          {#each ['going', 'maybe', 'declined'] as status}
            <button
              class="rsvp-button"
              class:rsvp-button--active={event.myStatus === status}
              class:rsvp-button--going={status === 'going'}
              class:rsvp-button--maybe={status === 'maybe'}
              class:rsvp-button--declined={status === 'declined'}
              type="button"
              disabled={busy}
              onclick={() => setStatus(status)}
            >
              {STATUS_LABELS[status]}
            </button>
          {/each}
        </div>
      {/if}

      <button class="button button--primary button--wide" type="button" onclick={share}>
        Поделиться ссылкой
      </button>

      <section class="detail-section">
        <div class="section-heading">
          <h2>Участники</h2>
          <span>{going.length} идут</span>
        </div>
        <div class="participants">
          {#each event.participants as participant (participant.user.id)}
            <div class="participant">
              <Avatar user={participant.user} size={34} />
              <span>{participant.user.firstName || participant.user.username || 'Гость'}</span>
              <small class:participant__going={participant.status === 'going'}>
                {participant.role === 'owner' ? 'организатор' : STATUS_LABELS[participant.status]}
              </small>
            </div>
          {/each}
        </div>
      </section>

      <section class="detail-section">
        <div class="section-heading">
          <h2>Обсуждение</h2>
          <span>{comments.length}</span>
        </div>

        {#if commentsLoading}
          <p class="muted">Загружаем комментарии…</p>
        {:else if comments.length}
          <div class="comments">
            {#each comments as comment (comment.id)}
              <div class="comment">
                <Avatar user={comment.user} size={30} />
                <div>
                  <strong>{comment.user.firstName || comment.user.username || 'Гость'}</strong>
                  <p>{comment.text}</p>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <p class="muted">Пока тихо. Напишите первым.</p>
        {/if}

        <form class="comment-form" onsubmit={submitComment}>
          <input
            bind:value={commentText}
            maxlength="1000"
            placeholder="Написать комментарий…"
            autocomplete="off"
          />
          <button class="button button--primary" type="submit" disabled={sending || !commentText.trim()}>
            {sending ? '…' : '→'}
          </button>
        </form>
      </section>

      {#if error}
        <p class="form-error">{error}</p>
      {/if}

      {#if event.isOwner}
        <button class="button button--danger button--wide" type="button" onclick={remove}>
          Удалить событие
        </button>
      {/if}
    </div>
  </div>
</div>
