<script>
  let { user = null, size = 36, ring = false } = $props();

  const name = $derived(
    [user?.firstName, user?.lastName].filter(Boolean).join(' ') ||
      user?.username ||
      '?',
  );
  const initials = $derived(
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase(),
  );
  const hue = $derived(
    [...(user?.id || name)].reduce((acc, char) => acc + char.charCodeAt(0), 0) % 360,
  );
</script>

{#if user?.photoUrl}
  <img
    class="avatar"
    class:avatar--ring={ring}
    src={user.photoUrl}
    alt={name}
    width={size}
    height={size}
    style={`--size:${size}px`}
    loading="lazy"
  />
{:else}
  <span
    class="avatar avatar--initials"
    class:avatar--ring={ring}
    style={`--size:${size}px;--hue:${hue}`}
    title={name}
  >
    {initials}
  </span>
{/if}
