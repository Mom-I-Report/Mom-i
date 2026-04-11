# M-Take AI 수면 분석 백엔드

영유아 수면 분석 리포트 생성 서비스 백엔드입니다. (FastAPI + DDD 아키텍처)

## 구조 설명
- `app/domain`: 비즈니스 엔티티 및 스키마
- `app/application`: 유스케이스 로직
- `app/infrastructure`: 외부 시스템 (DB, Gemini AI, PDF 등) 연동
- `app/interfaces`: API 엔드포인트 라우팅

## 실행 방법
1. 가상 환경을 만들어 활성화 (선택)
2. `pip install -r requirements.txt`
3. 터미널(backend 폴더 내)에서 `uvicorn app.main:app --reload`
