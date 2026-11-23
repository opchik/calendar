import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

/**
 * SvelteKit 3: конфигурация передаётся в Vite-плагин (svelte.config.js больше не нужен).
 *
 * Сборка — в чистую статику (static/): приложение одноэкранное и работает
 * в браузере Telegram, поэтому server/ просто раздаёт эти файлы.
 * prerender нужен, чтобы в index.html попал стартовый HTML и загрузился клиент;
 * router.resolution: 'client' — SvelteKit не ходит на сервер за маршрутами.
 */
export default defineConfig({
  plugins: [
    sveltekit({
      adapter: adapter({
        pages: 'static',
        assets: 'static',
        fallback: 'index.html',
        strict: false,
      }),
      paths: { relative: false },
      router: { resolution: 'client' },
      prerender: { entries: ['*'] },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3000',
    },
  },
});
