from enum import Enum

class InterviewMode(str, Enum):
    BUDDY = "buddy"
    STRICT = "strict"
    BEHAVIORAL = "behavioral"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
