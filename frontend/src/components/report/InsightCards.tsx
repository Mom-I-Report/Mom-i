import { md2html } from '../../lib/utils';
import type { AiComment } from '../../types/report';

interface Props { comments: AiComment[] }

export default function InsightCards({ comments }: Props) {
  if (!comments.length) return null;

  return (
    <div>
      <div className="section-label">핵심 인사이트</div>
      <div className="insight-list">
        {comments.map((t, i) => (
          <div key={i} className={`insight-card ${t.type}`}>
            <div className="insight-type-label">
              {t.type === 'caution' ? 'ALERT' : 'EXCELLENT'}
            </div>
            <div className="insight-title">{t.title}</div>
            <div
              className="insight-text"
              dangerouslySetInnerHTML={{ __html: md2html(t.text) }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
