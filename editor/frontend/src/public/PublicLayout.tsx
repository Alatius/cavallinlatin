import { Link, Outlet, useMatch } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { HeadwordsProvider } from '../components/HeadwordsContext';
import IndexPanel from '../components/IndexPanel';
import MobileSearchBar from './MobileSearchBar';

export default function PublicLayout() {
  const { user } = useAuth();
  const entryMatch = useMatch('/entry/:urlId');
  const editorDest = entryMatch?.params.urlId
    ? `/editor/entry/${entryMatch.params.urlId}`
    : '/editor';

  return (
    <HeadwordsProvider>
      <div className="editor-shell editor-shell--public">
        <header className="editor-shell__header">
          <Link to="/" className="editor-shell__home">
            Cavallins latinsk-svenska lexikon
          </Link>
          <div className="editor-shell__spacer" />
          {user ? (
            <Link to={editorDest}>Redigeringsläge</Link>
          ) : (
            <Link to="/editor/login">
              Logga in<span className="hide-on-mobile"> som redaktör</span>
            </Link>
          )}
        </header>
        <MobileSearchBar basePath="/entry" />
        <div className="editor-shell__body">
          <IndexPanel basePath="/entry" showStatusFilter={false} />
          <main className="editor-shell__main">
            <Outlet />
          </main>
        </div>
      </div>
    </HeadwordsProvider>
  );
}
