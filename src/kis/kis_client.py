"""
한국투자증권 OpenAPI 클라이언트
모의투자 계좌를 통한 실제 주문 처리
"""
import os
import time
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("kis_client")


class KISClient:
    """한국투자증권 OpenAPI 클라이언트"""
    
    # 모의투자 URL
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
    
    def __init__(self, app_key: str, app_secret: str, account_no: str, mock: bool = True):
        """
        Args:
            app_key: APP KEY
            app_secret: APP SECRET
            account_no: 계좌번호 (CANO-ACNT_PRDT_CD, 예: 12345678-01)
            mock: 모의투자 여부 (True: 모의투자, False: 실전투자)
        """
        self.app_key = app_key
        self.app_secret = app_secret
        
        # 계좌번호 파싱
        parts = account_no.split("-")
        if len(parts) != 2:
            raise ValueError(f"계좌번호 형식 오류: {account_no} (예: 12345678-01)")
        
        self.cano = parts[0]  # 계좌번호 앞자리
        self.acnt_prdt_cd = parts[1]  # 계좌번호 뒷자리
        
        self.mock = mock
        self.base_url = self.BASE_URL if mock else "https://openapi.koreainvestment.com:9443"
        
        # Access Token
        self.access_token = None
        self.token_expired_at = None
        
        # 초기 인증
        self._get_access_token()
    
    def _get_access_token(self):
        """Access Token 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        expires_in = int(data["expires_in"])  # 초
        self.token_expired_at = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info(f"✅ Access Token 발급 완료 (만료: {self.token_expired_at})")
    
    def _ensure_token(self):
        """Token 유효성 확인 및 갱신"""
        if not self.access_token or datetime.now() >= self.token_expired_at:
            self._get_access_token()
    
    def _make_request(self, method: str, path: str, headers: Dict, body: Optional[Dict] = None) -> Dict:
        """공통 요청 메서드"""
        self._ensure_token()
        
        # 공통 헤더
        headers["authorization"] = f"Bearer {self.access_token}"
        headers["appkey"] = self.app_key
        headers["appsecret"] = self.app_secret
        
        url = f"{self.base_url}{path}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=body)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "tr_id": "FHKST01010100",  # 주식현재가 시세
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장구분 (J: 주식)
            "FID_INPUT_ISCD": ticker,
        }
        
        try:
            data = self._make_request("GET", path, headers, params)
            
            if data["rt_cd"] == "0":
                return float(data["output"]["stck_prpr"])  # 현재가
            else:
                logger.error(f"현재가 조회 실패: {data['msg1']}")
                return None
        except Exception as e:
            logger.error(f"현재가 조회 에러: {e}")
            return None
    
    def get_balance(self) -> Dict:
        """계좌 잔고 조회"""
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "tr_id": "VTTC8434R" if self.mock else "TTTC8434R",  # 모의투자/실전투자
        }
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",  # 시간외단일가여부
            "OFL_YN": "",  # 오프라인여부
            "INQR_DVSN": "02",  # 조회구분 (01: 대출일별, 02: 종목별)
            "UNPR_DVSN": "01",  # 단가구분
            "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "01",  # 처리구분 (00: 전일, 01: 금일)
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        
        try:
            data = self._make_request("GET", path, headers, params)
            
            if data["rt_cd"] != "0":
                logger.error(f"잔고 조회 실패: {data['msg1']}")
                return {"cash": 0, "holdings": {}}
            
            # 예수금 (현금)
            output2 = data.get("output2", [{}])[0]
            cash = float(output2.get("dnca_tot_amt", 0))  # 예수금총액
            
            # 보유 종목
            holdings = {}
            for item in data.get("output1", []):
                ticker = item["pdno"]  # 종목코드
                name = item["prdt_name"]  # 종목명
                shares = int(item["hldg_qty"])  # 보유수량
                avg_price = float(item["pchs_avg_pric"])  # 매입평균가격
                
                if shares > 0:
                    holdings[ticker] = {
                        "name": name,
                        "shares": shares,
                        "avg_price": avg_price,
                    }
            
            return {
                "cash": cash,
                "holdings": holdings,
            }
            
        except Exception as e:
            logger.error(f"잔고 조회 에러: {e}")
            return {"cash": 0, "holdings": {}}
    
    def order_buy(self, ticker: str, shares: int, price: Optional[float] = None) -> bool:
        """매수 주문
        
        Args:
            ticker: 종목코드
            shares: 매수 수량
            price: 지정가 (None: 시장가)
        
        Returns:
            성공 여부
        """
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "tr_id": "VTTC0802U" if self.mock else "TTTC0802U",  # 주식현금매수주문
        }
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": ticker,  # 종목코드
            "ORD_DVSN": "01" if price else "01",  # 주문구분 (00: 지정가, 01: 시장가)
            "ORD_QTY": str(shares),  # 주문수량
            "ORD_UNPR": str(int(price)) if price else "0",  # 주문단가
        }
        
        try:
            data = self._make_request("POST", path, headers, body)
            
            if data["rt_cd"] == "0":
                logger.info(f"✅ 매수 주문 성공: {ticker} {shares}주")
                return True
            else:
                logger.error(f"❌ 매수 주문 실패: {data['msg1']}")
                return False
                
        except Exception as e:
            logger.error(f"매수 주문 에러: {e}")
            return False
    
    def order_sell(self, ticker: str, shares: int, price: Optional[float] = None) -> bool:
        """매도 주문
        
        Args:
            ticker: 종목코드
            shares: 매도 수량
            price: 지정가 (None: 시장가)
        
        Returns:
            성공 여부
        """
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "tr_id": "VTTC0801U" if self.mock else "TTTC0801U",  # 주식현금매도주문
        }
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": ticker,  # 종목코드
            "ORD_DVSN": "01" if price else "01",  # 주문구분 (00: 지정가, 01: 시장가)
            "ORD_QTY": str(shares),  # 주문수량
            "ORD_UNPR": str(int(price)) if price else "0",  # 주문단가
        }
        
        try:
            data = self._make_request("POST", path, headers, body)
            
            if data["rt_cd"] == "0":
                logger.info(f"✅ 매도 주문 성공: {ticker} {shares}주")
                return True
            else:
                logger.error(f"❌ 매도 주문 실패: {data['msg1']}")
                return False
                
        except Exception as e:
            logger.error(f"매도 주문 에러: {e}")
            return False


def test_kis_client():
    """KIS 클라이언트 테스트"""
    # 환경변수에서 인증 정보 로드
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    account_no = os.getenv("KIS_ACCOUNT_NO")
    
    if not all([app_key, app_secret, account_no]):
        print("❌ 환경변수 설정 필요: KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO")
        return
    
    # 클라이언트 생성
    client = KISClient(app_key, app_secret, account_no, mock=True)
    
    # 잔고 조회
    print("\n1️⃣ 잔고 조회")
    balance = client.get_balance()
    print(f"현금: {balance['cash']:,.0f}원")
    for ticker, holding in balance['holdings'].items():
        print(f"- {holding['name']}({ticker}): {holding['shares']}주 @ {holding['avg_price']:,.0f}원")
    
    # 현재가 조회
    print("\n2️⃣ 현재가 조회")
    price = client.get_current_price("005930")
    if price:
        print(f"삼성전자 현재가: {price:,.0f}원")
    
    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    test_kis_client()
