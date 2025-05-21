import asyncio
from typing import Dict, List, Optional

from bson import ObjectId

from app.db.mongodb import get_collection
from app.utils.logger import logger


class QueryService:
    """문제 조회 서비스"""

    # 동시 조회 세마포어
    _query_semaphore = asyncio.Semaphore(100)

    # Part 5 관련 메서드
    async def get_part5_questions(
        self,
        category: Optional[str] = None,
        subtype: Optional[str] = None,
        difficulty: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
    ) -> List[Dict]:
        """
        Part 5 문제를 필터 조건에 맞게 랜덤으로 조회
        """
        async with self._query_semaphore:
            try:
                # 검색 조건 구성
                query = {}
                if category:
                    query["questionCategory"] = category
                if subtype:
                    query["questionSubType"] = subtype
                if difficulty:
                    query["difficulty"] = difficulty
                if keyword:
                    # 키워드 검색 (문제 또는 선택지에 키워드가 포함된 경우)
                    query["$or"] = [
                        {"questionText": {"$regex": keyword, "$options": "i"}},
                        {"choices.text": {"$regex": keyword, "$options": "i"}},
                    ]

                # 페이지네이션 계산
                skip = (page - 1) * limit

                # 랜덤 샘플링 + 스킵을 위한 파이프라인
                pipeline = [
                    {"$match": query},
                    {"$sample": {"size": limit + skip}},
                    {"$skip": skip},
                    {"$limit": limit},
                ]

                async with get_collection("part5_questions") as collection:
                    cursor = await collection.aggregate(pipeline)
                    questions = await cursor.to_list(length=limit)
                    return questions
            except Exception as e:
                logger.error(f"Error getting Part 5 questions: {e}")
                return []

    async def get_part5_total_count(
        self,
        category: Optional[str] = None,
        subtype: Optional[str] = None,
        difficulty: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        """Part 5 문제 총 개수 조회"""
        try:
            query = {}
            if category:
                query["questionCategory"] = category
            if subtype:
                query["questionSubType"] = subtype
            if difficulty:
                query["difficulty"] = difficulty
            if keyword:
                query["$or"] = [
                    {"questionText": {"$regex": keyword, "$options": "i"}},
                    {"choices.text": {"$regex": keyword, "$options": "i"}},
                ]

            async with get_collection("part5_questions") as collection:
                return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error getting Part 5 count: {e}")
            return 0

    async def get_part5_answer(self, question_id: ObjectId) -> Dict:
        """Part 5 문제의 정답/해석/해설/어휘정보 조회"""
        try:
            async with get_collection("part5_questions") as collection:
                question = await collection.find_one({"_id": question_id})
                if not question:
                    return None

                # 필요한 필드만 추출하여 반환
                return {
                    "id": str(question["_id"]),
                    "answer": question["answer"],
                    "explanation": question["explanation"],
                    "vocabulary": question.get("vocabulary", []),
                }
        except Exception as e:
            logger.error(f"Error getting Part 5 answer: {e}")
            return None

    async def get_part5_used_categories(self) -> List[str]:
        """
        데이터베이스에 실제로 사용 중인 Part 5 카테고리 목록 조회
        """
        try:
            pipeline = [{"$group": {"_id": "$questionCategory"}}, {"$sort": {"_id": 1}}]

            async with get_collection("part5_questions") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)
                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 5 categories: {e}")
            return []

    async def get_part5_used_subtypes(
        self, category: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        데이터베이스에 실제로 사용 중인 Part 5 서브타입 목록 조회
        특정 카테고리가 지정된 경우 해당 카테고리의 서브타입만 반환
        """
        try:
            async with get_collection("part5_questions") as collection:
                if category:
                    pipeline = [
                        {"$match": {"questionCategory": category}},
                        {"$group": {"_id": "$questionSubType"}},
                        {"$sort": {"_id": 1}},
                    ]

                    cursor = await collection.aggregate(pipeline)
                    results = await cursor.to_list(length=100)

                    return [result["_id"] for result in results]
                else:
                    pipeline = [
                        {
                            "$group": {
                                "_id": {
                                    "category": "$questionCategory",
                                    "subtype": "$questionSubType",
                                }
                            }
                        },
                        {"$sort": {"_id.category": 1, "_id.subtype": 1}},
                    ]

                    cursor = await collection.aggregate(pipeline)
                    results = await cursor.to_list(length=100)

                    # 카테고리별로 서브타입 그룹화
                    grouped = {}
                    for result in results:
                        category = result["_id"]["category"]
                        subtype = result["_id"]["subtype"]

                        if category not in grouped:
                            grouped[category] = []

                        grouped[category].append(subtype)

                    return grouped
        except Exception as e:
            logger.error(f"Error getting Part 5 subtypes: {e}")
            return {} if category is None else []

    async def get_part5_used_difficulties(
        self, category: Optional[str] = None, subtype: Optional[str] = None
    ) -> List[str]:
        """
        데이터베이스에 실제로 사용 중인 Part 5 난이도 목록 조회
        특정 카테고리나 서브타입이 지정된 경우 해당 조건에 맞는 난이도만 반환
        """
        try:
            match_stage = {}
            if category:
                match_stage["questionCategory"] = category
            if subtype:
                match_stage["questionSubType"] = subtype

            pipeline = [
                {"$match": match_stage},
                {"$group": {"_id": "$difficulty"}},
                {"$sort": {"_id": 1}},
            ]

            async with get_collection("part5_questions") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 5 difficulties: {e}")
            return []

    # Part 6 관련 메서드
    async def get_part6_sets(
        self,
        passage_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 2,
        page: int = 1,
    ) -> List[Dict]:
        """
        Part 6 문제 세트를 필터 조건에 맞게 랜덤으로 조회
        """
        async with self._query_semaphore:
            try:
                query = {}
                if passage_type:
                    query["passageType"] = passage_type
                if difficulty:
                    query["difficulty"] = difficulty

                # 페이지네이션 계산
                skip = (page - 1) * limit

                # 랜덤 샘플링 + 스킵을 위한 파이프라인
                pipeline = [
                    {"$match": query},
                    {"$sample": {"size": limit + skip}},
                    {"$skip": skip},
                    {"$limit": limit},
                ]

                async with get_collection("part6_sets") as collection:
                    cursor = await collection.aggregate(pipeline)
                    sets = await cursor.to_list(length=limit)
                    return sets
            except Exception as e:
                logger.error(f"Error getting Part 6 sets: {e}")
                return []

    async def get_part6_total_count(
        self,
        passage_type: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> int:
        """Part 6 문제 세트 총 개수 조회"""
        try:
            query = {}
            if passage_type:
                query["passageType"] = passage_type
            if difficulty:
                query["difficulty"] = difficulty

            async with get_collection("part6_sets") as collection:
                return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error getting Part 6 count: {e}")
            return 0

    async def get_part6_answer(self, set_id: ObjectId, question_seq: int) -> Dict:
        """Part 6 문제 세트 내 특정 문제의 정답/해설 조회"""
        try:
            async with get_collection("part6_sets") as collection:
                set_data = await collection.find_one({"_id": set_id})
                if not set_data:
                    return None

                # 해당 question_seq를 가진 문제 찾기
                for question in set_data.get("questions", []):
                    if question.get("blankNumber") == question_seq:
                        return {
                            "set_id": str(set_data["_id"]),
                            "question_seq": question_seq,
                            "answer": question["answer"],
                            "explanation": question["explanation"],
                        }

                return None
        except Exception as e:
            logger.error(f"Error getting Part 6 answer: {e}")
            return None

    async def get_part6_used_passage_types(self) -> List[str]:
        """데이터베이스에 실제로 사용 중인 Part 6 지문 유형 목록 조회"""
        try:
            pipeline = [{"$group": {"_id": "$passageType"}}, {"$sort": {"_id": 1}}]

            async with get_collection("part6_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 6 passage types: {e}")
            return []

    async def get_part6_used_difficulties(
        self, passage_type: Optional[str] = None
    ) -> List[str]:
        """
        데이터베이스에 실제로 사용 중인 Part 6 난이도 목록 조회
        특정 지문 타입이 지정된 경우 해당 지문 타입에서 사용 중인 난이도만 반환
        """
        try:
            match_stage = {}
            if passage_type:
                match_stage["passageType"] = passage_type

            pipeline = [
                {"$match": match_stage},
                {"$group": {"_id": "$difficulty"}},
                {"$sort": {"_id": 1}},
            ]

            async with get_collection("part6_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 6 difficulties: {e}")
            return []

    # Part 7 관련 메서드
    async def get_part7_sets(
        self,
        set_type: str,
        passage_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        limit: int = 1,
        page: int = 1,
    ) -> List[Dict]:
        """
        Part 7 문제 세트를 필터 조건에 맞게 랜덤으로 조회
        """
        async with self._query_semaphore:
            try:
                query = {"questionSetType": set_type}
                if difficulty:
                    query["difficulty"] = difficulty

                # passage_types 처리 (복수 타입 지원)
                if passage_types:
                    if len(passage_types) == 1:
                        # 단일 타입 지정한 경우
                        query["passages.type"] = passage_types[0]
                    else:
                        # 복수 타입 조합 지정한 경우 (모든 타입을 포함하는 문서 찾기)
                        query["$and"] = [{"passages.type": pt} for pt in passage_types]

                # 페이지네이션 계산
                skip = (page - 1) * limit

                # set_type별 최대 limit 조정
                max_limits = {"Single": 5, "Double": 2, "Triple": 2}
                adjusted_limit = min(limit, max_limits.get(set_type, 1))

                # 랜덤 샘플링 + 스킵을 위한 파이프라인
                pipeline = [
                    {"$match": query},
                    {"$sample": {"size": adjusted_limit + skip}},
                    {"$skip": skip},
                    {"$limit": adjusted_limit},
                ]

                async with get_collection("part7_sets") as collection:
                    cursor = await collection.aggregate(pipeline)
                    sets = await cursor.to_list(length=adjusted_limit)
                    return sets
            except Exception as e:
                logger.error(f"Error getting Part 7 sets: {e}")
                return []

    async def get_part7_total_count(
        self,
        set_type: str,
        passage_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> int:
        """Part 7 문제 세트 총 개수 조회"""
        try:
            query = {"questionSetType": set_type}
            if difficulty:
                query["difficulty"] = difficulty

            if passage_types:
                if len(passage_types) == 1:
                    query["passages.type"] = passage_types[0]
                else:
                    query["$and"] = [{"passages.type": pt} for pt in passage_types]

            async with get_collection("part7_sets") as collection:
                return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error getting Part 7 count: {e}")
            return 0

    async def get_part7_answer(self, set_id: ObjectId, question_seq: int) -> Dict:
        """Part 7 문제 세트 내 특정 문제의 정답/해설 조회"""
        try:
            async with get_collection("part7_sets") as collection:
                set_data = await collection.find_one({"_id": set_id})
                if not set_data:
                    return None

                # 해당 question_seq를 가진 문제 찾기
                for question in set_data.get("questions", []):
                    if question.get("questionSeq") == question_seq:
                        return {
                            "set_id": str(set_data["_id"]),
                            "question_seq": question_seq,
                            "answer": question["answer"],
                            "explanation": question["explanation"],
                        }

                return None
        except Exception as e:
            logger.error(f"Error getting Part 7 answer: {e}")
            return None

    async def get_part7_used_set_types(self) -> List[str]:
        """데이터베이스에 실제로 사용 중인 Part 7 세트 유형 목록 조회"""
        try:
            pipeline = [{"$group": {"_id": "$questionSetType"}}, {"$sort": {"_id": 1}}]

            async with get_collection("part7_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 7 set types: {e}")
            return []

    async def get_part7_used_passage_types(
        self, set_type: Optional[str] = None
    ) -> List[str]:
        """
        데이터베이스에 실제로 사용 중인 Part 7 지문 유형 목록 조회
        특정 세트 유형이 지정된 경우 해당 세트 유형에서 사용 중인 지문 유형만 반환
        """
        try:
            match_stage = {}
            if set_type:
                match_stage = {"questionSetType": set_type}

            pipeline = [
                {"$match": match_stage},
                {"$unwind": "$passages"},  # passages 배열 풀기
                {"$group": {"_id": "$passages.type"}},
                {"$sort": {"_id": 1}},
            ]

            async with get_collection("part7_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 7 passage types: {e}")
            return []

    async def get_part7_used_passage_combinations(
        self, set_type: str
    ) -> List[List[str]]:
        """
        데이터베이스에 실제로 사용 중인 Part 7 지문 유형 조합 목록 조회
        특정 세트 유형(Double, Triple)에서 자주 사용되는 조합 반환
        """
        if set_type not in ["Double", "Triple"]:
            return []

        try:
            # 특정 세트 유형에 해당하는 문서만 조회
            pipeline = [
                {"$match": {"questionSetType": set_type}},
                # 각 문서마다 passages.type 값들을 배열로 추출
                {
                    "$project": {
                        "_id": 0,
                        "passage_types": {
                            "$map": {"input": "$passages", "as": "p", "in": "$$p.type"}
                        },
                    }
                },
                # 동일한 조합끼리 그룹화
                {"$group": {"_id": "$passage_types", "count": {"$sum": 1}}},
                # 빈도 순으로 정렬
                {"$sort": {"count": -1}},
                {"$limit": 20},  # 상위 20개 조합만 반환
            ]

            async with get_collection("part7_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=20)
                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 7 passage combinations: {e}")
            return []

    async def get_part7_used_difficulties(
        self, set_type: Optional[str] = None
    ) -> List[str]:
        """
        데이터베이스에 실제로 사용 중인 Part 7 난이도 목록 조회
        특정 세트 유형이 지정된 경우 해당 세트 유형에서 사용 중인 난이도만 반환
        """
        try:
            match_stage = {}
            if set_type:
                match_stage = {"questionSetType": set_type}

            pipeline = [
                {"$match": match_stage},
                {"$group": {"_id": "$difficulty"}},
                {"$sort": {"_id": 1}},
            ]

            async with get_collection("part7_sets") as collection:
                cursor = await collection.aggregate(pipeline)
                results = await cursor.to_list(length=100)

                return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Error getting Part 7 difficulties: {e}")
            return []
