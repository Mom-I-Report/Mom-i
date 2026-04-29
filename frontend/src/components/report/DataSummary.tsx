import RadarChart from './RadarChart';
import { fmtH } from '../../lib/utils';
import type { Summary, Breath, BodyTemp, Trend } from '../../types/report';

interface Props {
  summary?: Summary;
  breath?: Breath;
  bodyTemp?: BodyTemp;
  trend?: Trend;
  showTrend?: boolean;
}

function TrendBadge({ val, unit }: { val?: number; unit: string }) {
  if (val == null || val === 0) return null;
  const sign  = val > 0 ? '+' : '';
  const color = val > 0 ? '#10B981' : '#DC2626';
  return <span style={{ fontSize: 10, color, marginLeft: 4 }}>{sign}{val}{unit}</span>;
}

export default function DataSummary({ summary, breath, bodyTemp, trend, showTrend }: Props) {
  const tempClass = ({ '정상': '', '미열 주의': 'amber', '발열 의심': 'red' } as Record<string, string>)[bodyTemp?.status ?? ''] ?? '';

  return (
    <div>
      <div className="section-label">데이터 요약</div>
      <div className="overview-row">
        <div className="radar-wrap">
          <RadarChart summary={summary} breath={breath} bodyTemp={bodyTemp} />
        </div>
        <div className="stat-list">
          <div className="stat-row">
            <span className="stat-label">평균 수면</span>
            <span className="stat-val">
              {fmtH(summary?.avg_sleep_h)}
              {showTrend && <TrendBadge val={trend?.sleep_vs_last_week} unit="h" />}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">평균 뒤척임</span>
            <span className="stat-val">
              {summary?.avg_restless_min ?? '-'}분
              {showTrend && <TrendBadge val={trend?.restless_vs_last_week} unit="분" />}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">평균 호흡수</span>
            <span className="stat-val mint">{breath?.breath_avg ?? '-'} rpm</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">평균 체온</span>
            <span className={`stat-val ${tempClass || 'red'}`}>{bodyTemp?.body_temp_avg ?? '-'}°C</span>
          </div>
        </div>
      </div>
    </div>
  );
}
