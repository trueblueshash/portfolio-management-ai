import { useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getComps, refreshComps } from '../api/client';
import { PublicComp } from '../types';

function fmtPercent(value: number | null): string {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function fmtRevenue(value: number | null, currency: string): string {
  if (value === null || value === undefined) return '—';
  if (currency === 'INR') return `₹${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}Cr`;
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}M`;
}

function fmtRevPerEmp(value: number | null): string {
  if (value === null || value === undefined) return '—';
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}K`;
}

function median(vals: number[]): number | null {
  if (!vals.length) return null;
  const sorted = [...vals].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) return (sorted[mid - 1] + sorted[mid]) / 2;
  return sorted[mid];
}

export default function CompsTable({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['comps', companyId],
    queryFn: () => getComps(companyId),
    enabled: !!companyId,
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshComps(companyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['comps', companyId] }),
  });

  const rows: PublicComp[] = data?.data || [];
  const latestFetched = rows.find((r) => !!r.fetched_at)?.fetched_at || null;
  const portfolioRow = rows.find((r) => r.is_portfolio_company);
  const peerRows = rows.filter((r) => !r.is_portfolio_company);

  const peerMedian = useMemo(() => {
    const toVals = (key: keyof PublicComp) =>
      peerRows.map((r) => r[key]).filter((v): v is number => typeof v === 'number');
    return {
      comp_name: 'Peer median',
      revenue_ttm_millions: median(toVals('revenue_ttm_millions')),
      revenue_growth_pct: median(toVals('revenue_growth_pct')),
      gross_margin_pct: median(toVals('gross_margin_pct')),
      operating_margin_pct: median(toVals('operating_margin_pct')),
      sm_pct_of_revenue: median(toVals('sm_pct_of_revenue')),
      rd_pct_of_revenue: median(toVals('rd_pct_of_revenue')),
      rule_of_40: median(toVals('rule_of_40')),
      revenue_per_employee_k: median(toVals('revenue_per_employee_k')),
    };
  }, [peerRows]);

  if (isLoading || refreshMutation.isPending) {
    return (
      <div className="border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-xl text-gray-900">Comps Benchmarking</h2>
          <div className="h-8 w-24 bg-gray-100 rounded animate-pulse" />
        </div>
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-200 bg-red-50 rounded-xl p-6">
        <p className="text-sm text-red-700 mb-3">Failed to load comps data.</p>
        <button onClick={() => queryClient.invalidateQueries({ queryKey: ['comps', companyId] })} className="px-3 py-1.5 bg-dawn text-white rounded text-sm font-semibold">Retry</button>
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="border border-gray-200 rounded-xl p-8 text-center">
        <h3 className="font-serif text-xl text-gray-900 mb-2">Pull competitor benchmarks</h3>
        <p className="text-sm text-gray-500 mb-4">Fetch comparable public company metrics and benchmark this company’s position.</p>
        <button onClick={() => refreshMutation.mutate()} className="px-4 py-2 bg-dawn text-white rounded-lg text-sm font-semibold">Pull Benchmarks</button>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <h2 className="font-serif text-xl text-gray-900">Comps Benchmarking</h2>
        <button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending} className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-200 text-gray-700 hover:border-dawn hover:text-dawn disabled:opacity-50">
          {refreshMutation.isPending ? 'Refreshing...' : 'Refresh data'}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full text-sm">
          <thead>
            <tr className="bg-gray-50/80">
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 sticky left-0 bg-gray-50/80">Company</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Rev (TTM)</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Growth %</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Gross %</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Op. %</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">S&M %</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">R&D %</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Rule of 40</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Rev/Emp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {[...(portfolioRow ? [portfolioRow] : []), ...peerRows].map((r) => (
              <tr key={r.id} className={r.is_portfolio_company ? 'bg-orange-50/40' : 'hover:bg-gray-50/40'}>
                <td className="px-4 py-2.5 sticky left-0 bg-inherit">
                  <div className="text-xs font-semibold text-gray-800 flex items-center gap-2">
                    {r.is_portfolio_company && <span className="w-2 h-2 rounded-full bg-dawn inline-block" />}
                    {r.comp_name}
                    {r.is_portfolio_company && <span className="px-1.5 py-0.5 rounded bg-dawn/10 text-dawn text-[10px]">Portfolio</span>}
                  </div>
                  {!r.is_portfolio_company && <div className="text-[11px] text-gray-400">{r.ticker || 'Private'}</div>}
                </td>
                <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtRevenue(r.revenue_ttm_millions, r.revenue_currency || 'USD')}</td>
                <td className={`px-3 py-2.5 text-right text-xs font-medium ${(r.revenue_growth_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-amber-600'}`}>{fmtPercent(r.revenue_growth_pct)}</td>
                <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(r.gross_margin_pct)}</td>
                <td className={`px-3 py-2.5 text-right text-xs font-medium ${(r.operating_margin_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-amber-600'}`}>{fmtPercent(r.operating_margin_pct)}</td>
                <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(r.sm_pct_of_revenue)}</td>
                <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(r.rd_pct_of_revenue)}</td>
                <td className={`px-3 py-2.5 text-right text-xs font-semibold ${(r.rule_of_40 ?? 0) >= 40 ? 'text-emerald-600' : (r.rule_of_40 ?? 0) < 20 ? 'text-amber-600' : 'text-gray-700'}`}>{r.rule_of_40 !== null && r.rule_of_40 !== undefined ? r.rule_of_40.toFixed(1) : '—'}</td>
                <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtRevPerEmp(r.revenue_per_employee_k)}</td>
              </tr>
            ))}
            <tr className="bg-gray-50">
              <td className="px-4 py-2.5 text-xs font-semibold text-gray-700 sticky left-0 bg-gray-50">Peer median</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">
                {fmtRevenue(peerMedian.revenue_ttm_millions, portfolioRow?.revenue_currency || 'USD')}
              </td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(peerMedian.revenue_growth_pct)}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(peerMedian.gross_margin_pct)}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(peerMedian.operating_margin_pct)}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(peerMedian.sm_pct_of_revenue)}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtPercent(peerMedian.rd_pct_of_revenue)}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{peerMedian.rule_of_40 !== null ? peerMedian.rule_of_40.toFixed(1) : '—'}</td>
              <td className="px-3 py-2.5 text-right text-xs text-gray-700">{fmtRevPerEmp(peerMedian.revenue_per_employee_k)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 text-xs text-gray-500">
        Source: yfinance + portfolio MIS · Last refresh {latestFetched ? formatDistanceToNow(new Date(latestFetched), { addSuffix: true }) : 'unknown'}
      </div>
    </div>
  );
}
