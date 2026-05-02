import DataSummary from './DataSummary';
import DailySection from './DailySection';
import ActionPlan from './ActionPlan';
import InsightCards from './InsightCards';
import DevCare from './DevCare';
import type { ReportJson } from '../../types/report';

interface Props {
  rj: ReportJson;
  showTrend?: boolean;
}

export default function ReportBody({ rj, showTrend = false }: Props) {
  const daily      = rj.daily       ?? [];
  const aiComment  = rj.ai_comment  ?? [];

  return (
    <div className="report-body">
      <DataSummary
        summary={rj.summary}
        breath={rj.breath}
        bodyTemp={rj.body_temp}
        trend={rj.trend}
        showTrend={showTrend}
      />

      <DailySection daily={daily} breath={rj.breath} />

      {daily.length > 0 && <hr className="rep-divider" />}

      {rj.sleep_guide && <ActionPlan guide={rj.sleep_guide} />}

      {aiComment.length > 0 && <InsightCards comments={aiComment} />}

      {rj.age_kick && <DevCare ageKick={rj.age_kick} />}
    </div>
  );
}
