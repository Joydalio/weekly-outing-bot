# 주간 나들이 추천 봇

매주 수요일 오전 8시(KST), 만 4세 여아와 함께 갈 강동구 둔촌오륜역 인근
나들이 장소를 AI가 추천해 텔레그램으로 보내줍니다.

## 한 번만 하면 되는 설치

### 1. 텔레그램 봇 만들기
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 안내대로 이름 입력
2. 받은 **봇 토큰**(예: `123456:ABC-...`)을 복사해 둡니다.

### 2. 내 chat_id 얻기
1. 방금 만든 봇과의 대화창에서 아무 메시지나 보냅니다.
2. 브라우저에서 `https://api.telegram.org/bot<봇토큰>/getUpdates` 접속
3. 응답에서 `"chat":{"id": 숫자}`의 **숫자**가 chat_id 입니다.

### 3. Anthropic API 키
[console.anthropic.com](https://console.anthropic.com) → API Keys에서 발급.

### 4. GitHub 저장소 + 시크릿
1. 이 코드를 GitHub 저장소에 올립니다.
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서
   다음 3개를 등록:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

### 5. 동작 확인
저장소 **Actions** 탭 → `weekly-outing` → **Run workflow**로 즉시 테스트 발송.
이후 매주 수요일 오전 8시에 자동으로 도착합니다.

## 로컬에서 미리보기 (전송 없이)
```bash
pip install -r requirements.txt
ANTHROPIC_API_KEY=... python -m src.generate --dry-run
```
