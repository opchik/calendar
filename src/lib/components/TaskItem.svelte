<script>
  let { task, ontoggle, onremove } = $props();
</script>

<li class="task" class:task--done={task.done}>
  <button
    class="task__toggle"
    aria-label={task.done ? 'Вернуть' : 'Выполнить'}
    aria-pressed={task.done}
    onclick={() => ontoggle(task.id)}
  >
    {task.done ? '✓' : ''}
  </button>
  <span class="task__title">{task.title}</span>
  <button class="task__delete" aria-label="Удалить" onclick={() => onremove(task.id)}>✕</button>
</li>
