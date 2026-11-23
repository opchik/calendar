<script>
  import { addTask } from '#lib/stores/tasks.js';
  import { haptic } from '#lib/telegram.js';

  let { onerror = () => {} } = $props();

  let title = $state('');
  let busy = $state(false);

  const submitLabel = $derived(busy ? 'Добавляем…' : 'Добавить');

  async function submit(event) {
    event.preventDefault();
    const value = title.trim();
    if (!value || busy) return;

    busy = true;
    try {
      await addTask(value);
      title = '';
      haptic.light();
    } catch (error) {
      onerror(error.message);
    } finally {
      busy = false;
    }
  }
</script>

<form class="task-form" id="task-form" onsubmit={submit}>
  <input
    class="task-form__input"
    id="task-title"
    bind:value={title}
    maxlength="200"
    placeholder="Что нужно сделать?"
    autocomplete="off"
    enterkeyhint="done"
    required
  />
  <button class="task-form__submit" type="submit" disabled={busy}>{submitLabel}</button>
</form>
