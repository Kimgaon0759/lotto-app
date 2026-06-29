#!/usr/bin/env python3
"""
로또 당첨번호 자동 업데이트 스크립트
신규 API(selectPstLt645InfoNew.do)로 data/lotto.json 업데이트.
GitHub Actions가 매주 토요일 자동 실행합니다.

API 파라미터 규칙:
  srchLtEpsd=N 요청 시 실제 에피소드 N+4 반환 (2026-06 기준).
  에피소드 r을 얻으려면 srchLtEpsd = r-4 로 요청 후 반환값 검증.
  에피소드 1221 미만은 신규 API에 없음(구 시스템 전용).
"""
import urllib.request
import http.cookiejar
import json
import os
import time
from datetime import datetime

DATA_FILE = 'data/lotto.json'
BASE_ROUND = 1216

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.dhlottery.co.kr/lt645/result',
}
API_OFFSET = 4  # srchLtEpsd = r - OFFSET 로 에피소드 r 조회

def init_session():
    req = urllib.request.Request('https://www.dhlottery.co.kr/', headers={
        'User-Agent': HEADERS['User-Agent'],
    })
    opener.open(req, timeout=10)

def fetch_round(r):
    """
    에피소드 r을 신규 API로 fetch.
    반환된 에피소드가 r과 일치하면 entry dict, 아니면 None 반환.
    list가 빈 경우도 None.
    """
    ts = int(time.time() * 1000)
    srch = r - API_OFFSET
    url = (f'https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do'
           f'?srchDir=center&srchLtEpsd={srch}&_={ts}')
    req = urllib.request.Request(url, headers=HEADERS)
    with opener.open(req, timeout=12) as res:
        data = json.loads(res.read().decode())
    items = data.get('data', {}).get('list', [])
    if not items:
        return None
    item = items[0]
    if item['ltEpsd'] != r:
        return None  # 원하는 회차 없음 (신규 DB 부재 또는 초과)
    raw = str(item['ltRflYmd'])  # "20260627"
    return {
        'round': item['ltEpsd'],
        'nums': [item['tm1WnNo'], item['tm2WnNo'], item['tm3WnNo'],
                 item['tm4WnNo'], item['tm5WnNo'], item['tm6WnNo']],
        'bonus': item['bnsWnNo'],
        'date': f"{raw[:4]}-{raw[4:6]}-{raw[6:]}",
    }

# 현재 저장된 데이터 로드
try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        current = json.load(f)
    existing = {r['round']: r for r in current.get('rounds', [])}
except Exception:
    existing = {}

latest_saved = max(existing.keys()) if existing else BASE_ROUND
print(f"현재 저장된 최신 회차: {latest_saved}회")

first_draw = datetime(2002, 12, 7)
estimated = 1 + (datetime.now() - first_draw).days // 7
print(f"예상 최신 회차: {estimated}회")

init_session()

new_count = 0
no_data_streak = 0

for r in range(BASE_ROUND + 1, estimated + 3):
    if r in existing:
        continue
    try:
        entry = fetch_round(r)
    except Exception as e:
        print(f"  FAIL {r}회: {e}")
        break

    if entry is None:
        no_data_streak += 1
        if no_data_streak <= 5:
            print(f"  -- {r}회: 신규 API 데이터 없음 (스킵)")
            continue  # 구간 공백 가능 → 계속 탐색
        else:
            # 연속 5회 데이터 없으면 최신 이후로 판단
            print(f"  종료: {r}회 이후 데이터 없음")
            break

    no_data_streak = 0
    existing[r] = entry
    new_count += 1
    print(f"  OK {entry['round']}회 ({entry['date']}): {entry['nums']} + {entry['bonus']}")

if new_count == 0:
    print("새로운 회차 없음 — 이미 최신 상태입니다.")
else:
    all_rounds = sorted(existing.values(), key=lambda x: x['round'], reverse=True)
    os.makedirs('data', exist_ok=True)
    result = {
        'updated': datetime.now().strftime('%Y-%m-%d'),
        'latest': all_rounds[0]['round'],
        'rounds': all_rounds
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n완료! {new_count}개 신규 추가 — 총 {len(all_rounds)}회차 저장 (최신: {all_rounds[0]['round']}회)")
