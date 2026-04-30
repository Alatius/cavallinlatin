import type { LockInfo } from '../api/types';

interface Props {
  lock: LockInfo | null;
  selfUserId: number | null;
}

export default function LockIndicator({ lock, selfUserId }: Props) {
  if (!lock || lock.user_id === selfUserId) return null;
  const minutesLeft = Math.max(0, Math.round((lock.expires_at - Date.now() / 1000) / 60));
  return (
    <div className="lock-indicator">
      {lock.display_name} redigerar (ca {minutesLeft} min kvar)
    </div>
  );
}
