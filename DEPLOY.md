# Lightsail 배포 가이드

## 권장 인스턴스 스펙

| 항목 | 권장 |
|------|------|
| OS | Ubuntu 22.04 LTS |
| RAM | 2GB 이상 (MariaDB + FastAPI + APScheduler 동시 실행) |
| 스토리지 | 20GB 이상 |
| 방화벽 포트 | SSH 22, API 8000 |

---

## 1. 서버 초기 설정 (최초 1회)

```bash
# 패키지 업데이트
sudo apt-get update && sudo apt-get upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 설치 확인
docker --version
docker compose version
```

---

## 2. 코드 배포

```bash
# 코드 클론
git clone <레포 URL> /srv/momi
cd /srv/momi

# 또는 업데이트 시
git pull origin dev
```

---

## 3. 환경변수 설정

`.env.example`을 참고해 **서버에서 직접** `.env` 파일을 생성합니다.  
절대로 로컬 개발용 `.env`를 그대로 복사하지 않습니다 (API 키 혼용 방지).

```bash
cp .env.example .env
nano .env   # 또는 vim .env
```

### 운영 환경 값 생성 방법

```bash
# DB 패스워드 (DB_PASSWORD, DB_ROOT_PASSWORD)
openssl rand -base64 32

# JWT_SECRET (맘아이 메인 서버와 반드시 동일한 값이어야 함)
openssl rand -base64 64

# ADMIN_API_KEY
openssl rand -base64 32
```

### 운영 .env 예시

```env
DB_ROOT_PASSWORD=<openssl 생성값>
DB_NAME=momi_db
DB_USER=momi_user
DB_PASSWORD=<openssl 생성값>

PROJECT_NAME="맘아이 리포트 서버"
GEMINI_API_KEY=<Google AI Studio 운영 키>

DATABASE_URL="mysql+pymysql://momi_user:<DB_PASSWORD>@localhost:3306/momi_db"

JWT_SECRET=<맘아이 메인 서버와 동일한 값>
ADMIN_API_KEY=<openssl 생성값>
```

> **주의**: `DATABASE_URL`의 패스워드 부분은 DB_PASSWORD와 동일한 값으로 직접 입력합니다.  
> 도커 실행 시 `docker-compose.yml`이 `DATABASE_URL`을 컨테이너 내부 호스트(`db`)로 자동 오버라이드합니다.

---

## 4. 빌드 및 실행

```bash
cd /srv/momi

# 운영 배포 — override 파일 제외하고 실행 (중요!)
docker compose -f docker-compose.yml up -d --build
```

> `docker compose up -d`(인수 없음)는 `docker-compose.override.yml`도 함께 적용되어  
> 코드 볼륨 마운트 + --reload가 활성화됩니다. 운영에서는 반드시 `-f docker-compose.yml` 지정.

---

## 5. 최초 실행 확인

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.yml ps

# 앱 로그 확인 (DB 연결 및 테이블 생성 확인)
docker compose -f docker-compose.yml logs -f app

# 헬스체크
curl http://localhost:8000/health
# 정상: {"status":"ok","version":"0.2.0"}
```

앱 최초 기동 시 `create_tables()`가 자동으로 `Weekly_Data`, `Generated_Reports` 테이블을 생성합니다.  
로그에서 다음을 확인합니다:

```
INFO  uvicorn.error — Application startup complete.
INFO  ... — [스케줄러] rolling 삭제 스케줄러 시작 (매주 월요일 10:00)
```

---

## 6. Lightsail 방화벽 설정

Lightsail 콘솔 → 인스턴스 → **네트워킹** 탭에서 인바운드 규칙 추가:

| 프로토콜 | 포트 | 용도 |
|----------|------|------|
| TCP | 22 | SSH |
| TCP | 8000 | API 서버 |

> 맘아이 메인 서버 IP만 허용하려면 소스를 해당 IP로 제한합니다 (보안 강화).

---

## 7. 코드 업데이트

```bash
cd /srv/momi
git pull origin dev

# 이미지 재빌드 후 재시작 (다운타임 수 초)
docker compose -f docker-compose.yml up -d --build app
```

DB 스키마가 변경된 경우:

```bash
# 컨테이너 내에서 Alembic 마이그레이션 실행
docker compose -f docker-compose.yml exec app alembic upgrade head
```

---

## 8. 로그 확인

```bash
# 실시간 로그
docker compose -f docker-compose.yml logs -f app

# 최근 200줄
docker compose -f docker-compose.yml logs --tail=200 app

# DB 로그
docker compose -f docker-compose.yml logs --tail=50 db
```

---

## 9. 서비스 중단 / 재시작

```bash
# 재시작
docker compose -f docker-compose.yml restart app

# 전체 종료
docker compose -f docker-compose.yml down

# 전체 종료 + DB 볼륨 삭제 (데이터 초기화 — 주의!)
docker compose -f docker-compose.yml down -v
```

---

## 10. 트러블슈팅

### 앱이 즉시 종료되는 경우
환경변수 누락이 원인입니다. 로그에서 확인:
```bash
docker compose -f docker-compose.yml logs app | grep "ValueError"
# 예: ValueError: 필수 환경변수가 설정되지 않았습니다: GEMINI_API_KEY
```
`.env` 파일을 수정 후 재시작합니다.

### DB 연결 실패
```bash
# DB 컨테이너 상태 확인
docker compose -f docker-compose.yml ps db
# DB가 healthy인지 확인 후 앱 재시작
docker compose -f docker-compose.yml restart app
```

### Gemini API 오류
로그에서 에러 코드 확인:
- `429`: 요청 한도 초과 — 자동 재시도(최대 5회) 후 실패 시 500 반환
- `503`: Gemini 일시 장애 — 동일하게 자동 재시도

### 디스크 공간 부족
```bash
# 미사용 도커 리소스 정리
docker system prune -f
```
