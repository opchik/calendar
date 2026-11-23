const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const userName = tg?.initDataUnsafe?.user?.first_name;
if (userName) {
  document.getElementById("user-name").textContent = userName;
}

document.getElementById("today-date").textContent = new Date().toLocaleDateString(
  "ru-RU",
  { weekday: "long", day: "numeric", month: "long", year: "numeric" }
);
