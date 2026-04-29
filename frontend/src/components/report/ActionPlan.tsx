import { md2html, stripLeadingEmoji } from '../../lib/utils';
import type { SleepGuide } from '../../types/report';

interface Props { guide: SleepGuide }

export default function ActionPlan({ guide }: Props) {
  return (
    <div>
      <div className="section-label">핵심 솔루션</div>
      <div className="action-plan">
        <div className="action-plan-title">
          [ ACTION PLAN ] {stripLeadingEmoji(guide.title)}
        </div>
        <div
          className="action-plan-reason"
          dangerouslySetInnerHTML={{ __html: md2html(guide.reason) }}
        />
        <div className="action-steps">
          {guide.steps.map((s, i) => (
            <div className="action-step" key={i}>
              <span className="action-step-num">{String(i + 1).padStart(2, '0')}</span>
              <span
                className="action-step-text"
                dangerouslySetInnerHTML={{ __html: md2html(s) }}
              />
            </div>
          ))}
        </div>
        {guide.kick_action && (
          <div className="kick-action-wrap">
            <span
              className="kick-action-text"
              dangerouslySetInnerHTML={{ __html: md2html(stripLeadingEmoji(guide.kick_action)) }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
