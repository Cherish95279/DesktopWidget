import pathlib
path = pathlib.Path(r"D:\PythonProjects\DesktopWidget\src\utils.py")
content = path.read_text("utf-8")

# Add the new entry next to each existing "Thundery outbreaks possible" entry
replacements = [
    # Icon map
    ('"Thundery outbreaks possible": "⛈️",', '"Thundery outbreaks possible": "⛈️",\n        "Thundery outbreaks in nearby": "⛈️",'),
    # English (en)
    ('"Thundery outbreaks possible": "Thundery outbreaks possible",', '"Thundery outbreaks possible": "Thundery outbreaks possible",\n        "Thundery outbreaks in nearby": "Thundery outbreaks in nearby",'),
    # Chinese - zh_CN
    ('"Thundery outbreaks possible": "可能有雷暴",', '"Thundery outbreaks possible": "可能有雷暴",\n        "Thundery outbreaks in nearby": "附近有雷暴",'),
    # zh_TW
    ('"Thundery outbreaks possible": "可能有雷暴",', '"Thundery outbreaks possible": "可能有雷暴",\n        "Thundery outbreaks in nearby": "附近有雷暴",'),
    # Japanese - ja (find: "Blizzard": "吹雪", "Thundery outbreaks possible": "雷雨")
    ('"Thundery outbreaks possible": "雷雨",', '"Thundery outbreaks possible": "雷雨",\n        "Thundery outbreaks in nearby": "付近で雷雨",'),
    # Korean - ko
    ('"Thundery outbreaks possible": "뇌우",', '"Thundery outbreaks possible": "뇌우",\n        "Thundery outbreaks in nearby": "인근 뇌우",'),
    # Spanish - es
    ('"Thundery outbreaks possible": "Tormenta eléctrica",', '"Thundery outbreaks possible": "Tormenta eléctrica",\n        "Thundery outbreaks in nearby": "Tormenta eléctrica cercana",'),
    # French - fr
    ('"Thundery outbreaks possible": "Orages possibles",', '"Thundery outbreaks possible": "Orages possibles",\n        "Thundery outbreaks in nearby": "Orages à proximité",'),
    # German - de
    ('"Thundery outbreaks possible": "Gewitter möglich",', '"Thundery outbreaks possible": "Gewitter möglich",\n        "Thundery outbreaks in nearby": "Gewitter in der Nähe",'),
]

for old, new in replacements:
    count = content.count(old)
    if count == 1:
        content = content.replace(old, new, 1)
        print(f"  OK: added nearby entry")
    else:
        print(f"  SKIP: found {count} matches for old pattern")

path.write_text(content, "utf-8")
import py_compile
py_compile.compile(str(path), doraise=True)
print("OK")
