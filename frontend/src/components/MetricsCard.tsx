import { HeadlineMetric } from '../api/metrics';

function formatValue(value: number | null, unit: string, currency?: string): string {
  if (value === null || value === undefined) return '—';

  const sym = currency === 'INR' ? '₹' : '$';
  const bigLabel = currency === 'INR' ? 'Cr' : 'M';
  const smallLabel = currency === 'INR' ? 'L' : 'K';

  if (unit === '%') {
    if (Math.abs(value) <= 1) return `${(value * 100).toFixed(1)}%`;
    return `${value.toFixed(1)}%`;
  }
  if (unit === 'x') return `${value.toFixed(1)}x`;
  if (unit === '#') return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (unit === 'months') return `${value.toFixed(1)} mo`;
  if (unit === '$Mn' || unit === 'INR Cr') return `${sym}${value.toFixed(1)}${bigLabel}`;
  if (unit === '$K' || unit === 'INR L') {
    if (Math.abs(value) >= 1000) return `${sym}${(value / 1000).toFixed(1)}${bigLabel}`;
    return `${sym}${value.toFixed(0)}${smallLabel}`;
  }
  if (unit === '$' || unit === 'INR') {
    if (Math.abs(value) >= 10000000) return `${sym}${(value / 10000000).toFixed(1)}${bigLabel}`;
    if (Math.abs(value) >= 100000) return `${sym}${(value / 100000).toFixed(1)}${smallLabel}`;
    if (Math.abs(value) >= 1000) return `${sym}${(value / 1000).toFixed(0)}${smallLabel}`;
    return `${sym}${value.toFixed(0)}`;
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export default function MetricsCard({ metric, currency }: { metric: HeadlineMetric; currency?: string }) {
  const isPositive = metric.change_pct !== null && metric.change_pct >= 0;
  // For churn and burn, negative change is actually good
  const invertedMetrics = ['churn', 'burn'];
  const isInverted = invertedMetrics.some(k => metric.raw_name.toLowerCase().includes(k));
  const isGood = isInverted ? !isPositive : isPositive;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-300 transition-colors">
      <div className="text-xs text-gray-400 font-medium mb-1.5 truncate">{metric.name}</div>
      <div className="text-2xl font-semibold text-gray-900 tracking-tight font-sans">
        {formatValue(metric.value, metric.unit, currency)}
      </div>
      {metric.change_pct !== null && (
        <div className={`text-xs font-medium mt-1 ${isGood ? 'text-emerald-600' : 'text-red-500'}`}>
          {metric.change_pct > 0 ? '↑' : '↓'} {Math.abs(metric.change_pct).toFixed(1)}% MoM
        </div>
      )}
    </div>
  );
}

export { formatValue };
