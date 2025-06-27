from enum import Enum


class LawApiPath(str, Enum):
    law = "law"  # 법령
    prec = "prec"  # 판례
