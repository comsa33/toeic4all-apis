from typing import Annotated, List, Literal

from pydantic import BaseModel, Field

SeqInt = Annotated[int, Field(ge=1)]

# ── 지문 유형 Enum ─────────────────────
PassageType = Literal[
    "Email",
    "Letter",
    "Memo",
    "Notice",
    "Advertisement",
    "Article",
    "Form",
    "Schedule",
    "Receipt",
    "Chart",
    "Chat",
    "Report",
    "Other",
]

# ── 문항 유형 Enum ─────────────────────
QuestionType = Literal[
    "주제/목적", "세부사항", "추론", "어휘", "참조", "일치", "정보연계", "문장삽입"
]

# ── 단일/이중/삼중 지문 세트 유형 ──────
SetType = Literal["Single", "Double", "Triple"]


# ── 지문 단위 ────────────────────────
class PassageChunk(BaseModel):
    seq: SeqInt
    type: PassageType
    text: str
    translation: str | None = None


# ── 선택지 ───────────────────────────
class Choice(BaseModel):
    id: Literal["A", "B", "C", "D"]
    text: str
    translation: str


# ── 질문 단위 ────────────────────────
class SubQuestion(BaseModel):
    questionSeq: SeqInt
    questionType: QuestionType
    questionText: str
    questionTranslation: str
    choices: List[Choice] = Field(..., min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]
    explanation: str


# ── 파트7 세트 전체 ──────────────────
class Part7Set(BaseModel):
    part: int = Field(7, frozen=True)
    difficulty: Literal["Easy", "Medium", "Hard"]
    questionSetType: SetType
    passages: List[PassageChunk] = Field(..., min_length=1, max_length=3)
    questions: List[SubQuestion] = Field(..., min_length=2)
