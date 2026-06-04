"""
patch_content.py — content-draft-merged.json 검수 패치
실행: python patch_content.py
"""
import json, os, copy

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "content-draft-merged.json")

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

entries = {e["id"]: e for e in data["entries"]}

def e(id_): return entries[id_]

# ── id=1 ──────────────────────────────────────────────
# separation_sleep_guide: Drowsy But Awake → 한국어
e(1)["separation_sleep_guide"] = (
    "4개월은 분리수면 준비를 시작하기 좋은 첫 시점이에요. "
    "수면 구조가 성인형으로 바뀌는 이 시기부터 "
    "졸리지만 깨어있는 상태로 눕히기 원칙을 낮잠부터 천천히 연습해보세요."
)

# ── id=2 ──────────────────────────────────────────────
# separation_sleep_guide: Drowsy But Awake → 한국어
e(2)["separation_sleep_guide"] = (
    "수면 퇴행으로 분리수면이 어렵게 느껴질 수 있어요. "
    "하지만 이 시기에 졸리지만 깨어있는 상태로 눕히는 원칙을 포기하지 마세요. "
    "퇴행은 2~6주 내 자연스럽게 회복됩니다."
)

# ── id=7 ──────────────────────────────────────────────
# sleep_activities[2]: Sleep Prop → 한국어
e(7)["sleep_activities"][2] = (
    "저녁 목욕 후 수유→졸음→눕히기 순서 연습: "
    "수면 보조물 없이 스스로 잠드는 연습으로 건강한 수면 연상 형성"
)

# ── id=9 ──────────────────────────────────────────────
# sleep_activities[1]: EASY 루틴 → 한국어
e(9)["sleep_activities"][1] = (
    "이유식 후 감각 놀이: 이유식 후 짧은 탐색 놀이로 "
    "'먹기→놀기→자기' 순서를 자연스럽게 형성"
)

# ── id=13 ──────────────────────────────────────────────
# dev_status: 레이크 그라스프 → 한국어
e(13)["dev_status"] = e(13)["dev_status"].replace(
    "집게손가락으로 물건을 가리키거나 긁어 모으는 레이크 그라스프가 발달합니다",
    "집게손가락으로 물건을 가리키거나 손가락으로 긁어 모으는 동작이 발달합니다"
)

# ── id=16 ──────────────────────────────────────────────
# sleep_activities[2]: 환경 점검(팁) → 실제 놀이 활동
e(16)["sleep_activities"][2] = (
    "취침 전 부드러운 스트레칭: 기어가기와 서기로 긴장된 팔·다리 근육을 "
    "가볍게 이완시켜 편안한 수면 진입을 도와줌"
)
# separation_sleep_guide: 체크인 → 확인 방문
e(16)["separation_sleep_guide"] = e(16)["separation_sleep_guide"].replace(
    "체크인", "확인 방문"
)

# ── id=17 ──────────────────────────────────────────────
# sleep_activities[2]: 팁성 문구 → 실제 활동
e(17)["sleep_activities"][2] = (
    "취침 1시간 전 조용한 그림책 보기: 기어다니며 흥분된 아기가 차분해질 수 있도록 "
    "조명을 낮추고 그림책을 함께 보며 각성 수준 낮추기"
)

# ── id=20 ──────────────────────────────────────────────
# sleep_activities[1]: 콩·쌀 질식 위험 → 안전한 활동으로 교체
e(20)["sleep_activities"][1] = (
    "크기 다른 블록·컵 집기 놀이: 크기가 다른 블록이나 컵을 하나씩 집어 "
    "담는 놀이로 집게 잡기 발달, 소근육 에너지 소모"
)

# ── id=22 ──────────────────────────────────────────────
# sleep_activities[2]: ↓ 기호 → 글로
e(22)["sleep_activities"][2] = (
    "취침 전 포옹 충분히: 분리불안이 심한 시기일수록 낮 접촉을 충분히 해 "
    "취침 시 분리 저항을 줄여줌"
)

# ── id=29 ──────────────────────────────────────────────
# sleep_activities[2]: 팁성 문구 + Overtired → 실제 활동
e(29)["sleep_activities"][2] = (
    "취침 전 포옹과 자장가: 걷기 배우는 시기는 에너지 소모가 크므로 "
    "오후 7시 전 취침을 목표로 하고, 포옹과 자장가로 차분하게 마무리"
)

# ── id=42 ──────────────────────────────────────────────
# sleep_activities[0]: 수면 수용성↑ → 글로
e(42)["sleep_activities"][0] = (
    "인형 재우기 놀이: 인형에게 이불 덮고 자장가 불러주기, "
    "모방 능력이 발달하는 이 시기에 취침 루틴을 놀이로 자연스럽게 학습해 수면 수용성을 높여줌"
)
# sleep_activities[2]: 수면 수용성↑ → 글로, 도약10 → 이 시기
e(42)["sleep_activities"][2] = (
    "취침 전 인형 함께 재우기: '우리 모두 잘 시간' 의식으로 수면 수용성을 높이고, "
    "이 시기 발달 특성(시스템·순서 이해)을 활용해 '잘 시간은 정해진 것' 규칙을 자연스럽게 학습"
)

# ── id=44 ──────────────────────────────────────────────
# dev_status: tantrum → 한국어
e(44)["dev_status"] = e(44)["dev_status"].replace(
    "감정 폭발(tantrum)", "감정 폭발(떼쓰기)"
)

# ── id=55 ──────────────────────────────────────────────
# separation_sleep_guide: Overtired → 한국어
e(55)["separation_sleep_guide"] = e(55)["separation_sleep_guide"].replace(
    "Overtired가 되기 쉬워요",
    "너무 피곤한 상태가 되기 쉬워요"
)

# ── 최종 저장 ──────────────────────────────────────────
data["entries"] = list(entries.values())
data["status"] = "검수완료 — mwlee 2026-06-05 (영문→한국어, 안전, 활동 보완)"

with open(PATH, encoding="utf-8", newline="\n") as _: pass  # 인코딩 확인
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("패치 완료!")
print("수정 항목:")
print("  id=1,2   separation_sleep_guide: Drowsy But Awake → 한국어")
print("  id=7     sleep_activities[2]: Sleep Prop → 한국어")
print("  id=9     sleep_activities[1]: EASY 루틴 → 한국어")
print("  id=13    dev_status: 레이크 그라스프 → 한국어")
print("  id=16    sleep_activities[2]: 팁→활동 / 체크인→확인 방문")
print("  id=17    sleep_activities[2]: 팁 → 실제 활동")
print("  id=20    sleep_activities[1]: 콩·쌀(질식위험) → 블록 집기")
print("  id=22    sleep_activities[2]: ↓ 기호 → 한글")
print("  id=29    sleep_activities[2]: 팁+Overtired → 실제 활동")
print("  id=42    sleep_activities[0,2]: ↑ 기호 → 한글, 도약10 → 이 시기")
print("  id=44    dev_status: tantrum → 떼쓰기")
print("  id=55    separation_sleep_guide: Overtired → 너무 피곤한 상태")
