# Workflow: Упаковка/Распаковка форм 1С и сборка обработки

Набор скриптов для работы с внешними обработками 1С в текстовом формате.

## 📦 Структура

```
workflow/
├── pack_forms.py          # Скрипт упаковки форм в Form.bin
├── unpack_forms.py        # Скрипт распаковки Form.bin в текст
├── make.py                # Скрипт сборки обработки через Designer
├── ТестCOMПодключения.xml # Метаданные обработки (пример)
└── ТестCOMПодключения/    # Исходный код обработки (пример)
    └── Forms/
        ├── Обычная/
        │   └── Ext/
        │       ├── Form.bin      # Бинарный файл формы
        │       └── Form/         # Текстовый формат
        │           ├── Form.xml
        │           └── Module.bsl
        └── Управляемая/
            └── Ext/
                └── Form/
                    ├── Form.xml
                    └── Module.bsl
```

## 🔧 Требования

- Python 3.8+
- [v8unpack](https://github.com/x1a90/v8unpack) — для распаковки/упаковки форм
- 1С:Предприятие 8.3+ — для сборки обработки

```bash
pip install v8unpack
```

---

## 📜 Скрипты

### 1. `unpack_forms.py` — Распаковка форм

Распаковывает все файлы `Form.bin` в текстовый формат (`Form.xml` + `Module.bsl`).

**Что делает:**
- Находит все файлы `Form.bin` в проекте
- Распаковывает каждый в структуру `Ext/Form/`
- Создаёт `Form.xml` и `Module.bsl` (если есть модуль)
- Перезаписывает существующие файлы

**Запуск:**
```bash
python unpack_forms.py
```

**Результат:**
```
[OK] Распакован: ТестCOMПодключения/Forms/Обычная/Ext/Form.bin
[OK] Перезаписан: ТестCOMПодключения/Forms/Управляемая/Ext/Form.bin
```

---

### 2. `pack_forms.py` — Упаковка форм

Упаковывает текстовые файлы форм обратно в `Form.bin`.

**Что делает:**
- Находит все директории `Ext/Form/` с файлом `Form.xml`
- Для каждой создаёт/обновляет `Form.bin`
- Берёт содержимое `Module.bsl` и записывает в бинарный файл

**Запуск:**
```bash
python pack_forms.py
```

**Результат:**
```
[OK] Упакован: ТестCOMПодключения/Forms/Обычная/Ext/Form.bin
[OVERWRITE] Перезаписан: ТестCOMПодключения/Forms/Управляемая/Ext/Form.bin
```

---

### 3. `make.py` — Сборка обработки

Собирает внешнюю обработку через 1С:Designer из XML-файла метаданных.

**Что делает:**
- Находит XML-файл метаданных в корне проекта
- Запускает 1С:Designer в режиме загрузки внешней обработки
- Сохраняет результат в папку `build/` с именем `<XML>_<GitVersion>.epf`

**Настройка:**
```bash
# Переменные окружения (опционально)
set 1C_BASE_PATH=C:\1c-bases\БППустаяДляСборки
set 1C_EXE_PATH=C:\Program Files\1cv8\8.3.27.1719\bin\1cv8.exe
```

**Запуск:**
```bash
python make.py
```

**Результат:**
```
build/ТестCOMПодключения_Исправлен вывод сообщения.epf
```

---

## 🚀 Типовой процесс работы

### Начало разработки (распаковка)
```bash
# 1. Распаковать все формы для редактирования
python unpack_forms.py

# 2. Редактировать Module.bsl в любом редакторе
# 3. Закоммитить изменения
git add .
git commit -m "Описание изменений"
```

### Перед сборкой (упаковка)
```bash
# 1. Упаковать формы обратно в бинарник
python pack_forms.py

# 2. Собрать обработку
python make.py

# 3. Готово! Обработка в build/
```

---

## ⚙️ Конвейер CI/CD

Пример использования в автоматизации:

```yaml
# .github/workflows/build.yml
- name: Unpack forms
  run: python unpack_forms.py

- name: Run tests
  run: pytest tests/

- name: Pack forms
  run: python pack_forms.py

- name: Build epf
  run: python make.py

- name: Upload artifact
  uses: actions/upload-artifact@v4
  with:
    path: build/*.epf
```

---

## 📝 Примечания

- Скрипты автоматически очищают временные папки (`temp_unpack`, `decode_stage_*`, и т.д.)
- `Form.bin` исключён из git через `.gitignore` — храните только текстовые файлы
- Папка `build/` также игнорируется git

---

## 📄 Лицензия

MIT
