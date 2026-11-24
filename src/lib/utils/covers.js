export const COVERS = [
  { id: 'preset:sunset', label: 'Закат', background: 'linear-gradient(135deg,#ff9966,#ff5e62 55%,#8e2de2)' },
  { id: 'preset:ocean', label: 'Океан', background: 'linear-gradient(135deg,#2193b0,#6dd5ed)' },
  { id: 'preset:forest', label: 'Лес', background: 'linear-gradient(135deg,#134e5e,#71b280)' },
  { id: 'preset:night', label: 'Ночь', background: 'linear-gradient(135deg,#141e30,#243b55 60%,#4b6cb7)' },
  { id: 'preset:peach', label: 'Персик', background: 'linear-gradient(135deg,#ffecd2,#fcb69f)' },
  { id: 'preset:lavender', label: 'Лаванда', background: 'linear-gradient(135deg,#a18cd1,#fbc2eb)' },
  { id: 'preset:mint', label: 'Мята', background: 'linear-gradient(135deg,#43e97b,#38f9d7)' },
  { id: 'preset:citrus', label: 'Цитрус', background: 'linear-gradient(135deg,#f7971e,#ffd200)' },
];

const presetMap = new Map(COVERS.map((cover) => [cover.id, cover]));

export function coverStyle(cover) {
  if (!cover) return { background: COVERS[0].background };

  const preset = presetMap.get(cover);
  if (preset) return { background: preset.background };

  if (cover.startsWith('/uploads/') || cover.startsWith('http://') || cover.startsWith('https://')) {
    return {
      backgroundImage: `linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.35)), url("${cover}")`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    };
  }

  return { background: COVERS[0].background };
}

export function coverPreviewStyle(cover) {
  return coverStyle(cover);
}
