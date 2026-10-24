import { createFileRoute } from '@tanstack/react-router';
import { Dashboard } from '@/components/deepdive/Dashboard';
export const Route = createFileRoute('/run/$runId')({component: RunPage});
function RunPage() { const {runId} = Route.useParams(); return <Dashboard runId={runId} />; }
