# Mom-i 리포트 서비스 전체 흐름

> mermaid.live 또는 Notion 코드블록(mermaid)에 붙여넣으면 이미지로 렌더링됩니다.

```mermaid
sequenceDiagram
    autonumber
    participant App as 맘아이 앱
    participant Momi as 맘아이 서버
    participant Report as Mom-i 리포트 서버
    participant Relay as EMTAKE Relay 서버
    participant AI as Gemini AI
    participant Notify as SMS / 이메일

    rect rgb(219, 234, 254)
        Note over App,Report: 구독 등록 (최초 1회)
        App->>Momi: 리포트 서비스 구독 신청
        Momi->>Report: POST /subscriptions (ser_no, account)
        App->>Report: POST /share-targets — 알림 받을 연락처 등록 (JWT)
    end

    rect rgb(254, 243, 199)
        Note over Report,Notify: 주간 자동 리포트 생성 (매주 월요일 자동 실행)
        loop 구독자 전체 순회
            Report->>Relay: 7일치 센서 데이터 요청 (SensorData CMD)
            Relay-->>Report: 수면 · 환경 · 호흡 · 체온 데이터
            Report->>AI: AI 분석 요청
            AI-->>Report: 리포트 JSON (수면 패턴 · 조언 · 교육법)
            Report->>Report: 리포트 DB 저장
            Report->>Notify: SMS / 이메일 발송 (등록된 연락처 기준)
        end
    end

    rect rgb(220, 252, 231)
        Note over App,Report: 앱에서 리포트 열람
        App->>Report: GET /reports (JWT)
        Report-->>App: 리포트 목록 · 상세
    end
```

---

## API 목록 (리포트 서버 기준)

| 엔드포인트 | 인증 | 호출 주체 | 설명 |
|-----------|------|-----------|------|
| `POST /subscriptions` | X-API-Key | 맘아이 서버 | 구독 등록 |
| `DELETE /subscriptions/{ser_no}` | X-API-Key | 맘아이 서버 | 구독 해제 |
| `POST /share-targets` | JWT | 맘아이 앱 | 알림 수신자 추가 |
| `GET /share-targets` | JWT | 맘아이 앱 | 수신자 목록 조회 |
| `DELETE /share-targets/{id}` | JWT | 맘아이 앱 | 수신자 삭제 |
| `GET /reports` | JWT | 맘아이 앱 | 리포트 목록 조회 |
| `GET /reports/{id}` | JWT | 맘아이 앱 | 리포트 상세 조회 |

## 맘아이 서버가 제공해야 할 것

| 항목 | 용도 |
|------|------|
| `ser_no` | 기기 식별자 (구독 등록 시 전달) |
| `account` | EMTAKE 계정 이메일 (리포트 서버가 relay 호출에 사용) |
| JWT 발급 | 앱 → 리포트 서버 인증용 (HS256, `ser_no` 클레임 포함) |
