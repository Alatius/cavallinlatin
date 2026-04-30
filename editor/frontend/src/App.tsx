import { Navigate, type RouteObject } from 'react-router-dom';

import ActivityPage from './editor/ActivityPage';
import EditorLayout from './editor/EditorLayout';
import EntryEditor from './editor/EntryEditor';
import EditorHome from './editor/EditorHome';
import LoginPage from './auth/LoginPage';
import InviteAcceptPage from './auth/InviteAcceptPage';
import RequireAuth from './auth/RequireAuth';
import PublicLayout from './public/PublicLayout';
import HomePage from './public/HomePage';
import EntryView from './public/EntryView';
import SearchPage from './public/SearchPage';

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'entry/:urlId', element: <EntryView /> },
      { path: 'search', element: <SearchPage /> },
      { path: 'lookup', element: <LookupRedirect /> },
    ],
  },
  { path: '/editor/login', element: <LoginPage /> },
  { path: '/editor/invite/:token', element: <InviteAcceptPage /> },
  {
    path: '/editor',
    element: (
      <RequireAuth>
        <EditorLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <EditorHome /> },
      { path: 'activity', element: <ActivityPage /> },
      { path: 'entry/:urlId', element: <EntryEditor /> },
    ],
  },
  { path: '*', element: <Navigate to="/" /> },
];

function LookupRedirect() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q') ?? '';
  if (!q) return <Navigate to="/" />;
  return <Navigate to={`/search?q=${encodeURIComponent(q)}`} replace />;
}
