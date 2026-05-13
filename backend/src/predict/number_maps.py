"""预测算法使用的数字映射常量。

从 predict/mechanisms.py 中提取，供机制算法和其他模块复用。
"""

from __future__ import annotations

HEAD_NUMBER_MAP: dict[str, list[str]] = {
    "0头": [f"{number:02d}" for number in range(1, 10)],
    "1头": [str(number) for number in range(10, 20)],
    "2头": [str(number) for number in range(20, 30)],
    "3头": [str(number) for number in range(30, 40)],
    "4头": [str(number) for number in range(40, 50)],
}

TAIL_NUMBER_MAP: dict[str, list[str]] = {
    f"{tail}尾": [
        f"{number:02d}"
        for number in range(1, 50)
        if number % 10 == tail
    ]
    for tail in range(10)
}

PARITY_NUMBER_MAP: dict[str, list[str]] = {
    "单": [f"{number:02d}" for number in range(1, 50) if number % 2 == 1],
    "双": [f"{number:02d}" for number in range(1, 50) if number % 2 == 0],
}

WAVE_COLOR_NUMBER_MAP: dict[str, list[str]] = {
    "红波": ["01", "02", "07", "08", "12", "13", "18", "19", "23", "24", "29", "30", "34", "35", "40", "45", "46"],
    "蓝波": ["03", "04", "09", "10", "14", "15", "20", "25", "26", "31", "36", "37", "41", "42", "47", "48"],
    "绿波": ["05", "06", "11", "16", "17", "21", "22", "27", "28", "32", "33", "38", "39", "43", "44", "49"],
}

HALF_WAVE_NUMBER_MAP: dict[str, list[str]] = {
    "红单": ["01", "07", "13", "19", "23", "29", "35", "45"],
    "红双": ["02", "08", "12", "18", "24", "30", "34", "40", "46"],
    "蓝单": ["03", "09", "15", "25", "31", "37", "41", "47"],
    "蓝双": ["04", "10", "14", "20", "26", "36", "42", "48"],
    "绿单": ["05", "11", "17", "21", "27", "33", "39", "43", "49"],
    "绿双": ["06", "16", "22", "28", "32", "38", "44"],
}

SIZE_NUMBER_MAP: dict[str, list[str]] = {
    "小": [f"{number:02d}" for number in range(1, 25)],
    "大": [str(number) for number in range(25, 50)],
}
