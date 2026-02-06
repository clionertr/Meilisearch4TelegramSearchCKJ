export interface ActivityItem {
  id: number;
  title: string;
  time: string;
  summary: string;
  count?: number;
  image?: string;
  initial?: string;
  bgGradient?: string;
  isOnline?: boolean;
}

export interface ChatItem {
    id: number;
    title: string;
    type: 'Group' | 'Channel' | 'Private';
    messages: string;
    status?: 'Real-time' | 'Paused';
    image?: string;
    initial?: string;
    colorClass?: string;
    selected?: boolean;
}

export interface SearchResult {
    id: number;
    title: string;
    time: string;
    subtext: string;
    avatarInitials?: string;
    avatarImage?: string;
    avatarColor?: string;
    context: {
        prev: string;
        match: {
            sender: string;
            text: string;
            highlight: string;
            after: string;
        };
        next: string;
        file?: string;
    };
}