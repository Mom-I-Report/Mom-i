export interface SleepDay {
  day: string;
  sleep_h: number;
  restless_min: number;
  date?: string;
}

export interface Summary {
  avg_sleep_h?: number;
  avg_restless_min?: number;
  cry_count?: number;
}

export interface Breath {
  breath_avg?: number;
  breath_min?: number;
  breath_max?: number;
  is_normal?: boolean;
}

export interface BodyTemp {
  body_temp_avg?: number;
  status?: '정상' | '미열 주의' | '발열 의심';
}

export interface Trend {
  sleep_vs_last_week?: number;
  restless_vs_last_week?: number;
  cry_vs_last_week?: number;
}

export interface AiComment {
  type: 'caution' | 'good';
  icon: string;
  title: string;
  text: string;
}

export interface SleepGuide {
  method_name: string;
  title: string;
  reason: string;
  steps: string[];
  kick_action?: string;
}

export interface AgeKick {
  title: string;
  text: string;
  is_wonder_weeks?: boolean;
}

export interface ReportJson {
  summary?: Summary;
  breath?: Breath;
  body_temp?: BodyTemp;
  daily?: SleepDay[];
  trend?: Trend;
  ai_comment?: AiComment[];
  sleep_guide?: SleepGuide | null;
  age_kick?: AgeKick | null;
  week_label?: string;
}

// API 요청/응답 타입
export interface SleepInput {
  date: string;
  sleep_min: number;
  restless_min: number;
}

export interface GenerateReportRequest {
  ser_no: string;
  baby_age_months: number;
  week_start: string;
  sleep: SleepInput[];
  environment: { temp_avg: number; temp_max: number; temp_min: number; db_max: number; db_avg: number };
  breath: { breath_min: number; breath_max: number; breath_avg: number };
  body_temp: { body_temp_min: number; body_temp_max: number; body_temp_avg: number };
  monthly: { month_sleep_h: number; month_restless_h: number };
  events: { cry_count: number; leave_count: number };
}

export interface Device {
  ser_no: string;
  subscribed_at: string | null;
  last_report_at: string | null;
  report_count: number;
}

export interface DeviceReport {
  report_id: number;
  week_start: string;
  created_at: string;
  report_json: ReportJson;
}
