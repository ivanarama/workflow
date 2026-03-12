# -*- coding: utf-8 -*-
"""
Скрипт для массовой распаковки файлов Form.bin в текстовый формат
используя утилиту v8unpack
"""

import os
import sys
import io

# Устанавливаем UTF-8 для вывода в консоль
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import shutil
import subprocess
from pathlib import Path

# Корневая директория проекта (где лежит этот скрипт)
ROOT_DIR = Path(__file__).parent.resolve()

# Путь к v8unpack: ищем в PATH или в стандартных местах Python
def find_v8unpack():
    """Автоматический поиск v8unpack.exe"""
    # Сначала пробуем найти через shutil.which (ищет в PATH)
    v8unpack = shutil.which("v8unpack")
    if v8unpack:
        return v8unpack
    
    # Если не найдено, ищем в стандартных путях Python
    python_scripts = Path(sys.executable).parent / "Scripts" / "v8unpack.exe"
    if python_scripts.exists():
        return str(python_scripts)
    
    # Для Windows Store Python
    appdata_local = Path(os.environ.get("LOCALAPPDATA", ""))
    if appdata_local.exists():
        for pattern in appdata_local.glob("**/Scripts/v8unpack.exe"):
            return str(pattern)
    
    return None

V8UNPACK_PATH = find_v8unpack()

def find_bin_files(root_path):
    """Найти все файлы Form.bin в директории и поддиректориях"""
    bin_files = []
    for root, dirs, files in os.walk(root_path):
        # Пропускаем служебные директории
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.qwen', 'temp_unpack', 'temp_pack', 'decode_stage_']):
            continue

        for file in files:
            if file == "Form.bin":
                bin_files.append(os.path.join(root, file))

    return bin_files


def unpack_form_bin(bin_file_path):
    """
    Распаковать файл Form.bin в текстовый формат
    v8unpack saby создает структуру: decode_stage_0/0/form и decode_stage_0/0/module
    """
    bin_path = Path(bin_file_path)
    form_dir = bin_path.parent / "Form"

    # Проверяем, уже ли распакован (Form.xml должен существовать)
    if form_dir.exists():
        form_xml = form_dir / "Form.xml"
        if form_xml.exists() and form_xml.stat().st_size > 0:
            print(f"[OVERWRITE] Перезаписываем: {bin_path.relative_to(ROOT_DIR)}")

    try:
        # Создаем временную директорию для распаковки
        temp_dir = bin_path.parent / "temp_unpack"

        # Очищаем старую temp директорию и decode_stage_* директории
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Очищаем старые decode_stage_* директории если есть
        for decode_stage in bin_path.parent.glob("decode_stage_*"):
            try:
                shutil.rmtree(decode_stage, ignore_errors=True)
            except:
                pass

        temp_dir.mkdir(exist_ok=True)

        # Команда для распаковки: v8unpack -E <bin_file> <output_dir> --temp <temp_dir>
        # Используем абсолютные пути для избежания проблем с кодировкой
        abs_bin_path = bin_path.resolve()
        abs_temp_dir = temp_dir.resolve()

        cmd = f'"{V8UNPACK_PATH}" -E "{abs_bin_path}" "{abs_temp_dir}" --temp "{abs_temp_dir}"'

        # Убираем text=True, чтобы избежать ошибок кодировки
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
            shell=True
        )

        # Ищем распакованные файлы в decode_stage_0/0/
        decode_dir = temp_dir / "decode_stage_0" / "0"

        if decode_dir.exists():
            form_file = decode_dir / "form"
            module_file = decode_dir / "module"

            # Создаем целевую директорию
            form_dir.mkdir(parents=True, exist_ok=True)

            files_copied = False

            # Проверяем, существовал ли Form.xml до распаковки
            form_xml_path = form_dir / "Form.xml"
            form_existed = form_xml_path.exists() and form_xml_path.stat().st_size > 0

            # Копируем form -> Form.xml
            if form_file.exists() and form_file.stat().st_size > 0:
                shutil.copy2(form_file, form_dir / "Form.xml")
                files_copied = True

            # Копируем module -> Module.bsl (если есть)
            if module_file.exists() and module_file.stat().st_size > 0:
                shutil.copy2(module_file, form_dir / "Module.bsl")
                files_copied = True

            # Удаляем временную директорию
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if files_copied:
                if form_existed:
                    print(f"[OK] Перезаписан: {bin_path.relative_to(ROOT_DIR)}")
                    return True, "overwrite"
                else:
                    print(f"[OK] Распакован: {bin_path.relative_to(ROOT_DIR)}")
                    return True, "success"
        
        # Если не нашли файлы
        print(f"[WARN] Пустой результат: {bin_path.relative_to(ROOT_DIR)}")
        return False, "empty_result"

    except subprocess.TimeoutExpired:
        print(f"[ERR] Таймаут: {bin_path.relative_to(ROOT_DIR)}")
        return False, "timeout"
    except Exception as e:
        print(f"[ERR] Исключение: {bin_path.relative_to(ROOT_DIR)} - {str(e)}")
        return False, "exception"


def main():
    print("=" * 60)
    print("Распаковка файлов Form.bin в текстовый формат")
    print("=" * 60)
    print()

    # Проверяем наличие v8unpack
    if not os.path.exists(V8UNPACK_PATH):
        print(f"Ошибка: v8unpack не найден по пути: {V8UNPACK_PATH}")
        sys.exit(1)

    # Чистим старые временные папки в build/ и другие служебные
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        # Чистим все временные папки с префиксами temp_*, decode_*, encode_*
        patterns = ["temp_pack_*", "temp_unpack_*", "decode_stage_*", "encode_stage_*", "unpack_test", "test_pack", "manual_test"]
        for pattern in patterns:
            for temp_folder in build_dir.glob(pattern):
                try:
                    shutil.rmtree(temp_folder)
                    print(f"[CLEAN] Удалена временная папка: {temp_folder.relative_to(ROOT_DIR)}")
                except Exception as e:
                    print(f"[WARN] Не удалось удалить {temp_folder}: {e}")
    print()

    # Ищем все Form.bin файлы
    print(f"Поиск файлов Form.bin в: {ROOT_DIR}")
    bin_files = find_bin_files(ROOT_DIR)

    if not bin_files:
        print("Файлы Form.bin не найдены")
        sys.exit(0)

    print(f"Найдено файлов: {len(bin_files)}")
    print()
    
    # Статистика
    stats = {
        "success": 0,
        "overwrite": 0,
        "empty_result": 0,
        "v8unpack_error": 0,
        "timeout": 0,
        "exception": 0
    }
    
    # Распаковываем каждый файл
    for i, bin_file in enumerate(bin_files, 1):
        print(f"[{i}/{len(bin_files)}] ", end="")
        success, status = unpack_form_bin(bin_file)
        
        if success:
            stats[status] = stats.get(status, 0) + 1
        else:
            stats[status] = stats.get(status, 0) + 1
    
    # Итоговый отчет
    print()
    print("=" * 60)
    print("ИТОГИ:")
    print("=" * 60)
    print(f"Всего файлов:        {sum(stats.values())}")
    print(f"[OK] Распаковано:    {stats['success']}")
    print(f"[OVERWRITE] Перезаписано: {stats['overwrite']}")
    print(f"[WARN] Пустые:       {stats['empty_result']}")
    print(f"[ERR] Ошибки:        {stats['v8unpack_error'] + stats['timeout'] + stats['exception']}")
    print()


if __name__ == "__main__":
    main()
