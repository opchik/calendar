<script>
  let {
    circles = [],
    selected = [],
    ontoggle = () => {},
    onall = () => {},
    onmanage = () => {},
  } = $props();
</script>

<div class="chips-row">
  <button
    class="chip"
    class:chip--active={selected.length === 0}
    type="button"
    onclick={onall}
  >
    Все
  </button>

  {#each circles as circle (circle.id)}
    <button
      class="chip"
      class:chip--active={selected.includes(circle.id)}
      type="button"
      onclick={() => ontoggle(circle.id)}
    >
      <i class="chip__dot" style={`--dot:${circle.color}`}></i>
      {circle.name}
    </button>
  {/each}

  <button class="chip chip--ghost" type="button" onclick={onmanage}>＋ Круг</button>
</div>
