<script>
  import TaskItem from './TaskItem.svelte';
  import { removeTask, toggleTask } from '#lib/stores/tasks.js';
  import { haptic } from '#lib/telegram.js';

  let { tasks, onerror = () => {} } = $props();

  async function toggle(id) {
    try {
      await toggleTask(id);
      haptic.selection();
    } catch (error) {
      onerror(error.message);
    }
  }

  async function remove(id) {
    try {
      await removeTask(id);
    } catch (error) {
      onerror(error.message);
    }
  }
</script>

{#if tasks.length}
  <ul class="tasks" id="task-list">
    {#each tasks as task (task.id)}
      <TaskItem {task} ontoggle={toggle} onremove={remove} />
    {/each}
  </ul>
{:else}
  <p class="empty">Пока пусто. Добавьте первую задачу.</p>
{/if}
