import { Chart } from 'react-chartjs-2';
import type { SleepDay } from '../../types/report';

interface Props { daily: SleepDay[] }

export default function BarChart({ daily }: Props) {
  return (
    <Chart
      type="bar"
      data={{
        labels: daily.map(d => d.day),
        datasets: [
          {
            type: 'bar' as const,
            label: '수면 (시간)',
            data: daily.map(d => d.sleep_h),
            backgroundColor: 'rgba(51,65,85,0.75)',
            borderRadius: 5,
            yAxisID: 'y',
            order: 2,
          },
          {
            type: 'line' as const,
            label: '뒤척임 (분)',
            data: daily.map(d => d.restless_min),
            borderColor: '#10B981',
            backgroundColor: 'rgba(16,185,129,0.1)',
            borderWidth: 2,
            pointBackgroundColor: '#10B981',
            pointRadius: 4,
            tension: 0.3,
            yAxisID: 'y2',
            order: 1,
          },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          y:  { position: 'left',  min: 0, ticks: { font: { size: 10 }, callback: (v) => `${v}h` },   grid: { color: '#F1F5F9' } },
          y2: { position: 'right', min: 0, ticks: { font: { size: 10 }, callback: (v) => `${v}분` }, grid: { drawOnChartArea: false } },
          x:  { ticks: { font: { size: 11, family: 'Noto Sans KR', weight: 'bold' } } },
        },
        plugins: {
          legend: { position: 'top', align: 'end', labels: { font: { size: 11, family: 'Noto Sans KR' }, boxWidth: 12, padding: 10 } },
        },
      }}
    />
  );
}
