import { useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { generateOnePager, getOnePager, updateOnePagerField } from '../api/client';
import { MetricRow, OnePager } from '../types';

type EditableField =
  | 'stance'
  | 'stance_summary'
  | 'next_milestone'
  | 'metrics_table'
  | 'performance_narrative'
  | 'working_well'
  | 'needs_improvement'
  | 'value_creation';

const STANCE_META = {
  green: { label: 'Executing well', emoji: '🟢', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  yellow: { label: 'Needs attention', emoji: '🟡', className: 'bg-amber-50 text-amber-700 border-amber-200' },
  red: { label: 'Significant concerns', emoji: '🔴', className: 'bg-orange-50 text-orange-700 border-orange-200' },
} as const;

function bulletText(items: string[] = []): string {
  return items.join('\n');
}

function parseBullets(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function OnePagerSection({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<EditableField | null>(null);
  const [draftStance, setDraftStance] = useState<'green' | 'yellow' | 'red'>('yellow');
  const [draftText, setDraftText] = useState('');
  const [draftMetrics, setDraftMetrics] = useState<MetricRow[]>([]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['onepager', companyId],
    queryFn: () => getOnePager(companyId),
    enabled: !!companyId,
  });

  const onepager: OnePager | null = data?.data ?? null;

  const editedFields = useMemo(() => {
    const history = onepager?.edit_history ?? [];
    return new Set(history.map((h) => h.field));
  }, [onepager]);

  const startEdit = (field: EditableField) => {
    if (!onepager) return;
    setEditing(field);
    if (field === 'stance') {
      setDraftStance(onepager.stance);
      setDraftText(onepager.stance_summary || '');
      return;
    }
    if (field === 'metrics_table') {
      setDraftMetrics(onepager.metrics_table || []);
      setDraftText(bulletText(onepager.performance_narrative || []));
      return;
    }
    if (field === 'working_well') setDraftText(bulletText(onepager.working_well || []));
    else if (field === 'needs_improvement') setDraftText(bulletText(onepager.needs_improvement || []));
    else if (field === 'value_creation') setDraftText(bulletText(onepager.value_creation || []));
    else if (field === 'next_milestone') setDraftText(onepager.next_milestone || '');
    else if (field === 'stance_summary') setDraftText(onepager.stance_summary || '');
    else setDraftText('');
  };

  const resetEditor = () => {
    setEditing(null);
    setDraftText('');
    setDraftMetrics([]);
  };

  const generateMutation = useMutation({
    mutationFn: () => generateOnePager(companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onepager', companyId] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ field, value }: { field: EditableField; value: any }) => {
      if (!onepager) throw new Error('No one-pager found');
      return updateOnePagerField(onepager.id, field, value);
    },
  });

  const saveEdit = async () => {
    if (!editing || !onepager) return;
    try {
      if (editing === 'stance') {
        await updateMutation.mutateAsync({ field: 'stance', value: draftStance });
        await updateMutation.mutateAsync({ field: 'stance_summary', value: draftText.trim() });
      } else if (editing === 'metrics_table') {
        await updateMutation.mutateAsync({ field: 'metrics_table', value: draftMetrics });
        await updateMutation.mutateAsync({ field: 'performance_narrative', value: parseBullets(draftText) });
      } else if (editing === 'working_well' || editing === 'needs_improvement' || editing === 'value_creation') {
        await updateMutation.mutateAsync({ field: editing, value: parseBullets(draftText) });
      } else {
        await updateMutation.mutateAsync({ field: editing, value: draftText.trim() });
      }
      queryClient.invalidateQueries({ queryKey: ['onepager', companyId] });
      resetEditor();
    } catch (_err) {
      // Handled by mutation state; keep editor open for retry.
    }
  };

  if (isLoading || generateMutation.isPending) {
    return (
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100 bg-gray-50/50">
          <h2 className="font-serif text-xl text-gray-900">Portfolio One-Pager</h2>
          <p className="text-xs text-gray-400 mt-1">Analyzing metrics, documents, and intelligence...</p>
        </div>
        <div className="px-6 py-6 space-y-3">
          <div className="h-4 bg-gray-100 rounded animate-pulse" />
          <div className="h-4 bg-gray-100 rounded w-5/6 animate-pulse" />
          <div className="h-24 bg-gray-100 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-200 bg-red-50 rounded-xl p-6">
        <h3 className="font-serif text-lg text-red-700">Could not load one-pager</h3>
        <p className="text-sm text-red-600 mt-1 mb-4">Please try again.</p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['onepager', companyId] })}
          className="px-4 py-2 bg-dawn text-white rounded-lg text-sm font-semibold hover:bg-dawn/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!onepager) {
    return (
      <div className="border border-gray-200 rounded-xl p-8 text-center">
        <h3 className="font-serif text-xl text-gray-900 mb-2">Generate your first one-pager</h3>
        <p className="text-sm text-gray-500 mb-5">
          Build a structured weekly portfolio update using metrics, internal docs, and recent intelligence.
        </p>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="px-5 py-2.5 bg-dawn text-white rounded-lg text-sm font-semibold hover:bg-dawn/90 disabled:opacity-50"
        >
          {generateMutation.isPending ? 'Generating...' : 'Generate One-Pager'}
        </button>
      </div>
    );
  }

  const stanceMeta = STANCE_META[onepager.stance];
  const docsUsed = Array.isArray(onepager.data_sources?.documents_used) ? onepager.data_sources.documents_used.length : (onepager.data_sources?.documents_used ? 1 : 0);
  const intelCount = onepager.data_sources?.intelligence_count ?? 0;
  const periodCount = onepager.data_sources?.metrics_periods?.length ?? 0;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100 bg-gray-50/50 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-xl text-gray-900">Portfolio One-Pager</h2>
          <p className="text-xs text-gray-400 mt-1">
            {onepager.period_label} · Generated {formatDistanceToNow(new Date(onepager.generated_at), { addSuffix: true })} · {onepager.generated_by === 'manual' ? 'AI-generated, manually edited' : 'AI-generated'}
          </p>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-200 text-gray-700 hover:border-dawn hover:text-dawn"
        >
          🔄 Regenerate
        </button>
      </div>

      <div className="p-6 space-y-5">
        <section className="border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-start gap-3 mb-2">
            <h3 className="font-serif text-lg text-gray-900">Overall Stance</h3>
            <button onClick={() => startEdit('stance')} className="text-xs text-gray-500 hover:text-dawn">✏️ Edit</button>
          </div>
          {editing === 'stance' ? (
            <div className="space-y-2">
              <select value={draftStance} onChange={(e) => setDraftStance(e.target.value as 'green' | 'yellow' | 'red')} className="border border-gray-200 rounded px-2 py-1 text-sm">
                <option value="green">Green</option>
                <option value="yellow">Yellow</option>
                <option value="red">Red</option>
              </select>
              <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} rows={3} className="w-full border border-gray-200 rounded px-3 py-2 text-sm" />
              <div className="flex gap-2">
                <button onClick={saveEdit} className="px-3 py-1.5 bg-dawn text-white rounded text-xs font-semibold">Save</button>
                <button onClick={resetEditor} className="px-3 py-1.5 border border-gray-200 rounded text-xs">Cancel</button>
              </div>
            </div>
          ) : (
            <>
              <div className={`inline-flex items-center gap-2 px-2.5 py-1 text-xs font-semibold rounded-full border ${stanceMeta.className}`}>
                <span>{stanceMeta.emoji}</span>
                <span>{stanceMeta.label}</span>
              </div>
              <p className="text-sm text-gray-600 mt-2">{onepager.stance_summary}</p>
              {editedFields.has('stance') && <span className="text-[11px] text-dawn font-medium">Edited</span>}
            </>
          )}
        </section>

        <section className="border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-start gap-3 mb-2">
            <h3 className="font-serif text-lg text-gray-900">Next Milestone</h3>
            <button onClick={() => startEdit('next_milestone')} className="text-xs text-gray-500 hover:text-dawn">✏️ Edit</button>
          </div>
          {editing === 'next_milestone' ? (
            <div className="space-y-2">
              <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} rows={2} className="w-full border border-gray-200 rounded px-3 py-2 text-sm" />
              <div className="flex gap-2">
                <button onClick={saveEdit} className="px-3 py-1.5 bg-dawn text-white rounded text-xs font-semibold">Save</button>
                <button onClick={resetEditor} className="px-3 py-1.5 border border-gray-200 rounded text-xs">Cancel</button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-700">{onepager.next_milestone}</p>
              {editedFields.has('next_milestone') && <span className="text-[11px] text-dawn font-medium">Edited</span>}
            </>
          )}
        </section>

        <section className="border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-start gap-3 mb-3">
            <h3 className="font-serif text-lg text-gray-900">Performance Update</h3>
            <button onClick={() => startEdit('metrics_table')} className="text-xs text-gray-500 hover:text-dawn">✏️ Edit</button>
          </div>
          {editing === 'metrics_table' ? (
            <div className="space-y-3">
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">Metric</th>
                      <th className="px-2 py-1 text-left">Current</th>
                      <th className="px-2 py-1 text-left">Previous</th>
                      <th className="px-2 py-1 text-left">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draftMetrics.map((row, idx) => (
                      <tr key={`${row.metric_name}-${idx}`} className="border-t border-gray-100">
                        <td className="px-2 py-1"><input value={row.metric_name} onChange={(e) => setDraftMetrics(draftMetrics.map((r, i) => (i === idx ? { ...r, metric_name: e.target.value } : r)))} className="w-full border border-gray-200 rounded px-2 py-1" /></td>
                        <td className="px-2 py-1"><input value={row.current_value} onChange={(e) => setDraftMetrics(draftMetrics.map((r, i) => (i === idx ? { ...r, current_value: e.target.value } : r)))} className="w-full border border-gray-200 rounded px-2 py-1" /></td>
                        <td className="px-2 py-1"><input value={row.previous_value} onChange={(e) => setDraftMetrics(draftMetrics.map((r, i) => (i === idx ? { ...r, previous_value: e.target.value } : r)))} className="w-full border border-gray-200 rounded px-2 py-1" /></td>
                        <td className="px-2 py-1"><input value={row.change_pct} onChange={(e) => setDraftMetrics(draftMetrics.map((r, i) => (i === idx ? { ...r, change_pct: e.target.value } : r)))} className="w-full border border-gray-200 rounded px-2 py-1" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} rows={4} className="w-full border border-gray-200 rounded px-3 py-2 text-sm" placeholder="One bullet per line" />
              <div className="flex gap-2">
                <button onClick={saveEdit} className="px-3 py-1.5 bg-dawn text-white rounded text-xs font-semibold">Save</button>
                <button onClick={resetEditor} className="px-3 py-1.5 border border-gray-200 rounded text-xs">Cancel</button>
              </div>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50/80">
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Metric</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Current</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Previous</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(onepager.metrics_table || []).map((row, idx) => (
                      <tr key={`${row.metric_name}-${idx}`} className="border-t border-gray-100">
                        <td className="px-3 py-2 text-xs text-gray-700">{row.metric_name}</td>
                        <td className="px-3 py-2 text-xs text-gray-700">{row.current_value}</td>
                        <td className="px-3 py-2 text-xs text-gray-700">{row.previous_value}</td>
                        <td className="px-3 py-2 text-xs font-medium text-gray-700">{row.change_pct} {row.trend === 'up' ? '↑' : row.trend === 'down' ? '↓' : '→'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ul className="mt-3 space-y-1 text-sm text-gray-600">
                {(onepager.performance_narrative || []).map((item, idx) => (
                  <li key={`${item}-${idx}`}>• {item}</li>
                ))}
              </ul>
              {(editedFields.has('metrics_table') || editedFields.has('performance_narrative')) && <span className="text-[11px] text-dawn font-medium">Edited</span>}
            </>
          )}
        </section>

        {(
          [
            { title: '✅ What\'s Working Well', field: 'working_well' as EditableField, items: onepager.working_well || [] },
            { title: '⚠️ What Needs Improvement', field: 'needs_improvement' as EditableField, items: onepager.needs_improvement || [] },
            { title: '🎯 Value Creation Areas', field: 'value_creation' as EditableField, items: onepager.value_creation || [] },
          ]
        ).map((section) => (
          <section key={section.field} className="border border-gray-200 rounded-lg p-4">
            <div className="flex justify-between items-start gap-3 mb-2">
              <h3 className="font-serif text-lg text-gray-900">{section.title}</h3>
              <button onClick={() => startEdit(section.field)} className="text-xs text-gray-500 hover:text-dawn">✏️ Edit</button>
            </div>
            {editing === section.field ? (
              <div className="space-y-2">
                <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} rows={5} className="w-full border border-gray-200 rounded px-3 py-2 text-sm" placeholder="One bullet per line" />
                <div className="flex gap-2">
                  <button onClick={saveEdit} className="px-3 py-1.5 bg-dawn text-white rounded text-xs font-semibold">Save</button>
                  <button onClick={resetEditor} className="px-3 py-1.5 border border-gray-200 rounded text-xs">Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <ul className="space-y-1 text-sm text-gray-600">
                  {section.items.map((item, idx) => (
                    <li key={`${section.field}-${idx}`}>• {item}</li>
                  ))}
                </ul>
                {editedFields.has(section.field) && <span className="text-[11px] text-dawn font-medium">Edited</span>}
              </>
            )}
          </section>
        ))}
      </div>

      <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 text-xs text-gray-500">
        Data sources: {periodCount} metric periods · {docsUsed} documents · {intelCount} intel
      </div>
    </div>
  );
}
