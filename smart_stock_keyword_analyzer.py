#!/usr/bin/env python3
"""
🚀 Smart Stock Keyword Analysis System
실행파일 기반 - 뉴스/공시 키워드 자동 분석 → 주가 연관성 학습 → 매수 신호
"""

import sqlite3
import json
import requests
from datetime import datetime, timedelta
from collections import Counter
import re
import hashlib
from pathlib import Path
import yfinance as yf
from bs4 import BeautifulSoup
import time

class StockKeywordAnalysisDB:
    """주식 키워드 분석 데이터베이스"""
    
    def __init__(self, db_path="/home/netizang/stock_keyword_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 1. 키워드 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY,
                keyword TEXT UNIQUE,
                category TEXT,
                frequency INTEGER DEFAULT 0,
                last_seen TIMESTAMP
            )
        ''')
        
        # 2. 뉴스/기사 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY,
                title TEXT,
                source TEXT,
                url TEXT UNIQUE,
                content TEXT,
                published_date TIMESTAMP,
                collected_date TIMESTAMP,
                keywords TEXT,
                hash_id TEXT UNIQUE
            )
        ''')
        
        # 3. 기업-키워드 관계 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS company_keywords (
                id INTEGER PRIMARY KEY,
                company_code TEXT,
                company_name TEXT,
                keyword TEXT,
                keyword_category TEXT,
                appearance_count INTEGER DEFAULT 1,
                last_updates TIMESTAMP
            )
        ''')
        
        # 4. 주가-키워드 연관성 분석 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS keyword_stock_correlation (
                id INTEGER PRIMARY KEY,
                keyword TEXT,
                company_code TEXT,
                company_name TEXT,
                date TIMESTAMP,
                price_before REAL,
                price_after REAL,
                price_change_pct REAL,
                correlation_score REAL,
                reliability_score REAL,
                analysis_status TEXT
            )
        ''')
        
        # 5. 학습 데이터 (예측 모델용)
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY,
                keyword TEXT,
                keyword_category TEXT,
                company_code TEXT,
                event_date TIMESTAMP,
                price_change_7day REAL,
                price_change_30day REAL,
                prediction_score REAL,
                actual_result TEXT,
                confidence_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 데이터베이스 초기화 완료")
    
    def extract_keywords(self, text, category="general"):
        """텍스트에서 핵심 키워드 추출 (NLP 기반)"""
        
        # 키워드 딕셔너리
        keyword_patterns = {
            "investment": [
                r"신(규)?투자", r"M&A", r"인수", r"합병", 
                r"투자", r"확대", r"진출", r"신사업",
                r"전략적.*투자", r"개발", r"착공", r"기공식"
            ],
            "technology": [
                r"AI", r"인공지능", r"반도체", r"칩", r"D\?램", 
                r"낸드", r"프로세서", r"GPU", r"NPU",
                r"5G", r"6G", r"통신", r"차세대"
            ],
            "product": [
                r"신제품", r"출시", r"론칭", r"공개", r"발표",
                r"출장", r"제품", r"서비스", r"생산"
            ],
            "financial": [
                r"실손", r"적자", r"흑자", r"수익", r"손실",
                r"매출", r"이익", r"배당", r"주가", r"상장",
                r"분할", r"분사", r"증자", r"감자"
            ],
            "personnel": [
                r"CEO", r"임원", r"대표", r"교체", r"퇴임",
                r"신임", r"승진", r"퇴직금", r"인사이동"
            ],
            "regulatory": [
                r"규제", r"승인", r"허가", r"인증", r"적격",
                r"부적격", r"위반", r"제재", r"과태료",
                r"조사", r"수거", r"리콜"
            ],
            "partnership": [
                r"협력", r"제휴", r"계약", r"양해각서", r"MOU",
                r"동맹", r"파트너", r"업체", r"공급"
            ],
            "market": [
                r"상승", r"하락", r"급등", r"급락", r"변동성",
                r"약세", r"강세", r"거래량", r"단가"
            ]
        }
        
        extracted = {}
        text_lower = text.lower()
        
        for category_name, patterns in keyword_patterns.items():
            found = []
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                found.extend(matches)
            
            if found:
                extracted[category_name] = list(set(found))
        
        return extracted
    
    def save_article(self, title, source, url, content, keywords_dict):
        """기사 저장"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        hash_id = hashlib.md5(url.encode()).hexdigest()
        
        try:
            c.execute('''
                INSERT INTO news_articles 
                (title, source, url, content, published_date, collected_date, keywords, hash_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, source, url, content,
                datetime.now(), datetime.now(),
                json.dumps(keywords_dict), hash_id
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def update_company_keywords(self, company_code, company_name, keywords_dict):
        """기업별 키워드 업데이트"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for category, keywords in keywords_dict.items():
            for keyword in keywords:
                try:
                    c.execute('''
                        INSERT INTO company_keywords 
                        (company_code, company_name, keyword, keyword_category, last_updates)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (company_code, company_name, keyword, category, datetime.now()))
                except sqlite3.IntegrityError:
                    c.execute('''
                        UPDATE company_keywords 
                        SET appearance_count = appearance_count + 1,
                            last_updates = ?
                        WHERE company_code = ? AND keyword = ?
                    ''', (datetime.now(), company_code, keyword))
        
        conn.commit()
        conn.close()
    
    def analyze_correlation(self, company_code, company_name):
        """키워드-주가 상관성 분석"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 해당 기업의 키워드 목록
        c.execute('''
            SELECT DISTINCT keyword, keyword_category FROM company_keywords
            WHERE company_code = ?
            ORDER BY appearance_count DESC
        ''', (company_code,))
        
        keywords = c.fetchall()
        
        results = []
        for keyword, category in keywords:
            # 키워드의 최근 5개 기사 수집 날짜 찾기
            c.execute('''
                SELECT collected_date FROM news_articles
                WHERE keywords LIKE ?
                ORDER BY collected_date DESC
                LIMIT 5
            ''', (f'%{keyword}%',))
            
            dates = [row[0] for row in c.fetchall()]
            
            # 주가 데이터 수집 (yfinance)
            try:
                ticker = yf.Ticker(f"{company_code}.KS")
                hist = ticker.history(period="3mo")
                
                if len(hist) > 0:
                    # 상관성 계산 (간단한 방식)
                    correlation_score = len(dates) / max(len(hist), 1)  # 키워드 빈도
                    
                    results.append({
                        "keyword": keyword,
                        "category": category,
                        "correlation_score": correlation_score,
                        "recent_appearances": len(dates)
                    })
            except:
                pass
        
        conn.close()
        
        # 상관성 높은 순서로 정렬
        results.sort(key=lambda x: x['correlation_score'], reverse=True)
        return results
    
    def get_keyword_statistics(self):
        """키워드 통계"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT keyword, keyword_category, SUM(appearance_count) as total
            FROM company_keywords
            GROUP BY keyword
            ORDER BY total DESC
            LIMIT 20
        ''')
        
        stats = c.fetchall()
        conn.close()
        
        return stats
    
    def export_report(self, output_file=None):
        """분석 보고서 생성"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_articles": 0,
            "total_keywords": 0,
            "top_keywords": [],
            "company_analysis": {}
        }
        
        # 기본 통계
        c.execute("SELECT COUNT(*) FROM news_articles")
        report["total_articles"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(DISTINCT keyword) FROM company_keywords")
        report["total_keywords"] = c.fetchone()[0]
        
        # 상위 키워드
        stats = self.get_keyword_statistics()
        report["top_keywords"] = [
            {"keyword": s[0], "category": s[1], "total_appearances": s[2]}
            for s in stats[:10]
        ]
        
        # 기업별 분석
        c.execute("SELECT DISTINCT company_code, company_name FROM company_keywords")
        companies = c.fetchall()
        
        for code, name in companies[:10]:  # 상위 10개 기업만
            correlation = self.analyze_correlation(code, name)
            report["company_analysis"][f"{code}_{name}"] = correlation[:5]
        
        conn.close()
        
        # 파일 저장 또는 출력
        if output_file is None:
            output_file = f"/home/netizang/cron_logs/keyword_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 보고서 저장: {output_file}")
        return report


def collect_news_before_market_open():
    """시장 개장 전(08:50까지) 뉴스 수집"""
    print("\n🔍 시장 개장 전 뉴스 수집 중...")
    
    db = StockKeywordAnalysisDB()
    
    # 샘플 뉴스 (실제로는 API에서 수집)
    sample_news = [
        {
            "title": "삼성전자, 신규 AI칩 개발 투자 확대",
            "source": "네이버",
            "url": "https://news.naver.com/samsung-ai-chip-001",
            "content": "삼성전자가 인공지능 반도체 개발에 대규모 신규투자를 단행하기로 결정했습니다."
        },
        {
            "title": "SK하이닉스, D램 가격 상승 수혜",
            "source": "다트",
            "url": "https://dart.fss.or.kr/sk-hynix-001",
            "content": "SK하이닉스가 D램 가격 상승으로 분기 실적이 흑자로 전환될 것으로 예상된다고 공시했습니다."
        },
        {
            "title": "LG전자, OLED 패널 신제품 출시",
            "source": "경제신문",
            "url": "https://biz.chosun.com/lg-oled-001",
            "content": "LG전자가 차세대 OLED 패널 기술을 적용한 신제품을 출시하기로 공개했습니다."
        },
        {
            "title": "현대차, 전기차 배터리 공급협력 계약",
            "source": "인베스팅닷컴",
            "url": "https://investing.com/hyundai-battery-001",
            "content": "현대자동차가 글로벌 배터리 기업과 장기 공급 계약을 체결했습니다."
        },
        {
            "title": "포스코, 반도체 소재 시장 진출",
            "source": "네이버",
            "url": "https://news.naver.com/posco-semicon-001",
            "content": "포스코가 반도체 제조용 특수강 시장으로 전략적 진출을 공표했습니다."
        }
    ]
    
    for news in sample_news:
        # 키워드 추출
        keywords = db.extract_keywords(news["content"])
        
        # 기사 저장
        db.save_article(
            news["title"],
            news["source"],
            news["url"],
            news["content"],
            keywords
        )
        
        print(f"✅ {news['title']}")
        print(f"   키워드: {list(keywords.keys())}")
        
        # 기업별 키워드 업데이트
        company_mapping = {
            "삼성전자": "005930",
            "SK하이닉스": "000660",
            "LG전자": "066570",
            "현대차": "005380",
            "포스코": "005490"
        }
        
        for company, code in company_mapping.items():
            if company.lower() in news["content"].lower():
                db.update_company_keywords(code, company, keywords)
    
    return db


def generate_analysis_report(db):
    """분석 보고서 생성"""
    print("\n📊 키워드-주가 상관성 분석 중...")
    
    report = db.export_report()
    
    print("\n" + "="*80)
    print("📈 KEYWORD-STOCK CORRELATION ANALYSIS REPORT")
    print("="*80)
    print(f"📅 {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}")
    print()
    
    print(f"📊 통계")
    print(f"  • 수집 기사: {report['total_articles']}개")
    print(f"  • 추출 키워드: {report['total_keywords']}개")
    print()
    
    print(f"🔑 상위 키워드 (출현 빈도)")
    for i, kw in enumerate(report['top_keywords'][:10], 1):
        print(f"  {i}. {kw['keyword']} [{kw['category']}]: {kw['total_appearances']}회")
    print()
    
    print(f"🏢 기업별 핵심 키워드 분석")
    for company, keywords in list(report['company_analysis'].items())[:5]:
        print(f"\n  📌 {company}")
        for kw in keywords:
            score = kw['correlation_score']
            bar = "█" * int(score * 10)
            print(f"     • {kw['keyword']}: {bar} ({score:.2%})")
    
    print("\n" + "="*80)
    print("✅ 분석 완료 - 데이터베이스에 저장되었습니다")
    print("="*80)


def main():
    """메인 프로세스"""
    print("\n" + "█"*80)
    print("🚀 SMART STOCK KEYWORD ANALYSIS SYSTEM v1.0")
    print("█"*80)
    
    # 1. 시장 개장 전 뉴스 수집
    db = collect_news_before_market_open()
    
    # 2. 키워드 분석
    generate_analysis_report(db)
    
    print("\n💡 다음 단계:")
    print("  1. 시장 개장 후 (10:00) 주가 데이터 수집")
    print("  2. 키워드-주가 상관성 계산")
    print("  3. 학습 데이터 업데이트")
    print("  4. 예측 모델 학습")
    print("\n📱 Telegram 전송:")
    print("  bash /home/netizang/send_keyword_analysis.sh")


if __name__ == "__main__":
    main()
