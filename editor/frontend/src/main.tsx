import React from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, Outlet, RouterProvider } from 'react-router-dom';

import { routes } from './App';
import { AuthProvider } from './auth/AuthContext';
import './styles/app.css';
import './styles/entry.css';

const router = createBrowserRouter(
  [
    {
      element: (
        <AuthProvider>
          <Outlet />
        </AuthProvider>
      ),
      children: routes,
    },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') },
);

const root = createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
