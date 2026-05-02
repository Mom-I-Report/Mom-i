import { Radar } from 'react-chartjs-2';
import type { Summary, Breath, BodyTemp } from '../../types/report';

interface Props {
  summary?: Summary;
  breath?: Breath;
  bodyTemp?: BodyTemp;
}

function radarScores(summary?: Summary, breath?: Breath, bodyTemp?: BodyTemp): number[] {
  const sleep  = Math.min(100, Math.round((summary?.avg_sleep_h    || 0) / 14 * 100));
  const stable = Math.max(0,   Math.round(100 - (summary?.avg_restless_min || 0) / 60 * 100));
  const bScore = breath?.is_normal ? 100 : 45;
  const tScore = ({ '정상': 100, '미열 주의': 60, '발열 의심': 20 } as Record<string, number>)[bodyTemp?.status ?? ''] ?? 100;
  return [sleep, stable, bScore, tScore];
}

export default function RadarChart({ summary, breath, bodyTemp }: Props) {
  return (
    <Radar
      data={{
        labels: ['수면', '안정도', '호흡', '체온'],
        datasets: [{
          data: radarScores(summary, breath, bodyTemp),
          backgroundColor: 'rgba(51,65,85,0.12)',
          borderColor: '#334155',
          borderWidth: 2,
          pointBackgroundColor: '#334155',
          pointRadius: 3,
        }],
      }}
      options={{
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0, max: 100,
            ticks: { display: false },
            grid: { color: '#E2E8F0' },
            pointLabels: {
              font: { size: 9, family: 'Noto Sans KR', weight: 'bold' },
              color: '#334155',
            },
          },
        },
        plugins: { legend: { display: false } },
        animation: { duration: 400 },
      }}
    />
  );
}
