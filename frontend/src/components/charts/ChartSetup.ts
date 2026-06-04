import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
} from 'chart.js';

// 전역으로 Chart.js 요소 등록
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

// PDF 캡처 시 그래프 선명도 향상 (devicePixelRatio 2x)
ChartJS.defaults.devicePixelRatio = 2;

// 재사용 가능한 차트 옵션/색상 설정
export const chartColors = {
  radarBackground: 'rgba(28,28,30,0.05)',
  radarBorder: '#1C1C1E',
  radarPoint: '#1C1C1E',
  barSleep: 'rgba(28, 28, 30, 0.85)',
  lineRestless: '#24614A',
  lineRestlessBg: 'rgba(36,97,74,0.1)',
  pointBorder: '#FFFFFF',
  textLight: '#8E8E93',
  textDark: '#3A3A3C',
  gridLight: '#E5E5EA'
};
