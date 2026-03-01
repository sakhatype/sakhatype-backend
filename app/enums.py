from enum import StrEnum, IntEnum

class Difficulty(StrEnum):
    normal = "normal"
    high = "high"

class TimeMode(IntEnum):
    fifteen = 15
    thirty = 30
    sixty = 60
    one_hundred_twenty = 120