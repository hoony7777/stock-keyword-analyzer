# 🚀 Smart Stock Keyword Analysis System
## 스마트 주식 키워드 분석 자동화 시스템

> 뉴스/공시에서 추출한 핵심 키워드와 주가 상승의 연관성을 자동으로 분석, 학습하여 향후 매수 신호로 활용하는 AI 기반 거래 보조 시스템

---

## ✨ 주요 기능

### 1🔍 **자동 키워드 추출**
- 08:50 이전의 뉴스/공시/기사에서 **자동으로 핵심 키워드 추출**
- 7가지 카테고리로 자동 분류:
  - 💼 **Investment** (신투자, M&A, 인수, 합병)
  - 🔧 **Technology** (AI, 반도체, 5G, 통신)
  - 🎯 **Product** (신제품, 출시, 론칭)
  - 💰 **Financial** (수익, 손실, 배당, 주가)
  - 👥 **Personnel** (CEO, 임원, 인사이동)
  - ⚖️ **Regulatory** (규제, 승인, 제재)
  - 🤝 **Partnership** (협력, 제휴, 계약)

### 2📊 **데이터베이스 자동화**
- SQLite 기반 다중 테이블 구조:
  - `keywords`: 핵심 키워드 저장
  - `news_articles`: 수집 기사 저장
  - `company_keywords`: 기업-키워드 매핑
  - `keyword_stock_correlation`: 주가 상관성 분석
  - `learning_data`: 머신러닝 데이터

### 3📈 **상관성 분석 & 학습**
- 키워드 출현 → 장개장 후 주가 추적
- 자동 상관성 점수 계산
- 과거 데이터 기반 신뢰도 평가
- 예측 모델 학습 (향후 매수 신호 생성)

### 4💬 **Telegram 자동 알림**
- 08:50 전: 핵심 키워드 분석 결과 전송
- 10:00 후: 키워드-주가 연관성 분석 결과
- 실시간 주가 데이터 함께 제공

---

## 🛠️ 설치 및 사용

### **방법 1: 실행파일 (Windows/Linux/Mac)**

#### 다운로드
```bash
# GitHub에서 최신 버전 다운로드
wget https://github.com/YOUR_USERNAME/stock-keyword-analyzer/releases/download/v1.0/stock_keyword_analyzer
chmod +x stock_keyword_analyzer

# 또는 macOS
curl -O https://github.com/YOUR_USERNAME/stock-keyword-analyzer/releases/download/v1.0/stock_keyword_analyzer_mac
chmod +x stock_keyword_analyzer_mac
```

#### 실행
```bash
# Linux/Mac
./stock_keyword_analyzer

# Windows
stock_keyword_analyzer.exe
```

### **방법 2: 소스코드 (Python)**

#### 요구 사항
- Python 3.8+
- pip

#### 설치
```bash
# 저장소 클론
git clone https://github.com/YOUR_USERNAME/stock-keyword-analyzer.git
cd stock-keyword-analyzer

# 의존성 설치
pip install -r requirements.txt
```

#### 실행
```bash
python3 smart_stock_keyword_analyzer.py
```

---

## 📊 프로세스 플로우

```
08:00 - 08:50 (장전 기사 수집)
    ↓
뉴스/공시/기사에서 핵심 키워드 추출
    ↓
카테고리 자동 분류 (7가지)
    ↓
기업-키워드 매핑 & DB 저장
    ↓
📱 Telegram 알림 (핵심 키워드)
    ↓
        
10:00 - 15:30 (장중 주가 추적)
    ↓
키워드별 기업 주가 수집
    ↓
상관성 점수 계산
    ↓
신뢰도 평가 (신뢰도 < 60% 제외)
    ↓
📱 Telegram 알림 (주가 상관성)
    ↓

데이터베이스 누적 저장
    ↓
머신러닝 모델 학습
    ↓
다음 거래일: 유사 키워드 감지 시 매수 신호
```

---

## 📚 데이터베이스 스키마

### **keywords (핵심 키워드 테이블)**
```
id | keyword | category | frequency | last_seen
```

### **news_articles (수집 기사)**
```
id | title | source | url | content | published_date | collected_date | keywords (JSON) | hash_id
```

### **company_keywords (기업-키워드 매핑)**
```
id | company_code | company_name | keyword | keyword_category | appearance_count | last_updates
```

### **keyword_stock_correlation (상관성 분석)**
```
id | keyword | company_code | company_name | date | price_before | price_after | 
price_change_pct | correlation_score | reliability_score | analysis_status
```

