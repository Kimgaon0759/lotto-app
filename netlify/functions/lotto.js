// netlify/functions/lotto.js
// 동행복권 API를 서버 측에서 호출해서 CORS 문제 해결

exports.handler = async (event) => {
  const round = event.queryStringParameters?.round;

  // round 없으면 최신 회차 자동 계산
  const firstDraw = new Date('2002-12-07');
  const estimated = 1 + Math.floor((new Date() - firstDraw) / (7 * 24 * 60 * 60 * 1000));
  const targetRound = round ? parseInt(round) : estimated;

  const results = [];

  // round 지정 없으면 최근 8회 병렬 fetch
  const rounds = round
    ? [targetRound]
    : Array.from({ length: 8 }, (_, i) => estimated + 1 - i).filter(r => r >= 1);

  await Promise.all(rounds.map(async (r) => {
    try {
      const url = `https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo=${r}`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
        signal: AbortSignal.timeout(6000),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.returnValue !== 'success') return;
      results.push({
        round: data.drwNo,
        nums: [data.drwtNo1, data.drwtNo2, data.drwtNo3, data.drwtNo4, data.drwtNo5, data.drwtNo6],
        bonus: data.bnusNo,
        date: data.drwNoDate,
      });
    } catch (e) { /* 개별 실패 무시 */ }
  }));

  results.sort((a, b) => b.round - a.round);

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=3600', // 1시간 캐시
    },
    body: JSON.stringify({ rounds: results }),
  };
};
