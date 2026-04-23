# DB 정리

> ⚠ **[DEPRECATED — 초기 설계안]** 이 문서는 2026-04-11 초기 5테이블 설계안입니다.  
> 현재 구현은 `Weekly_Data` + `Generated_Reports` + ETF 3개 테이블 구조입니다.  
> 최신 DB 스키마는 [`research.md`](./research.md) 섹션 4 또는 [`plan.md`](./plan.md) 섹션 7을 참조하세요.

---

### **1. Users (부모 + 아이 정보 통합)**

- **설명**: 아이를 돌보는 앱이므로 사용자 정보에 아이 데이터를 포함하여 관리 포인트를 줄입니다.
- **필드**: 이메일, 아이 이름, 생년월일, 성별, 카메라 식별 번호(`ser_no`).

### **2. Daily_Sleep_Logs (수면 전문 로그)**

- **설명**: 엠테이크 프로토콜의 핵심인 수면 시간 데이터를 날짜별로 저장합니다.
- **필드**: 실제 수면(`day_gs`), 뒤척임(`day_pr`), 측정 날짜.

### **3. Environment_Logs (환경 지표 로그)**

- **설명**: 초단위로 들어오는 온도/소음 데이터를 가공하여 저장하며, 리포트 시각화의 핵심 소스가 됩니다.
- **필드**: 최고/최저/평균 온도, 소음 피크치(`db_max`).

### **4. Event_Logs (AI '킥' 전용 소스)**

- **설명**: 울음, 카메라 이탈 등 정형화되지 않은 돌발 상황을 따로 관리하여 리포트의 풍부함을 더합니다.
- **필드**: 이벤트 타입(`Crying` 등), 발생 시간.

### DB 스키마 (MySQL/MariaDB)

- - 1. 사용자 및 아이 통합 정보
CREATE TABLE Users (
user_id INT AUTO_INCREMENT PRIMARY KEY,
email VARCHAR(100) NOT NULL UNIQUE, -- 사용자 계정 및 리포트 수신
baby_name VARCHAR(50) NOT NULL, -- 아이 이름 (호칭용)
baby_birth DATE NOT NULL, -- 아이 생일 (월령 계산용)
baby_gender ENUM('M', 'F') NOT NULL, -- 아이 성별 (가이드 기준)
ser_no VARCHAR(50) NOT NULL UNIQUE, -- 카메라 시리얼 번호 (Serno)
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
- - 2. 일일 수면 로그
CREATE TABLE Daily_Sleep_Logs (
sleep_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
day_gs VARCHAR(20), -- 실제 수면 시간 (SleepData)
day_pr VARCHAR(20), -- 뒤척임 시간 (SleepData)
measured_date DATE NOT NULL, -- 측정 날짜
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
- - 3. 일일 환경 통계 로그
CREATE TABLE Environment_Logs (
env_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
temp_avg FLOAT, -- 평균 온도 (IndoorTemp)
temp_max FLOAT, -- 최고 온도
temp_min FLOAT, -- 최저 온도
db_max INT, -- 최대 소음 (dB)
measured_date DATE NOT NULL,
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
- - 4. 특이사항 이벤트 로그
CREATE TABLE Event_Logs (
event_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
event_type VARCHAR(20), -- 이벤트 타입 (울음, 이탈 등)
event_time DATETIME, -- 이벤트 발생 시각
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
- - 5. 리포트 생성 이력
CREATE TABLE Generated_Reports (
report_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
ai_kick_comment TEXT, -- AI 생성 인사이트 (Kick)
report_url VARCHAR(255), -- 리포트 파일 링크
measured_week_start DATE, -- 해당 주차 시작일
is_deleted BOOLEAN DEFAULT FALSE, -- 파일 삭제 여부 (비용 관리)
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
