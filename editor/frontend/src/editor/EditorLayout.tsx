import { Link, Outlet, useMatch, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { HeadwordsProvider } from '../components/HeadwordsContext';
import IndexPanel from '../components/IndexPanel';

export default function EditorLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const entryMatch = useMatch('/editor/entry/:urlId');
  const publicDest = entryMatch?.params.urlId
    ? `/entry/${entryMatch.params.urlId}`
    : '/';

  async function onLogout() {
    await logout();
    navigate('/editor/login');
  }

  return (
    <HeadwordsProvider>
      <div className="editor-shell">
        <header className="editor-shell__header">
          <span className="editor-shell__user">
            {user?.display_name}
          </span>
          <div className="editor-shell__spacer" />
          <Link to="/editor/activity" className="editor-shell__nav">Aktivitet</Link>
          <Link to={publicDest} className="editor-shell__public">Publik vy</Link>
          <button type="button" className="editor-shell__logout" onClick={onLogout}>
            Logga ut
          </button>
        </header>
        <div className="editor-shell__body">
          <IndexPanel basePath="/editor/entry" />
          <main className="editor-shell__main">
            <Outlet />
          </main>
        </div>
      </div>
    </HeadwordsProvider>
  );
}
