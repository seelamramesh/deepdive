import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useResearch, safeUrl } from '@/lib/api';

export function ResearchForm({open, onClose, onCreated, parentId, initialQuestion = ''}: {open: boolean; onClose: () => void; onCreated: (id: string) => void; parentId?: string; initialQuestion?: string}) {
  const [question, setQuestion] = useState(initialQuestion);
  const [urls, setUrls] = useState('');
  const [rounds, setRounds] = useState(2);
  const [confidence, setConfidence] = useState(0.7);
  const [error, setError] = useState('');
  const mutation = useResearch(parentId);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    const sourceUrls = urls.split('\n').map(url => url.trim()).filter(Boolean);
    if (sourceUrls.length > 20 || sourceUrls.some(url => !safeUrl(url))) {setError('Enter up to 20 valid HTTP or HTTPS URLs.'); return;}
    try {
      const result = await mutation.mutateAsync({question: question.trim(), source_urls: sourceUrls, max_rounds: rounds, confidence_threshold: confidence});
      toast.success('Research started'); onCreated(result.run_id); onClose();
    } catch (failure) { const message = failure instanceof Error ? failure.message : 'Research failed to start'; setError(message); toast.error(message); }
  }
  return <Dialog open={open} onOpenChange={value => !value && !mutation.isPending && onClose()}><DialogContent className="mobile-dialog max-h-[90dvh] overflow-y-auto"><DialogHeader><DialogTitle>{parentId ? 'Research this gap' : 'New research'}</DialogTitle><DialogDescription>Evidence is checked before claims enter your report. More rounds use additional search and model calls.</DialogDescription></DialogHeader><form onSubmit={submit} className="space-y-4">
    <div><Label htmlFor="research-question">Question</Label><Textarea id="research-question" autoFocus minLength={10} maxLength={2000} required value={question} onChange={event => setQuestion(event.target.value)} placeholder="What would you like to research?" /></div>
    {!parentId && <div><Label htmlFor="source-urls">Source URLs · optional, one per line</Label><Textarea id="source-urls" value={urls} onChange={event => setUrls(event.target.value)} placeholder="https://example.org/report" /></div>}
    <div><Label htmlFor="research-rounds">Maximum rounds</Label><Input id="research-rounds" type="number" required min={1} max={5} value={rounds} onChange={event => setRounds(Number(event.target.value))} /></div>
    <div><Label htmlFor="confidence">Confidence threshold · {Math.round(confidence * 100)}%</Label><input className="w-full accent-primary" id="confidence" type="range" min="0.5" max="1" step="0.05" value={confidence} onChange={event => setConfidence(Number(event.target.value))} /></div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    <Button type="submit" disabled={mutation.isPending || question.trim().length < 10}>{mutation.isPending ? 'Starting…' : 'Start research'}</Button>
  </form></DialogContent></Dialog>;
}