### **learning_data (학습 데이터)**
```
id | keyword | keyword_category | company_code | event_date | price_change_7day | 
price_change_30day | prediction_score | actual_result | confidence_score
```

---

## 🎯 데이터 분석 예시

### **삼성전자 (005930)**
| 키워드 | 카테고리 | 출현 빈도 | 주가 상승률 | 신뢰도 |
|--------|---------|---------|----------|--------|
| **반도체** | Technology | 15회 | +2.3% | 92% |
| **신투자** | Investment | 8회 | +1.8% | 87% |
| **AI칩** | Technology | 5회 | +3.1% | 94% |

### **SK 하이닉스 (000660)**
| 키워드 | 카테고리 | 출현 빈도 | 주가 상승률 | 신뢰도 |
|--------|---------|---------|----------|--------|
| **D램** | Technology | 12회 | +1.9% | 85% |
| **가격상승** | Market | 7회 | +2.5% | 89% |
| **수익** | Financial | 6회 | +1.2% | 78% |

---

## 💾 파일 구조

```
stock-keyword-analyzer/
├── smart_stock_keyword_analyzer.py    # 메인 소스코드
├── requirements.txt                    # Python 의존성
├── README.md                           # 이 파일
├── LICENSE                             # MIT License
├── bin/
│   ├── stock_keyword_analyzer          # Linux 실행파일
│   ├── stock_keyword_analyzer_win.exe  # Windows 실행파일
│   └── stock_keyword_analyzer_mac      # macOS 실행파일
├── database/
│   └── stock_keyword_analysis.db       # SQLite 데이터베이스
└── reports/
    ├── keyword_analysis_report_*.json  # 일일 분석 보고서
    └── correlation_analysis_*.json     # 상관성 분석 결과
```

---

## 🔧 설정

### **1. Telegram 알림 설정**

`.env` 파일 생성:
```bash
BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
```

### **2. 자동 실행 (Cron)**

매일 08:00에 자동 실행:
```bash
0 8 * * 1-5 /home/netizang/bin/stock_keyword_analyzer
```

매일 10:00에 주가 추적:
```bash
0 10 * * 1-5 /home/netizang/bin/stock_keyword_analyzer
```

---

## 📊 Telegram 알림 예시

### **08:50 도착 메시지**
```
🚀 Stock Keyword Analysis Report
2026년 03월 09일 08:50

🔑 TODAY'S TOP KEYWORDS:
1. 반도체 [Technology]: 4회
2. 신투자 [Investment]: 3회
3. AI칩 [Technology]: 2회

🏢 COMPANY ANALYSIS:
📌 삼성전자 (005930)
  • AI칩 개발 → 주가 +3.1%
  • 반도체 투자 → 주가 +2.3%

📌 SK하이닉스 (000660)
  • D램 가격 상승 → 주가 +2.5%
```

### **10:30 도착 메시지**
```
📈 Post-Market Keyword Correlation
2026년 03월 09일 10:30

✅ HIGH CORRELATION (신뢰도 > 85%):
• 삼성전자: AI칩 (+3.1%) - 신뢰도 94% ✨
• SK하이닉스: D램 (+2.5%) - 신뢰도 89% ✨

⚠️ MEDIUM CORRELATION (신뢰도 60-85%):
• LG전자: 신제품 (+1.2%) - 신뢰도 72%
```

---

## 🚀 향후 업그레이드

- [ ] **NLP 고도화**: 감정 분석 (긍정/부정/중립) 추가
- [ ] **머신러닝**: 예측 모델 (XGBoost, LSTM) 적용
- [ ] **리얼타임 API**: Naver/DART API 통합
- [ ] **포트폴리오 매니저**: 자동 매수/매도 신호
- [ ] **모바일 앱**: iOS/Android 앱
- [ ] **클라우드 배포**: AWS/GCP 클라우드 지원

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🤝 기여

Pull Request 환영합니다! 

## 📧 연락

버그 보고나 제안: [GitHub Issues](https://github.com/YOUR_USERNAME/stock-keyword-analyzer/issues)

---

**⭐ 이 프로젝트가 도움이 되셨다면 Star를 눌러주세요!**

> 🎉  **2026년 3월 9일** - v1.0 첫 배포
> - 핵심 키워드 자동 추출
> - 7가지 카테고리 분류
> - 주가 상관성 분석
> - SQLite 데이터베이스
> - Telegram 알림 통합
