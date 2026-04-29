import { createElement } from 'react';
import { createRoot } from 'react-dom/client';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import ReportBodyPdf from '../components/report/ReportBodyPdf';
import type { ReportJson } from '../types/report';

export async function exportPdf(rj: ReportJson, headerHtml: string, label: string): Promise<void> {
  const wrap = document.createElement('div');
  wrap.style.cssText = [
    'position:fixed', 'top:-99999px', 'left:0',
    'width:960px', 'background:#fff',
    'padding:28px 32px', 'box-sizing:border-box',
    'font-family:"Noto Sans KR",sans-serif',
  ].join(';');

  wrap.innerHTML = headerHtml;

  const bodyMount = document.createElement('div');
  bodyMount.style.marginTop = '18px';
  wrap.appendChild(bodyMount);

  document.body.appendChild(wrap);
  const root = createRoot(bodyMount);
  root.render(createElement(ReportBodyPdf, { rj }));

  // 차트 렌더링 대기
  await new Promise(r => setTimeout(r, 600));

  try {
    const canvas = await html2canvas(wrap, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
      width: 960,
    });

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pdfW = pdf.internal.pageSize.getWidth();
    const pdfH = pdf.internal.pageSize.getHeight();
    const totalImgH = (canvas.height / canvas.width) * pdfW;
    const imgData = canvas.toDataURL('image/png');

    let offsetY = 0;
    while (offsetY < totalImgH) {
      pdf.addImage(imgData, 'PNG', 0, -offsetY, pdfW, totalImgH);
      offsetY += pdfH;
      if (offsetY < totalImgH) pdf.addPage();
    }

    pdf.save(`Mom-i_${label}.pdf`);
  } finally {
    root.unmount();
    document.body.removeChild(wrap);
  }
}
