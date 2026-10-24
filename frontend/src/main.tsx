import React from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRouter, RouterProvider } from '@tanstack/react-router';
import { routeTree } from './routeTree.gen';
import { Toaster } from '@/components/ui/sonner';
import './styles.css';
import './workspace.css';

const queryClient = new QueryClient({defaultOptions: {queries: {retry: 1, refetchOnWindowFocus: false}}});
const router = createRouter({routeTree});
declare module '@tanstack/react-router' { interface Register { router: typeof router } }
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><RouterProvider router={router}/><Toaster richColors /></QueryClientProvider></React.StrictMode>);
