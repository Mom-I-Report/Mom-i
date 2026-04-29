import type { Device, DeviceReport, GenerateReportRequest, ReportJson } from '../types/report';

const BASE = 'http://localhost:8000/api/v1';

export async function generateReport(req: GenerateReportRequest): Promise<ReportJson> {
  const res = await fetch(`${BASE}/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-local-key' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`서버 오류 ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function fetchDevices(apiKey: string): Promise<Device[]> {
  const res = await fetch(`${BASE}/admin/devices`, {
    headers: { 'X-API-Key': apiKey },
  });
  if (res.status === 403) throw new Error('API Key가 올바르지 않습니다.');
  if (!res.ok) throw new Error(`오류 ${res.status}`);
  return res.json();
}

export async function fetchDeviceReports(apiKey: string, serNo: string): Promise<DeviceReport[]> {
  const res = await fetch(`${BASE}/admin/devices/${encodeURIComponent(serNo)}/reports`, {
    headers: { 'X-API-Key': apiKey },
  });
  if (!res.ok) throw new Error(`오류 ${res.status}`);
  return res.json();
}
