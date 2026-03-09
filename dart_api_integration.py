#!/usr/bin/env python3
"""
DART API 실시간 공시 수집 시스템
- 금융감독원 DART API 기반 실시간 공시 모니터링
- 한국 주요 기업의 공시 정보 자동 수집
- 핵심 키워드 추출 및 분석
- SQLite 데이터베이스 저장 및 Telegram 알림
"""

import requests
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import hashlib
import telegram
import asyncio
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================
# ⚙️ 설정
# =========================================

# DART API 설정
DART_API_KEY = "1d74742e16516a1e6f07d71299e311535d056595"  # API 키
DART_BASE_URL = "https://opendart.fss.or.kr/api"

# Telegram 봇 설정
TELEGRAM_BOT_TOKEN = "8710681704:AAFYHBInLWskpxgWns3j6FUBKgTy3HHzfq8"
TELEGRAM_CHAT_ID = 8688208712
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# 모니터링 대상 기업 (한국 주요 기업)
TARGET_COMPANIES = {
    "005930": "삼성전자",          # Samsung Electronics
    "000660": "SK하이닉스",         # SK Hynix
    "066570": "LG전자",            # LG Electronics
    "005380": "현대차",            # Hyundai Motors
    "005490": "포스코",            # POSCO
    "035720": "카카오",            # Kakao
    "051910": "LG화학",            # LG Chem
    "012330": "현대모비스",        # Hyundai Mobis
    "003550": "LG",                # LG
    "015760": "한국전력",          # Korea Electric Power
}

# 중요도별 공시 유형 코드
IMPORTANT_DISCLOSURES = {
    "20": "주요사항",
    "21": "공시정정",
    "24": "자기주식취득",
    "25": "배당",
    "30": "임원·직원관련",
    "40": "합병·분할",
    "60": "자산양수도",
}

# 데이터베이스 설정
DB_PATH = "/home/netizang/dart_disclosures.db"

# =========================================
# 데이터베이스 설정
# =========================================

