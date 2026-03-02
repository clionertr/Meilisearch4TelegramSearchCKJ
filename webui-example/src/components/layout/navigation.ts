export interface NavItem {
  key: 'dashboard' | 'search' | 'sync' | 'settings';
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
    matchPrefixes: ['/dashboard'],
  },
  {
    key: 'search',
    to: '/search',
    icon: 'search',
    labelKey: 'nav.search',
    matchPrefixes: ['/search'],
  },
  {
    key: 'sync',
    to: '/sync',
    icon: 'sync',
    labelKey: 'nav.sync',
    matchPrefixes: ['/sync', '/synced-chats', '/select-chats'],
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
