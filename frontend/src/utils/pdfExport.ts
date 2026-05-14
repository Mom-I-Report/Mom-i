import html2canvas from 'html2canvas';

export async function downloadPdf(el: HTMLElement, label: string): Promise<void> {
  const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false, backgroundColor: '#ffffff' });
  const { jsPDF } = await import('jspdf');
  const pdfW = 210;
  const pdfH = Math.round(pdfW * canvas.height / canvas.width);
  const pdf = new jsPDF({ orientation: pdfH > pdfW ? 'portrait' : 'landscape', unit: 'mm', format: [pdfW, pdfH] });
  pdf.addImage(canvas.toDataURL('image/jpeg', 0.95), 'JPEG', 0, 0, pdfW, pdfH);
  const elRect = el.getBoundingClientRect();
  const scaleX = pdfW / el.offsetWidth;
  const scaleY = pdfH / el.offsetHeight;
  el.querySelectorAll<HTMLElement>('[data-ad-link]').forEach(adEl => {
    const url = adEl.getAttribute('data-ad-link');
    if (!url) return;
    const adRect = adEl.getBoundingClientRect();
    pdf.link(
      (adRect.left - elRect.left) * scaleX,
      (adRect.top  - elRect.top)  * scaleY,
      adRect.width  * scaleX,
      adRect.height * scaleY,
      { url },
    );
  });
  pdf.save(`momi-${label}.pdf`);
}
