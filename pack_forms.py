# -*- coding: utf-8 -*-
"""
Скрипт для массовой упаковки файлов форм из текстового формата в Form.bin
используя внутренние функции v8unpack напрямую
"""

import os
import sys
import io
import tempfile
import shutil
from pathlib import Path

# Устанавливаем UTF-8 для вывода в консоль
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Корневая директория проекта (где лежит этот скрипт)
ROOT_DIR = Path(__file__).parent.resolve()

# Импортируем v8unpack напрямую
try:
    from v8unpack.container_reader import extract as _container_extract
    from v8unpack.container_writer import build as _container_build
    V8UNPACK_AVAILABLE = True
except ImportError:
    V8UNPACK_AVAILABLE = False
    print("[WARN] v8unpack не установлен. Установите: pip install v8unpack")


def find_form_directories(root_path):
    """Найти все директории Ext/Form с Form.xml внутри"""
    form_dirs = []
    for root, dirs, files in os.walk(root_path):
        # Пропускаем служебные директории
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.qwen', 'temp_unpack', 'decode_stage_', 'temp_pack']):
            continue

        # Ищем структуру: .../Ext/Form/Form.xml
        # Проверяем, что мы в директории Form внутри Ext
        parent_dir = Path(root).parent
        if parent_dir.name == "Ext" and Path(root).name == "Form":
            form_xml = Path(root) / "Form.xml"
            if form_xml.exists() and form_xml.stat().st_size > 0:
                form_dirs.append(Path(root))

    return form_dirs


def pack_form_directory(form_dir_path):
    """
    Упаковать директорию с Form.xml в Form.bin
    Используем v8unpack.container_writer.build напрямую
    
    Алгоритм:
    1. Распаковываем существующий Form.bin (или создаем новый)
    2. Заменяем файл module на содержимое Module.bsl
    3. Запаковываем обратно
    """
    form_dir = Path(form_dir_path)
    bin_file = form_dir.parent / "Form.bin"
    form_xml = form_dir / "Form.xml"
    module_bsl = form_dir / "Module.bsl"

    if not form_xml.exists() or form_xml.stat().st_size == 0:
        print(f"[SKIP] Нет Form.xml: {form_dir.relative_to(ROOT_DIR)}")
        return False, "no_form_xml"

    bin_existed = bin_file.exists()
    if bin_existed:
        print(f"[OVERWRITE] Перезаписываем: {bin_file.relative_to(ROOT_DIR)}")
    else:
        print(f"[PACK] Создаём новый: {bin_file.relative_to(ROOT_DIR)}")

    if not V8UNPACK_AVAILABLE:
        print(f"[ERR] v8unpack не доступен: {form_dir.relative_to(ROOT_DIR)}")
        return False, "v8unpack_not_available"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            module_path = None
            
            if bin_existed:
                # Распаковываем существующий Form.bin
                # v8unpack распаковывает в поддиректорию '0'
                _container_extract(str(bin_file), temp_dir, deflate=False, recursive=True)
                
                # Находим файл module в распакованном содержимом
                module_path = _find_module_file(temp_dir)
                
                # Если module не найден, создаём его в директории '0'
                if module_path is None:
                    decode_dir = temp_path / "0"
                    if decode_dir.exists():
                        module_path = decode_dir / "module"
                    else:
                        print(f"[ERR] Не найдена директория '0' после распаковки")
                        return False, "extract_error"
            else:
                # Создаем новую структуру для нового Form.bin
                # v8unpack build ожидает структуру: temp_dir/0/form, temp_dir/0/module
                decode_dir = temp_path / "0"
                decode_dir.mkdir(parents=True, exist_ok=True)
                
                # Копируем Form.xml в form
                shutil.copy2(form_xml, decode_dir / "form")
                
                # Создаем module из Module.bsl если есть
                module_path = decode_dir / "module"
            
            # Записываем новый модуль из Module.bsl если он есть
            if module_bsl.exists() and module_bsl.stat().st_size > 0:
                if module_path is None:
                    decode_dir = temp_path / "0"
                    module_path = decode_dir / "module"
                    
                with open(module_bsl, 'rb') as f:
                    module_data = f.read()
                with open(module_path, 'wb') as f:
                    f.write(module_data)

            # Собираем Form.bin из temp директории
            # build ожидает temp_dir с поддиректорией '0' внутри
            _container_build(temp_dir, str(bin_file), nested=True)

            if bin_existed:
                print(f"[OK] Перезаписан: {bin_file.relative_to(ROOT_DIR)}")
                return True, "overwrite"
            else:
                print(f"[OK] Упакован: {bin_file.relative_to(ROOT_DIR)}")
                return True, "success"

    except Exception as e:
        print(f"[ERR] Исключение: {form_dir.relative_to(ROOT_DIR)} - {str(e)}")
        import traceback
        traceback.print_exc()
        return False, "exception"


def _find_module_file(extracted_dir: str):
    """Найти файл module в распакованном содержимом"""
    for root, dirs, files in os.walk(extracted_dir):
        for filename in files:
            if filename == 'module':
                return os.path.join(root, filename)
    return None


def main():
    print("=" * 60)
    print("Упаковка файлов форм из текстового формата в Form.bin")
    print("=" * 60)
    print()

    # Проверяем наличие v8unpack
    if not V8UNPACK_AVAILABLE:
        print("Ошибка: v8unpack не установлен")
        print("Установите: pip install v8unpack")
        sys.exit(1)

    # Чистим старые временные папки в build/
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

    # Ищем все директории с Form.xml
    print(f"Поиск директорий с Form.xml в: {ROOT_DIR}")
    form_dirs = find_form_directories(ROOT_DIR)

    if not form_dirs:
        print("Директории с Form.xml не найдены")
        sys.exit(0)

    print(f"Найдено директорий: {len(form_dirs)}")
    print()

    # Статистика
    stats = {
        "success": 0,
        "overwrite": 0,
        "no_form_xml": 0,
        "v8unpack_not_available": 0,
        "extract_error": 0,
        "exception": 0
    }

    # Упаковываем каждую директорию
    for i, form_dir in enumerate(form_dirs, 1):
        print(f"[{i}/{len(form_dirs)}] ", end="")
        success, status = pack_form_directory(form_dir)

        if success:
            stats[status] = stats.get(status, 0) + 1
        else:
            stats[status] = stats.get(status, 0) + 1

    # Итоговый отчет
    print()
    print("=" * 60)
    print("ИТОГИ:")
    print("=" * 60)
    print(f"Всего директорий:    {sum(stats.values())}")
    print(f"[OK] Упаковано:      {stats['success']}")
    print(f"[OVERWRITE] Перезаписано: {stats['overwrite']}")
    print(f"[SKIP] Нет Form.xml: {stats['no_form_xml']}")
    print(f"[ERR] Ошибки:        {stats['v8unpack_not_available'] + stats['exception']}")
    print()


if __name__ == "__main__":
    main()
