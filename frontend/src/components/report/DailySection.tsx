import BarChart from './BarChart';
import { fmtH } from '../../lib/utils';
import type { SleepDay, Breath } from '../../types/report';

interface Props {
  daily: SleepDay[];
  breath?: Breath;
}

export default function DailySection({ daily, breath }: Props) {
  if (!daily.length) return null;

  return (
    <>
      <hr className="rep-divider" />
      <div>
        <table className="daily-table">
          <thead>
            <tr><th>DAY</th><th>SLEEP</th><th>TOSS</th><th>BREATH</th><th>TEMP</th></tr>
          </thead>
          <tbody>
            {daily.map(d => (
              <tr key={d.day}>
                <td>{d.day}</td>
                <td className="sleep-col">{fmtH(d.sleep_h)}</td>
                <td>{d.restless_min}m</td>
                <td>{breath?.breath_avg ?? '-'}</td>
                <td>-</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <div className="daily-section" style={{ height: 160 }}>
          <BarChart daily={daily} />
        </div>
      </div>
    </>
  );
}
