/**
 * downloadPdf.ts
 *
 * html2canvas + jsPDF 기반 PDF 변환 유틸리티.
 *
 * ── 핵심 문제 & 해결 ──────────────────────────────────────────────
 * html2canvas는 DOM을 캡처할 때 Chart.js <canvas> 를 빈 캔버스로
 * 찍는 경우가 있습니다. 원인은 두 가지입니다.
 *
 *   1. Chart.js가 내부적으로 offscreen canvas를 사용하거나
 *      'willReadFrequently' 속성이 없으면 브라우저가 GPU 컨텍스트를
 *      공유하지 않아 toDataURL()이 빈 값을 반환합니다.
 *   2. html2canvas의 useCORS:true 여도 same-origin canvas는
 *      별도 처리가 필요합니다.
 *
 * 해결책: 캡처 직전에 모든 <canvas> 를 동일 크기의 <img> 로 교체하고,
 * 캡처 완료 후 원래대로 복원합니다. Chart.js 인스턴스는 건드리지 않으므로
 * 화면 표시에는 전혀 영향이 없습니다.
 * ──────────────────────────────────────────────────────────────────
 */

import html2canvas from "html2canvas";

/* ── 타입 ─────────────────────────────────────────────────── */
interface CanvasSnapshot {
  canvas:   HTMLCanvasElement;
  parent:   HTMLElement;
  nextSibling: ChildNode | null;
  img:      HTMLImageElement;
}

/* ── Chart.js 캔버스 → <img> 치환 (캡처 전) ───────────────── */
function replaceCanvasWithImages(root: HTMLElement): CanvasSnapshot[] {
  const snapshots: CanvasSnapshot[] = [];

  root.querySelectorAll<HTMLCanvasElement>("canvas").forEach((canvas) => {
    // 이미 픽셀이 없는 캔버스는 건너뜀
    const dataUrl = canvas.toDataURL("image/png");
    if (!dataUrl || dataUrl === "data:,") return;

    const img = document.createElement("img");
    img.src    = dataUrl;
    img.width  = canvas.offsetWidth;
    img.height = canvas.offsetHeight;
    img.style.cssText = canvas.style.cssText; // 인라인 스타일 복사
    img.style.display = "block";

    const parent      = canvas.parentElement as HTMLElement;
    const nextSibling = canvas.nextSibling;

    parent.replaceChild(img, canvas);

    snapshots.push({ canvas, parent, nextSibling, img });
  });

  return snapshots;
}

/* ── <img> → 원래 <canvas> 복원 (캡처 후) ────────────────── */
function restoreCanvases(snapshots: CanvasSnapshot[]): void {
  snapshots.forEach(({ canvas, parent, nextSibling, img }) => {
    parent.replaceChild(canvas, img);
    // nextSibling이 있으면 원래 위치로 이동
    if (nextSibling) {
      parent.insertBefore(canvas, nextSibling);
    }
  });
}

/* ── 메인 PDF 변환 함수 ───────────────────────────────────── */
export async function downloadPdf(
  el:    HTMLElement,
  label: string,
): Promise<void> {
  // 1. Chart.js 캔버스를 <img>로 교체
  const snapshots = replaceCanvasWithImages(el);

  let canvas: HTMLCanvasElement;
  try {
    // 2. html2canvas 캡처
    canvas = await html2canvas(el, {
      scale:           2,          // 레티나 대응 — 선명도 유지
      useCORS:         true,
      logging:         false,
      backgroundColor: "#ffffff",  // 투명 배경 방지
      // 스크롤 offset 보정 — 모달/오버레이에서 캡처할 때 위치 틀어짐 방지
      scrollX: -window.scrollX,
      scrollY: -window.scrollY,
      windowWidth:  document.documentElement.scrollWidth,
      windowHeight: document.documentElement.scrollHeight,
    });
  } finally {
    // 3. 캡처 성공 여부와 무관하게 DOM 복원
    restoreCanvases(snapshots);
  }

  // 4. jsPDF로 PDF 생성
  const { jsPDF } = await import("jspdf");

  const pdfW = 210; // A4 너비 (mm)
  const pdfH = Math.round(pdfW * canvas.height / canvas.width);

  const pdf = new jsPDF({
    orientation: pdfH > pdfW ? "portrait" : "landscape",
    unit:        "mm",
    format:      [pdfW, pdfH],
  });

  pdf.addImage(
    canvas.toDataURL("image/jpeg", 0.95),
    "JPEG",
    0, 0,
    pdfW, pdfH,
  );

  // 5. data-ad-link 속성 요소에 PDF 하이퍼링크 삽입 (기존 로직 유지)
  const elRect = el.getBoundingClientRect();
  const scaleX = pdfW / el.offsetWidth;
  const scaleY = pdfH / el.offsetHeight;

  el.querySelectorAll<HTMLElement>("[data-ad-link]").forEach((adEl) => {
    const url = adEl.getAttribute("data-ad-link");
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
