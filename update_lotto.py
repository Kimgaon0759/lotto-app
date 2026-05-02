#!/usr/bin/env python3
"""
로또 당첨번호 자동 업데이트 스크립트
data/lotto.json 에 1217회 이후 모든 새 회차를 저장합니다.
GitHub Actions가 매주 토요일 자동 실행합니다.
"""
import urllib.request
import json
import os
from datetime import datetime

DATA_FILE = 'data/lotto.json'
BASE_ROUND = 1216  # index.html의 BASE_FREQ 기준 회차

# 현재 저장된 데이터 로드
try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        current = json.load(f)
    existing = {r['round']: r for r in current.get('rounds', [])}
except Exception:
    existing = {}

latest_saved = max(existing.keys()) if existing else BASE_ROUND
print(f"현재 저장된 최신 회차: {latest_saved}회")

# 예상 최신 회차 계산
first_draw = datetime(2002, 12, 7)
estimated = 1 + (datetime.now() - first_draw).days // 7
print(f"예상 최신 회차: {estimated}회")

# BASE_ROUND+1 이후 모든 회차 fetch (누락 없이 전부)
new_count = 0
for r in range(BASE_ROUND + 1, estimated + 3):
    if r in existing:
        continue  # 이미 있는 회차 스킵
    try:
        url = f'https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.dhlottery.co.kr/',
        })
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())

        if data.get('returnValue') != 'success':
            print(f"  -- {r}회: 아직 추첨 안됨, 종료")
            break

        entry = {
            'round': data['drwNo'],
            'nums': [data['drwtNo1'], data['drwtNo2'], data['drwtNo3'],
                     data['drwtNo4'], data['drwtNo5'], data['drwtNo6']],
            'bonus': data['bnusNo'],
            'date': data['drwNoDate'],
        }
        existing[r] = entry
        new_count += 1
        print(f"  OK {entry['round']}회 ({entry['date']}): {entry['nums']} + {entry['bonus']}")

    except Exception as e:
        print(f"  FAIL {r}회: {e}")
        break

if new_count == 0:
    print("새로운 회차 없음 — 이미 최신 상태입니다.")
else:
    # 회차 순서 정렬 후 저장
    all_rounds = sorted(existing.values(), key=lambda x: x['round'], reverse=True)
    os.makedirs('data', exist_ok=True)
    result = {
        'updated': datetime.now().strftime('%Y-%m-%d'),
        'latest': all_rounds[0]['round'],
        'rounds': all_rounds  # 전체 저장 (통계+최근 표시 모두 활용)
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n완료! {new_count}개 신규 추가 — 총 {len(all_rounds)}회차 저장 (최신: {all_rounds[0]['round']}회)")
