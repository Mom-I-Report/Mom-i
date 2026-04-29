import BarChart from './BarChart';
import RadarChart from './RadarChart';
import ActionPlan from './ActionPlan';
import InsightCards from './InsightCards';
import DevCare from './DevCare';
import { fmtH } from '../../lib/utils';
import type { ReportJson } from '../../types/report';

interface Props { rj: ReportJson }

export default function ReportBodyPdf({ rj }: Props) {
  const summary   = rj.summary   ?? {};
  const breath    = rj.breath    ?? {};
  const bodyTemp  = rj.body_temp ?? {};
  const daily     = rj.daily     ?? [];
  const aiComment = rj.ai_comment ?? [];
  const tempClass = ({ '정상': '', '미열 주의': 'amber', '발열 의심': 'red' } as Record<string, string>)[bodyTemp?.status ?? ''] ?? '';

  return (
    <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start' }}>
      {/* 왼쪽: 데이터 요약 + 차트 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <div className="section-label">데이터 요약</div>
          <div className="overview-row">
            <div className="radar-wrap">
              <RadarChart summary={rj.summary} breath={rj.breath} bodyTemp={rj.body_temp} />
            </div>
            <div className="stat-list">
              <div className="stat-row"><span className="stat-label">평균 수면</span><span className="stat-val">{fmtH(summary.avg_sleep_h)}</span></div>
              <div className="stat-row"><span className="stat-label">평균 뒤척임</span><span className="stat-val">{summary.avg_restless_min ?? '-'}분</span></div>
              <div className="stat-row"><span className="stat-label">평균 호흡수</span><span className="stat-val mint">{breath.breath_avg ?? '-'} rpm</span></div>
              <div className="stat-row"><span className="stat-label">평균 체온</span><span className={`stat-val ${tempClass || 'red'}`}>{bodyTemp.body_temp_avg ?? '-'}°C</span></div>
            </div>
          </div>
        </div>
        {daily.length > 0 && (
          <div>
            <div className="section-label">일별 수면</div>
            <table className="pdf-daily-table">
              <thead><tr><th>DAY</th><th>SLEEP</th><th>TOSS</th><th>BREATH</th></tr></thead>
              <tbody>
                {daily.map(d => (
                  <tr key={d.day}>
                    <td>{d.day}</td>
                    <td style={{ color: '#10B981', fontWeight: 700 }}>{fmtH(d.sleep_h)}</td>
                    <td>{d.restless_min}m</td>
                    <td>{breath.breath_avg ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="daily-section" style={{ marginTop: 12, height: 150 }}>
              <BarChart daily={daily} />
            </div>
          </div>
        )}
      </div>

      {/* 오른쪽: AI 솔루션 + 인사이트 + 발달케어 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {rj.sleep_guide && <ActionPlan guide={rj.sleep_guide} />}
        {aiComment.length > 0 && <InsightCards comments={aiComment} />}
        {rj.age_kick && <DevCare ageKick={rj.age_kick} />}
      </div>
    </div>
  );
}
