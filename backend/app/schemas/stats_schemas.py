from pydantic import BaseModel
from typing import List
from datetime import date

class WordCountStat(BaseModel):
    date: date
    count: int

class LanguageStat(BaseModel):
    language: str
    count: int
    percentage: float

class StreakData(BaseModel):
    current: int
    longest: int
    totalWords: int

class UserStatsResponse(BaseModel):
    wordCounts: List[WordCountStat]
    languageBreakdown: List[LanguageStat]
    streak: StreakData

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2 