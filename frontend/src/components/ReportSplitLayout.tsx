import type { RefObject, ReactNode } from 'react';
import SleepReport from './SleepReport';
import ReportView from './ReportView';
import { isEmtakeReportData } from '../utils/sleepReportData';

type ReportMeta = {
  name?: string;
  ageMonths?: number;
  weekNum?: number;
  weekStart?: string;
  weekEnd?: string;
  generated?: string;
};

interface ReportSplitLayoutProps {
  viewMode: 'mobile' | 'pc';
  captureRef?: RefObject<HTMLDivElement | null>;
  apiReportData: Record<string, unknown> | null;
  meta?: ReportMeta;
  sleepReportData: Record<string, unknown>;
  childName: string;
  dateRange: string;
}

const PANEL_PAD = { pc: '10px 8px', mobile: '8px 6px' } as const;

export default function ReportSplitLayout({
  viewMode,
  captureRef,
  apiReportData,
  meta,
  sleepReportData,
  childName,
  dateRange,
}: ReportSplitLayoutProps) {
  const isPc = viewMode === 'pc';
  const isCompact = !isPc;
  const isApiReport = apiReportData != null && !isEmtakeReportData(apiReportData);

  const dataPanel = (
    <SleepReport
      embedded
      splitPanel={isPc}
      compact={isCompact}
      showGuidelines={false}
      reportData={sleepReportData}
      childName={childName}
      dateRange={dateRange}
    />
  );

  const guidelinesPanel = isApiReport ? (
    <ReportView data={apiReportData} meta={meta} mode="guidelines" hideSideAds compact={isCompact} />
  ) : (
    <div style={{ padding: isPc ? 20 : 14, color: 'var(--gray-mut)', fontSize: isCompact ? 11 : 13, textAlign: 'center', lineHeight: 1.5 }}>
      AI 리포트를 생성하면 수면 가이드라인이 표시됩니다.
    </div>
  );

  const panelInnerPc = (content: ReactNode, pad: string) => (
    <div className="report-panel-scroll" style={{ padding: pad }}>
      {content}
    </div>
  );

  const panelInnerMobile = (content: ReactNode) => (
    <div className="report-mobile-inner">{content}</div>
  );

  if (isPc) {
    return (
      <div ref={captureRef} className="report-split-shell report-split-shell--pc">
        <div className="report-panel report-panel--data">
          {panelInnerPc(dataPanel, PANEL_PAD.pc)}
        </div>
        <div className="report-panel">
          {panelInnerPc(guidelinesPanel, PANEL_PAD.pc)}
        </div>
      </div>
    );
  }

  return (
    <div ref={captureRef} className="report-split-shell report-split-shell--mobile">
      <div className="report-mobile-section">
        {panelInnerMobile(dataPanel)}
      </div>
      {isApiReport && (
        <div className="report-mobile-section">
          {panelInnerMobile(guidelinesPanel)}
        </div>
      )}
    </div>
  );
}
