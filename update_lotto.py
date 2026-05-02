#!/usr/bin/env python3
"""
로또 당첨번호 자동 업데이트 스크립트
data/lotto.json 파일을 최신 5회차로 업데이트합니다.
"""
import urllib.request
import json
import os
from datetime import datetime

DATA_FILE = 'data/lotto.json'

# 현재 데이터 로드
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    current = json.load(f)

existing_rounds = {r['round'] for r in current['rounds']}
latest_round = max(r['round'] for r in current['rounds'])
print(f"현재 최신 회차: {latest_round}회")

# 예상 최신 회차 계산
first_draw = datetime(2002, 12, 7)
estimated = 1 + (datetime.now() - first_draw).days // 7
print(f"예상 최신 회차: {estimated}회")

# 새 회차 fetch
new_rounds = []
for r in range(estimated + 2, latest_round, -1):
    if r < 1:
        continue
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
            continue

        entry = {
            'round': data['drwNo'],
            'nums': [data['drwtNo1'], data['drwtNo2'], data['drwtNo3'],
                     data['drwtNo4'], data['drwtNo5'], data['drwtNo6']],
            'bonus': data['bnusNo'],
            'date': data['drwNoDate'],
        }
        new_rounds.append(entry)
        print(f"  OK {entry['round']}회 ({entry['date']}): {entry['nums']} + {entry['bonus']}")

    except Exception as e:
        print(f"  FAIL {r}회 fetch 실패: {e}")

if not new_rounds:
    print("새로운 회차가 없거나 아직 추첨되지 않았습니다.")
else:
    all_rounds = current['rounds'] + new_rounds
    seen = set()
    unique = []
    for r in all_rounds:
        if r['round'] not in seen:
            seen.add(r['round'])
            unique.append(r)
    unique.sort(key=lambda x: x['round'], reverse=True)
    latest_5 = unique[:5]

    os.makedirs('data', exist_ok=True)
    result = {
        'updated': datetime.now().strftime('%Y-%m-%d'),
        'rounds': latest_5
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! {len(new_rounds)}개 신규 회차 추가 (최신: {latest_5[0]['round']}회)")
