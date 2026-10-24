import { useSyncExternalStore } from 'react';

const query = '(max-width: 639px)';
const getSnapshot = () => typeof window.matchMedia === 'function' && window.matchMedia(query).matches;
function subscribe(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => {};
  const media = window.matchMedia(query);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
