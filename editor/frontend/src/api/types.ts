export type EntryType =
  | 'primary'
  | 'derived'
  | 'proper'
  | 'plain'
  | 'reference'
  | 'etym';

export type Status =
  | 'untouched'
  | 'in_progress'
  | 'approved';

export const STATUS_VALUES: Status[] = [
  'untouched', 'in_progress', 'approved',
];

export const STATUS_LABEL_SV: Record<Status, string> = {
  untouched: 'Obearbetad',
  in_progress: 'Pågående',
  approved: 'Godkänd',
};

export interface User {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
}

export interface LockInfo {
  user_id: number;
  display_name: string;
  expires_at: number;
}

export interface EntrySummary {
  url_id: string;
  headword: string;
  alt_headwords: string[];
  type: EntryType;
  status: Status;
  comment_count: number;
}

export interface Entry {
  url_id: string;
  xml_id: string | null;
  xml_root: string | null;
  type: EntryType;
  headword: string;
  alt_headwords: string[];
  status: Status;
  xml_body: string;
  starting_column: string | null;
  prev_url_id: string | null;
  next_url_id: string | null;
  updated_at: number;
  lock: LockInfo | null;
}

export interface EntryList {
  total: number;
  offset: number;
  limit: number;
  items: EntrySummary[];
}

export interface SearchHit {
  url_id: string;
  headword: string;
  snippet: string;
}

export interface SearchResults {
  query: string;
  total: number;
  items: SearchHit[];
}

export interface InviteInfo {
  email: string | null;
  display_name: string | null;
  expires_at: number;
}

export interface Comment {
  id: number;
  user_id: number;
  display_name: string;
  body: string;
  created_at: number;
}

export interface ActivityItem {
  url_id: string;
  headword: string;
  user_id: number | null;
  display_name: string | null;
  snippet: string | null;
  at: number;
  count: number;
}
