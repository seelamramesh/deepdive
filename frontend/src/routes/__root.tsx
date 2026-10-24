import { createRootRoute, Outlet } from '@tanstack/react-router';
export const Route = createRootRoute({component: Outlet, notFoundComponent: () => <main className="p-10"><h1>Page not found</h1><a href="/">Open workspace</a></main>});
