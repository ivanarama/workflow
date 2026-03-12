# -*- coding: utf-8 -*-
"""
Скрипт сборки обработки 1С через Designer
Автоматически определяет пути на основе расположения скрипта
"""

import os
import sys
import io
import subprocess
import time
from pathlib import Path

# =============================================================================
# === НАСТРОЙКИ (все переменные объявлены в начале)
# =============================================================================

# Путь к базе 1С для сборки (можно переопределить в переменной окружения 1C_BASE_PATH)
PATH_TO_BASE = os.environ.get("1C_BASE_PATH", r"C:\1c-bases\БППустаяДляСборки3_0_188_22")

# Путь к 1С (по умолчанию, можно переопределить в переменной окружения 1C_EXE_PATH)
ONE_C_EXE = os.environ.get("1C_EXE_PATH", r"C:\Program Files\1cv8\8.3.27.1719\bin\1cv8.exe")

# Директория скрипта
SCRIPT_DIR = Path(__file__).parent.resolve()

# Путь к XML файлу (в той же папке что и скрипт, ищем первый *.xml)
PATH_TO_XML = None

# Имя выходной обработки (будет сформировано как <ИмяXML>_<GitVersion>.epf)
OUTPUT_FILENAME = None

# Директория сборки
BUILD_DIR = SCRIPT_DIR / "build"

# Файл лога
LOG_FILE = BUILD_DIR / "log.txt"


# =============================================================================
# === ФУНКЦИИ
# =============================================================================

def find_1c_exe():
    """Автоматический поиск 1cv8.exe"""
    # Пытаемся найти через реестр Windows
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\1C\1Cv8")
        try:
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            exe_path = Path(install_path) / "bin" / "1cv8.exe"
            if exe_path.exists():
                return str(exe_path)
        except:
            pass
    except:
        pass
    
    # Ищем в Program Files все версии
    for pf in [r"C:\Program Files\1cv8", r"C:\Program Files (x86)\1cv8"]:
        if os.path.exists(pf):
            for version in sorted(os.listdir(pf), reverse=True):
                exe = Path(pf) / version / "bin" / "1cv8.exe"
                if exe.exists():
                    return str(exe)
    
    return None


def find_xml_file():
    """Поиск XML файла в директории скрипта"""
    xml_files = list(SCRIPT_DIR.glob("*.xml"))
    # Исключаем служебные файлы (например, .xml файлы конфигурации IDE)
    for xml in xml_files:
        # Пропускаем файлы начинающиеся с точки (скрытые) и служебные
        if xml.name.startswith("."):
            continue
        return xml
    return None


def get_git_version():
    """Получить сообщение последнего коммита из git"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip()
        return version if version else "unknown"
    except Exception as e:
        print(f"[WARN] Не удалось получить версию git: {e}")
        return "unknown"


def create_directory(path):
    """Создать директорию если не существует"""
    Path(path).mkdir(parents=True, exist_ok=True)


def main():
    # Устанавливаем UTF-8 для вывода в консоль
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    
    print("=" * 60)
    print("Сборка обработки 1С через Designer")
    print("=" * 60)
    print()
    
    # Инициализация путей
    global ONE_C_EXE, PATH_TO_XML, OUTPUT_FILENAME
    
    # Ищем 1С только если указанный путь не существует
    if not os.path.exists(ONE_C_EXE):
        ONE_C_EXE = find_1c_exe()
    
    PATH_TO_XML = find_xml_file()
    
    # Проверка путей
    if not ONE_C_EXE:
        print("[ERR] 1С не найдена. Укажите путь в переменной окружения 1C_EXE_PATH")
        sys.exit(1)
    
    if not PATH_TO_XML:
        print("[ERR] XML файл не найден в директории скрипта")
        sys.exit(1)
    
    if not os.path.exists(PATH_TO_BASE):
        print(f"[ERR] База 1С не найдена: {PATH_TO_BASE}")
        sys.exit(1)
    
    # Формируем имя выходного файла: <ИмяXML>_<GitVersion>.epf
    xml_name = PATH_TO_XML.stem  # имя файла без расширения
    OUTPUT_FILENAME = f"{xml_name}_{get_git_version()}.epf"
    OUTPUT_FILE = BUILD_DIR / OUTPUT_FILENAME
    
    # Вывод информации
    print(f"[OK] 1С: {ONE_C_EXE}")
    print(f"[OK] База: {PATH_TO_BASE}")
    print(f"[OK] XML: {PATH_TO_XML.name}")
    print(f"[OK] Результат: {OUTPUT_FILENAME}")
    print()

    # Создаем директорию сборки
    create_directory(BUILD_DIR)

    # --- ЗАПУСК ---
    print("Запуск сборки в базе БП 3.0...")
    print("Если появится окно авторизации - просто нажмите Войти (поле будет пустым).")
    print()

    # Формируем параметры для Designer напрямую в командной строке
    cmd = (
        f'"{ONE_C_EXE}" DESIGNER '
        f'/N "" '
        f'/F "{PATH_TO_BASE}" '
        f'/LoadExternalDataProcessorOrReportFromFiles "{PATH_TO_XML}" "{OUTPUT_FILE}" '
        f'/Out "{LOG_FILE}"'
        # f' /NonStop'  # Можно добавить при необходимости
    )

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            timeout=300  # 5 минут на сборку
        )
    except subprocess.TimeoutExpired:
        print("[ERR] Таймаут сборки (5 минут)")
        sys.exit(1)
    
    # Небольшая пауза для завершения записи файла
    time.sleep(1)
    
    # --- ПРОВЕРКА ---
    print()
    if OUTPUT_FILE.exists():
        file_size = OUTPUT_FILE.stat().st_size
        print("=" * 60)
        print(f"УСПЕХ! Обработка собрана: {OUTPUT_FILE}")
        print(f"Размер файла: {file_size:,} байт")
        print("=" * 60)
    else:
        print("=" * 60)
        print("ОШИБКА: Файл не создался.")
        print(f"Проверьте лог сборки: {LOG_FILE}")
        print("=" * 60)
        
        if LOG_FILE.exists():
            print()
            print("Последние строки лога:")
            print("-" * 40)
            try:
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    for line in lines[-10:]:
                        print(line.rstrip())
            except:
                print("[Не удалось прочитать лог]")


if __name__ == "__main__":
    main()
