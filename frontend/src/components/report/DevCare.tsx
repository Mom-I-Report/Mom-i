import { md2html } from '../../lib/utils';
import type { AgeKick } from '../../types/report';

interface Props { ageKick: AgeKick }

export default function DevCare({ ageKick }: Props) {
  return (
    <div>
      <div className="section-label">발달 케어</div>
      <div className="dev-care-card">
        <div className="dev-care-title">{ageKick.title}</div>
        <div
          className="dev-care-text"
          dangerouslySetInnerHTML={{ __html: md2html(ageKick.text) }}
        />
      </div>
    </div>
  );
}