class DARTDatabase:
    """DART 공시 데이터베이스 관리"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 공시 정보 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disclosures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disclosure_id TEXT UNIQUE NOT NULL,
                company_code TEXT NOT NULL,
                company_name TEXT NOT NULL,
                disclosure_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                disclosure_date TEXT NOT NULL,
                report_date TEXT NOT NULL,
                url TEXT,
                importance_score INTEGER DEFAULT 50,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        ''')
        
        # 공시 분석 결과 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disclosure_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disclosure_id TEXT NOT NULL UNIQUE,
                category TEXT,
                keywords TEXT,
                sentiment TEXT,
                potential_impact TEXT,
                correlation_score REAL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (disclosure_id) REFERENCES disclosures(disclosure_id)
            )
        ''')
        
        # 공시 처리 로그 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_code TEXT,
                last_collection_date TEXT,
                total_collected INTEGER,
                error_message TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✓ DART 데이터베이스 초기화 완료")
    
    def save_disclosure(self, disclosure_data: Dict) -> bool:
        """공시 정보 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # DART API 필드맵핑
            title = disclosure_data.get('report_nm', '').strip() or disclosure_data.get('subject', 'N/A')
            rcept_dt = disclosure_data.get('rcept_dt', '')
            
            cursor.execute('''
                INSERT OR IGNORE INTO disclosures 
                (disclosure_id, company_code, company_name, disclosure_type, 
                 title, content, disclosure_date, report_date, url, 
                 importance_score, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                disclosure_data.get('rcept_no'),
                disclosure_data.get('corp_code') or disclosure_data.get('stock_code'),
                disclosure_data.get('corp_name'),
                disclosure_data.get('report_nm', '')[:50],
                title,
                disclosure_data.get('content', ''),
                rcept_dt,
                disclosure_data.get('report_date', rcept_dt),
                f"https://dart.fss.or.kr/dsab001/viewer.do?rcept_no={disclosure_data.get('rcept_no')}",
                disclosure_data.get('importance_score', 50),
                disclosure_data.get('keywords', '')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"✗ 공시 저장 실패: {e}")
            return False

# =========================================
# DART API 클라이언트
# =========================================

class DARTClient:
    """DART API 클라이언트"""
    
    def __init__(self, api_key: str = DART_API_KEY):
        self.api_key = api_key
        self.base_url = DART_BASE_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'
        }
    
    def get_recent_disclosures(self, company_code: str, days: int = 1) -> List[Dict]:
        """최근 공시 정보 조회"""
        try:
            # 최근 N일 공시 조회
            today = datetime.now()
            from_date = (today - timedelta(days=days)).strftime('%Y%m%d')
            to_date = today.strftime('%Y%m%d')
            
            # DART API 엔드포인트 (정정됨)
            url = f"{self.base_url}/list.json"
            
            params = {
                'crtfc_key': self.api_key,
                'corp_code': company_code,
                'start_dt': from_date,
                'end_dt': to_date,
                'last_reprt_at': 'Y',
                'page_count': 100,
            }
            
            logger.info(f"🔍 DART API 조회 중: {company_code} ({from_date} ~ {to_date})")
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == '000':  # 성공
                    documents = data.get('list', [])
                    logger.info(f"✓ {len(documents)}개 공시 조회 완료")
                    return documents
                else:
                    logger.warning(f"⚠️ DART API 오류: {data.get('message')}")
                    return []
            else:
                logger.error(f"✗ HTTP {response.status_code}: {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"✗ DART API 조회 실패: {e}")
            return []
    
    def get_disclosure_content(self, rcept_no: str) -> Optional[str]:
        """공시 상세 내용 조회"""
        try:
            # DART 웹에서 직접 조회 (API 제한 우회)
            url = f"https://dart.fss.or.kr/dsab001/viewer.do?rcept_no={rcept_no}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 공시 내용 추출
                content_div = soup.find('div', {'id': 'doc_body'})
                if content_div:
                    text = content_div.get_text(strip=True)
                    return text[:2000]  # 처음 2000자
            
            return None
        except Exception as e:
            logger.error(f"✗ 공시 내용 조회 실패: {e}")
            return None

# =========================================
# 공시 분석 엔진
# =========================================

class DisclosureAnalyzer:
    """공시 분석 및 키워드 추출"""
    
    # 키워드 패턴 (7가지 카테고리)
    KEYWORD_PATTERNS = {
        "investment": {
            "keywords": ["신규투자", "M&A", "인수", "합병", "확대", "진출", "사업확장", "투자", "개발"],
            "importance": 8
        },
        "technology": {
            "keywords": ["AI", "반도체", "칩", "D램", "5G", "차세대", "인공지능", "수소", "이차전지"],
            "importance": 9
        },
        "product": {
            "keywords": ["신제품", "출시", "론칭", "공개", "발표", "개발완료", "승인", "인증"],
            "importance": 7
        },
        "financial": {
            "keywords": ["실손", "적자", "흑자", "수익상승", "배당", "주가", "주식분할", "채권"],
            "importance": 8
        },
        "personnel": {
            "keywords": ["CEO", "임원", "교체", "퇴임", "인사이동", "신임"],
            "importance": 6
        },
        "regulatory": {
            "keywords": ["규제", "승인", "허가", "제재", "조사", "과징금", "시정명령"],
            "importance": 9
        },
        "partnership": {
            "keywords": ["협력", "제휴", "계약", "MOU", "동맹", "공동개발", "공급계약"],
            "importance": 7
        }
    }
    
    @classmethod
    def extract_keywords(cls, text: str) -> Dict[str, list]:
        """텍스트에서 핵심 키워드 추출"""
        keywords = {}
        text_lower = text.lower()
        
        for category, data in cls.KEYWORD_PATTERNS.items():
            category_keywords = []
            for keyword in data["keywords"]:
                pattern = re.compile(keyword, re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    category_keywords.append({
                        "keyword": keyword,
                        "count": len(matches),
                        "importance": data["importance"]
                    })
            
            if category_keywords:
                keywords[category] = category_keywords
        
        return keywords
    
    @classmethod
    def calculate_importance(cls, disclosure: Dict) -> int:
        """공시 중요도 계산"""
        score = 50  # 기본 점수
        
        # 공시 유형별 가중치
        report_type = disclosure.get('report_nm', '')
        if '주요' in report_type:
            score += 20
        if '정정' in report_type:
            score += 10
        if '자기주식' in report_type:
            score += 15
        if '배당' in report_type:
            score += 15
        if '임원' in report_type:
            score += 10
        
        # 제목에 포함된 키워드로 가중치 조정
        title = disclosure.get('subject', '').lower()
        keywords_impact = {
            'ai': 15, '반도체': 15, '수소': 12, 
            '배당': 10, '신제품': 10, '협력': 8
        }
        
        for keyword, weight in keywords_impact.items():
            if keyword in title:
                score += weight
        
        return min(score, 100)  # 최대 100
    
    @classmethod
    def analyze(cls, disclosure: Dict) -> Dict:
        """공시 통합 분석"""
        title = disclosure.get('subject', '')
        content = disclosure.get('content', '') or ''
        full_text = f"{title} {content}"
        
        keywords = cls.extract_keywords(full_text)
        importance_score = cls.calculate_importance(disclosure)
        
        # 상관성 점수 계산 (향후 ML 모델 사용 예정)
        correlation_score = 0.0
        if keywords:
            num_categories = len(keywords)
            correlation_score = min(num_categories * 0.25, 1.0)
        
        return {
            "keywords": keywords,
            "importance_score": importance_score,
            "correlation_score": correlation_score,
            "has_significant_keywords": importance_score > 60
        }

# =========================================
# Telegram 알림
# =========================================

async def send_telegram_alert(disclosure: Dict, analysis: Dict):
    """Telegram으로 공시 알림 전송"""
    try:
        importance_emoji = "🔴" if analysis["importance_score"] > 80 else "🟡" if analysis["importance_score"] > 60 else "🟢"
        
        # 메시지 구성
        message = f"{importance_emoji} *{disclosure.get('corp_name', 'N/A')}* 공시\n\n"
        message += f"*공시유형*: {disclosure.get('report_nm', 'N/A')}\n"
        message += f"*제목*: {disclosure.get('subject', 'N/A')[:60]}\n"
        message += f"*중요도*: {analysis['importance_score']}/100\n"
        
        # 추출된 키워드
        if analysis.get("keywords"):
            keywords_str = ", ".join([
                f"{k}" for cat_keywords in analysis["keywords"].values() 
                for k in [kw.get("keyword") for kw in cat_keywords]
            ])
            message += f"*키워드*: {keywords_str[:100]}\n"
        
        message += f"*공시일*: {disclosure.get('rcept_dt', 'N/A')}\n"
        
        # Telegram 전송
        await telegram_bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✓ Telegram 알림 전송: {disclosure.get('corp_name', 'N/A')}")
    
    except Exception as e:
        logger.error(f"✗ Telegram 알림 실패: {e}")

# =========================================
# 메인 실행
# =========================================

def run_dart_collection():
    """DART 공시 수집 및 분석 실행"""
    logger.info("=" * 70)
    logger.info("🚀 DART API 공시 수집 시작")
    logger.info("=" * 70)
    
    # 데이터베이스 초기화
    db = DARTDatabase()
    dart_client = DARTClient()
    
    # 각 기업별 공시 수집
    for company_code, company_name in TARGET_COMPANIES.items():
        logger.info(f"\n📊 {company_name} ({company_code}) 공시 조회 중...")
        
        try:
            # 최근 1일 공시 조회
            disclosures = dart_client.get_recent_disclosures(company_code, days=1)
            
            if not disclosures:
                logger.info(f"ℹ️  {company_name}: 새로운 공시 없음")
                continue
            
            # 각 공시 처리
            for disclosure in disclosures:
                # 공시 데이터 완성
                disclosure_id = disclosure.get('rcept_no')
                disclosure['corp_code'] = company_code
                disclosure['corp_name'] = company_name
                
                # 공시 내용 조회 (선택사항 - 시간 소요)
                # disclosure_content = dart_client.get_disclosure_content(disclosure_id)
                # disclosure['content'] = disclosure_content
                
                # 분석 실행
                analysis = DisclosureAnalyzer.analyze(disclosure)
                disclosure['importance_score'] = analysis['importance_score']
                disclosure['keywords'] = json.dumps(analysis['keywords'], ensure_ascii=False)
                
                # 데이터베이스 저장 (모든 공시)
                if db.save_disclosure(disclosure):
                    logger.info(f"✓ 저장됨: {disclosure.get('subject', 'N/A')[:40]} (중요도: {analysis['importance_score']})")
                    
                    # 중요 공시는 Telegram 알림
                    if analysis['importance_score'] > 70:
                        asyncio.run(send_telegram_alert(disclosure, analysis))
        
        except Exception as e:
            logger.error(f"✗ {company_name} 처리 중 오류: {e}")
            continue
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ DART API 공시 수집 완료")
    logger.info("=" * 70)

if __name__ == "__main__":
    run_dart_collection()
