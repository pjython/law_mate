from core.config import get_settings
from core.logging.config import get_logger
import requests
from typing import List, Dict, Any, Optional
from services.collector.constants import LawApiPath
import time

logger = get_logger(__name__)


class LawApi:
    """
    법제처 API를 통한 법률 문서 수집 클래스
    법령, 판례 등을 검색하고 수집하는 기능을 제공합니다.
    """
    # TODO Task 구현 필요

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "http://www.law.go.kr/DRF/lawSearch.do"
        self.user_id = self.settings.LAW_API_USER_ID
        self.response_type = "JSON"
        self.session = requests.Session()  # 세션 재사용으로 성능 향상

        logger.info(f"🏛️ 법제처 API 클라이언트 초기화 (사용자 ID: {self.user_id})")

    def get_law_list(
        self,
        search_keyword: str = "",
        page: int = 1,
        display: int = 20,
        target: str = "law",
        raise_for_status: bool = True,
    ) -> Dict[str, Any]:
        """
        법령 목록 조회

        Args:
            search_keyword: 검색 키워드 (빈 문자열이면 전체 조회)
            page: 페이지 번호 (1부터 시작)
            display: 페이지당 표시 건수 (최대 100)
            target: 검색 대상 (law: 법령, prec: 판례)
            raise_for_status: HTTP 오류 시 예외 발생 여부

        Returns:
            API 응답 JSON 데이터
        """
        try:
            logger.info(f"📋 법령 목록 조회 - 키워드: '{search_keyword}', 페이지: {page}, 건수: {display}")

            params = {
                "OC": self.user_id,
                "target": target,
                "type": self.response_type,
                "search": 2,  # 2: 법령명 검색
                "page": page,
                "display": min(display, 100),  # 최대 100건으로 제한
            }

            # 검색 키워드가 있으면 추가
            if search_keyword.strip():
                params["query"] = search_keyword.strip()

            response = self.session.get(self.base_url, params=params, timeout=30)

            if raise_for_status:
                response.raise_for_status()

            result = response.json()

            # 응답 데이터 검증
            if "LawSearch" in result:
                total_count = result["LawSearch"].get("totalCnt", 0)
                current_page = result["LawSearch"].get("page", page)
                logger.info(f"✅ 법령 목록 조회 성공 - 총 {total_count}건, 현재 페이지: {current_page}")
            else:
                logger.warning("⚠️ 예상과 다른 응답 형식입니다")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 법령 목록 조회 실패 - 네트워크 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ 법령 목록 조회 실패 - 일반 오류: {str(e)}")
            raise

    def get_law_detail(self, law_id: str, raise_for_status: bool = True) -> Dict[str, Any]:
        """
        특정 법령의 상세 내용 조회

        Args:
            law_id: 법령 ID
            raise_for_status: HTTP 오류 시 예외 발생 여부

        Returns:
            법령 상세 정보 JSON 데이터
        """
        try:
            logger.info(f"📄 법령 상세 조회 - ID: {law_id}")

            params = {
                "OC": self.user_id,
                "target": "law",
                "type": self.response_type,
                "ID": law_id,
            }

            response = self.session.get(self.base_url, params=params, timeout=30)

            if raise_for_status:
                response.raise_for_status()

            result = response.json()
            logger.info(f"✅ 법령 상세 조회 성공 - ID: {law_id}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 법령 상세 조회 실패 - 네트워크 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ 법령 상세 조회 실패 - 일반 오류: {str(e)}")
            raise

    def search_laws_by_keywords(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """
        키워드 목록으로 관련 법령 검색

        Args:
            keywords: 검색할 키워드 목록
            max_results: 최대 결과 수

        Returns:
            검색된 법령 목록
        """
        try:
            logger.info(f"🔍 키워드 기반 법령 검색 - 키워드: {keywords}, 최대 결과: {max_results}")

            all_laws = []
            seen_law_ids = set()  # 중복 제거용

            for keyword in keywords:
                if not keyword.strip():
                    continue

                logger.debug(f"🔎 키워드 검색 중: '{keyword}'")

                # 페이지별로 검색 (API 제한 고려)
                page = 1
                while len(all_laws) < max_results:
                    try:
                        result = self.get_law_list(
                            search_keyword=keyword,
                            page=page,
                            display=min(20, max_results - len(all_laws)),
                            raise_for_status=False,
                        )

                        # 응답 데이터 파싱
                        if "LawSearch" not in result or "law" not in result["LawSearch"]:
                            logger.debug(f"'{keyword}' 검색 결과 없음")
                            break

                        laws = result["LawSearch"]["law"]
                        if not laws:
                            break

                        # 중복 제거하며 추가
                        for law in laws:
                            law_id = law.get("법령ID", "")
                            if law_id and law_id not in seen_law_ids:
                                seen_law_ids.add(law_id)
                                law["검색키워드"] = keyword  # 어떤 키워드로 찾았는지 기록
                                all_laws.append(law)

                                if len(all_laws) >= max_results:
                                    break

                        page += 1
                        time.sleep(0.1)  # API 호출 간격 조절

                    except Exception as e:
                        logger.warning(f"⚠️ 키워드 '{keyword}' 검색 중 오류: {str(e)}")
                        break

                if len(all_laws) >= max_results:
                    break

            logger.info(f"✅ 키워드 기반 검색 완료 - 총 {len(all_laws)}개 법령 발견")
            return all_laws[:max_results]

        except Exception as e:
            logger.error(f"❌ 키워드 기반 법령 검색 실패: {str(e)}")
            raise

    def collect_law_documents(self, law_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        법령 목록에서 상세 문서 내용 수집

        Args:
            law_list: 법령 목록 (get_law_list 또는 search_laws_by_keywords 결과)

        Returns:
            상세 내용이 포함된 법령 문서 목록
        """
        try:
            logger.info(f"📚 법령 문서 수집 시작 - 대상: {len(law_list)}개")

            collected_docs = []

            for i, law in enumerate(law_list, 1):
                try:
                    law_id = law.get("법령ID", "")
                    law_name = law.get("법령명", "알 수 없음")

                    if not law_id:
                        logger.warning(f"⚠️ 법령 ID가 없습니다: {law_name}")
                        continue

                    logger.debug(f"📄 문서 수집 중 ({i}/{len(law_list)}): {law_name}")

                    # 상세 내용 조회
                    detail_result = self.get_law_detail(law_id, raise_for_status=False)

                    # 문서 데이터 구성
                    document = {
                        "id": law_id,
                        "title": law_name,
                        "content": self._extract_law_content(detail_result),
                        "source": f"법제처_API_{law_id}",
                        "metadata": {
                            "법령ID": law_id,
                            "법령명": law_name,
                            "검색키워드": law.get("검색키워드", ""),
                            "수집일시": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "원본데이터": law,
                        },
                    }

                    # 내용이 있는 경우만 추가
                    if document["content"].strip():
                        collected_docs.append(document)
                        logger.debug(f"✅ 문서 수집 완료: {law_name} ({len(document['content'])}자)")
                    else:
                        logger.warning(f"⚠️ 내용이 비어있습니다: {law_name}")

                    # API 호출 간격 조절
                    time.sleep(0.2)

                except Exception as e:
                    logger.warning(f"⚠️ 개별 문서 수집 실패 ({law.get('법령명', 'Unknown')}): {str(e)}")
                    continue

            logger.info(f"✅ 법령 문서 수집 완료 - 성공: {len(collected_docs)}개")
            return collected_docs

        except Exception as e:
            logger.error(f"❌ 법령 문서 수집 실패: {str(e)}")
            raise

    def _extract_law_content(self, detail_data: Dict[str, Any]) -> str:
        """
        API 응답에서 법령 내용 추출

        Args:
            detail_data: 법령 상세 API 응답 데이터

        Returns:
            추출된 법령 내용 텍스트
        """
        try:
            content_parts = []

            # API 응답 구조에 따라 내용 추출 (실제 API 응답 구조에 맞게 조정 필요)
            if "LawSearch" in detail_data:
                law_data = detail_data["LawSearch"]

                # 법령명 추가
                if "법령명" in law_data:
                    content_parts.append(f"# {law_data['법령명']}")

                # 법령 내용 추가 (실제 필드명은 API 문서 확인 필요)
                if "조문내용" in law_data:
                    content_parts.append(law_data["조문내용"])
                elif "내용" in law_data:
                    content_parts.append(law_data["내용"])
                elif "본문" in law_data:
                    content_parts.append(law_data["본문"])

                # 기타 중요 정보 추가
                if "제정개정" in law_data:
                    content_parts.append(f"\n## 제정개정 정보\n{law_data['제정개정']}")

            return "\n\n".join(content_parts) if content_parts else ""

        except Exception as e:
            logger.warning(f"⚠️ 법령 내용 추출 실패: {str(e)}")
            return ""

    def get_health_check(self) -> Dict[str, Any]:
        """
        API 연결 상태 확인

        Returns:
            상태 확인 결과
        """
        try:
            logger.debug("🩺 법제처 API 상태 확인 중...")

            # 간단한 검색으로 API 상태 확인
            result = self.get_law_list(search_keyword="", page=1, display=1, raise_for_status=False)

            if "LawSearch" in result:
                return {
                    "status": "healthy",
                    "api_accessible": True,
                    "user_id": self.user_id,
                    "base_url": self.base_url,
                    "message": "법제처 API 정상 연결",
                }
            else:
                return {"status": "warning", "api_accessible": True, "message": "API 응답 형식 확인 필요"}

        except Exception as e:
            logger.error(f"❌ 법제처 API 상태 확인 실패: {str(e)}")
            return {"status": "unhealthy", "api_accessible": False, "error": str(e), "message": "법제처 API 연결 실패"}


# 기존 호환성을 위한 별칭
def get_law(raise_for_status=True):
    """기존 get_law 함수 호환성 유지"""
    api = LawApi()
    return api.get_law_list(raise_for_status=raise_for_status)


if __name__ == "__main__":
    """
    법제처 API 테스트 및 사용 예시
    """
    print("🏛️ 법제처 API 테스트 시작...")

    try:
        # API 클라이언트 생성
        law_api = LawApi()

        # 1. API 상태 확인
        print("\n1️⃣ API 상태 확인:")
        health = law_api.get_health_check()
        print(f"   상태: {health['status']}")
        print(f"   메시지: {health['message']}")

        # 2. 키워드 검색 테스트
        print("\n2️⃣ 키워드 검색 테스트:")
        keywords = ["근로기준법", "임대차"]
        search_results = law_api.search_laws_by_keywords(keywords, max_results=5)
        print(f"   검색 결과: {len(search_results)}개 법령")

        for law in search_results[:3]:  # 상위 3개만 출력
            print(f"   - {law.get('법령명', 'Unknown')} (키워드: {law.get('검색키워드', 'N/A')})")

        # 3. 문서 수집 테스트
        if search_results:
            print("\n3️⃣ 문서 수집 테스트:")
            documents = law_api.collect_law_documents(search_results[:2])  # 상위 2개만 수집
            print(f"   수집된 문서: {len(documents)}개")

            for doc in documents:
                print(f"   - {doc['title']}: {len(doc['content'])}자")

        print("\n✅ 법제처 API 테스트 완료!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback

        traceback.print_exc()
