export interface NavItem {
  key: 'dashboard' | 'search' | 'settings';
  to: string;
  icon: string;
  labelKey: string;
  matchPrefixes: string[];
}

export const NAV_ITEMS: NavItem[] = [
  {
    key: 'dashboard',
    to: '/dashboard',
    icon: 'forum',
    labelKey: 'nav.chats',
    matchPrefixes: ['/dashboard', '/synced-chats', '/select-chats'],
  },
  {
    key: 'search',
    to: '/search',
    icon: 'search',
    labelKey: 'nav.search',
    matchPrefixes: ['/search'],
  },
  {
    key: 'settings',
    to: '/settings',
    icon: 'settings',
    labelKey: 'nav.settings',
    matchPrefixes: ['/settings', '/storage', '/ai-config'],
  },
];

export function isNavItemActive(pathname: string, item: NavItem): boolean {
  return item.matchPrefixes.some((prefix) => pathname.startsWith(prefix));
}
