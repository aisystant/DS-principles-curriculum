---
id: PD-GUIDE-V4-CONCEPT-CANDIDATES
title: "Кандидаты доменных понятий для PACK-personal/ontology.md § 2"
status: draft
created: 2026-05-16
upstream: [WP-300]
---

# Кандидаты доменных понятий v4 для PACK-personal/ontology.md § 2

> **Назначение:** список кандидатов на расширение [PACK-personal/ontology.md § 2 «Глоссарий домена»](../../../PACK-personal/ontology.md). Собран из всех 4 concept-map'ов и structure-guide'ов v4-reference.
>
> **Что дальше:** пилот ревизует «понятие vs кейс vs аналогия» → Knowledge Extractor (DP.AISYS.013) формализует утверждённые в `PACK-personal/ontology.md` § 2 → обновляются строки «Понятия:» в STRUCTURE-ALL-GUIDES.md и concept-map'ах с привязкой `parent: U.*`.
>
> **Правило идентификации (06-concept-graph-architecture.md §3.С5):** канонический русский имя + parent `U.*` из SPF.SPEC.002 § 2 + источник Pack `PD.FORM.NNN`/`PD.METHOD.NNN`. Локальный `PD.CON.NNN` НЕ вводится.

## Сводка

| Категория | Количество | Действие |
|-----------|-----------|----------|
| Уже в `PACK-personal/ontology.md` § 2 | ~10 | Сохранить, использовать как есть |
| Понятия — кандидаты на добавление в Pack-ontology | ~70 | Передать Knowledge Extractor |
| Кейсы (не понятия) | ~6 | Убрать из строк «Понятия:», оставить в тексте |
| Аналогии (не понятия) | ~7 | Убрать из строк «Понятия:», оставить в тексте как метафоры |
| Кандидаты на расширение SPF (нет родителя U.*) | ~2-3 | Передать Knowledge Extractor → SPF.SPEC.002 |

---

## Кейсы (не понятия) — убрать из строк «Понятия:»

| Имя | Где встречается | Природа |
|-----|-----------------|---------|
| Эффект Земмельвейса | 1.S1.SS1, 2.S1.02, 2.S1.07 | Исторический кейс сопротивления простой практике |
| Хохланд | Guide 4 (в концепт-мапе как пример Tame Flow) | Корпоративный кейс state-tracking |
| Когнитивная авария | 3.S6.SS7 | Антипаттерн-наблюдение |
| Контекстное загрязнение | 3.S4.SS4 | Антипаттерн-наблюдение |
| Потеря фокуса | 3.S8.SS5 | Антипаттерн-наблюдение |
| Сжигание времени | 3.S8.SS5 | Антипаттерн-наблюдение |
| Cognitive freeze | Guide 4 Tame Flow | Антипаттерн-наблюдение |

## Аналогии (не понятия) — оставить как метафоры в тексте

| Имя | Реальное понятие | Где встречается |
|-----|------------------|-----------------|
| Болид | Созидатель (`U.System`) | 1.S2.SS7, 1.S3.SS1, 1.S3.SS6, 3.S2.SS1, 4.S9.SS1 |
| Пилот | Часть аналогии Болид; реально = Человек + RoleAssignment Ученика | 1.S3.SS1, 3.S2.SS1, 4.S9.SS1 |
| Машина | Часть аналогии Болид; реально = IWE (`U.System`) | 1.S3.SS1, 3.S2.SS1, 4.S9.SS1 |
| Асептика для хирурга | Аналогия для «Культура как допуск к сложности» | 1.S1.SS2 |
| Рабочий стол в хаосе | Аналогия для «Когнитивная авария» | 3.S6.SS7 |
| Призма (для мировоззрения) | Аналогия для Мировоззрения (`U.Episteme`) | 1.S2.SS6 (через PD.FORM.022) |
| Автомобиль / культура вождения | Аналогия для IWE и культуры работы | 3.S1.SS4 |

---

## Понятия — кандидаты в PACK-personal/ontology.md § 2

### Уже зафиксированы в Pack-ontology (не дублировать)

`Созидатель → U.System`, `Характеристика созидателя → U.Characteristic`, `Состояние → U.Flow`, `Роль в деятельности → U.RoleAssignment`, `Знание → U.Capability`, `Навык → U.Capability`, `Мировоззрение → U.Episteme`, `Учёт времени → U.Method`, `Индикатор → U.Characteristic`, `Формализация → U.Episteme`.

### Руководство 1 — Системное саморазвитие (мировоззрение)

| Понятие | parent (U.*) | Источник | Комментарий | Статус |
|---------------------|--------------|----------|-------------|
| Мировоззренческая дуга | `U.Episteme` | PD.FORM.080 § 3 | Модель из 5 фаз | formalized |
| Фаза мировоззренческой дуги | `U.Kind` | PD.FORM.080 | Классификация состояний картины мира | formalized |
| Системное саморазвитие | `U.Method` | (новое, нужно обоснование) | Проект-метод — выстраивание себя как системы | formalized |
| Системное мировосприятие | `U.Episteme` | docs 1-1 | Стратегия видеть мир системно | formalized |
| Деятельностный кругозор | `U.Characteristic` | PD.FORM.022 § 6 | Уже в Pack как характеристика типа кругозора | formalized |
| Калибр личности | `U.Characteristic` | PD.FORM.090 | 6 уровней охвата (Я → человечество) | formalized |
| Экзокортекс | `U.System` | docs 1-1 § 1 | Персональная среда управления знаниями | formalized |
| Интеллект-стек | `U.Episteme` | docs (Левенчук) | 16 трансдисциплин как карта | formalized |
| Трансдисциплина | `U.Episteme` | docs | Дисциплина, прошивающая все области | formalized |
| SoTA (как статус) | `U.Episteme` | SPF-специфичный (уже в SPF) | Статус актуальности утверждения | formalized |
| Степень мастерства | `U.Kind` | FORM.006 | Объяснение → Умение → Навык → Мастерство | formalized |
| Ступень развития | `U.Kind` | PD.FORM.080, PD.FORM.089 | 5 ступеней: Случайный → Проактивный | formalized |
| Двойной gate | `U.Method` | PD.FORM.089 § 5.2 | Аттестатор (bh) + Диагност (cp) | formalized |
| Bottleneck (узкое место) | `U.Characteristic` | TOC + PD.FORM.089 | Точка фокуса развития | formalized |
| Творческий конвейер | `U.System` | PD.METHOD.019 | 4 стадии: потребление → размышления → действие → досуг | formalized |
| Культура ученика | `U.Episteme` | PD.FORM.022 | Инфраструктура из 6 практик; основа стиля ученика | formalized |
| 6 элементов культуры ученика | `U.Kind` | PD.FORM.022 / PD.METHOD.020 | Классификация: слот, саморегуляция, фиксация, восстановление, гигиена, ритуал | formalized |
| Допуск к сложности | `U.Method` | PD.FORM.022 | Минимальный набор практик, без которого сложные методы не усваиваются | formalized |
| Квадрант компетенций | `U.Kind` | docs (cited Burch) | 4 стадии освоения: НН → ОН → ОК → НК | formalized |
| Стиль жизни ученика | `U.Method` | PD.METHOD.021 (стиль становления) | Саморазвитие как норма, не проект | formalized |
| Слот саморазвития | `U.Method` | PD.METHOD.021 | Фиксированный временной блок, специализированный для саморазвития (тип содержимого) | formalized |
| Защищённый слот | `U.Method` | PD.METHOD.021 § 6.1 | **Атрибут защищённости**, применимый к разным типам слотов (саморазвития, стратсессии, восстановления и т.д.); правило: не переносится, а пропускается | formalized |
| Саморегуляция | `U.Method` | PD.METHOD.022 | Навык замечать состояние до спада ниже рабочего порога | formalized |
| Шкала состояния | `U.Characteristic` | PD.METHOD.022 | Инструмент самонаблюдения 0–5 | — |
| Отрицательная полезность труда | `U.Episteme` | (cited экономика) | Объяснение прокрастинации через уравнение «выигрыш vs затраты» | formalized |
| Аудит культуры ученика | `U.Method` | PD.FORM.022 | Диагностика состояния 6 элементов по шкале 0–10 | formalized |
| Гигиенический минимум | `U.Method` | PD.METHOD.020 | 6 столпов восстановления | formalized |
| 6 результатов программы ЛР | `U.Characteristic` | PD.FORM.093 | Терминальный профиль выпускника | formalized |
| Ценность как принцип | `U.Commitment` | docs | Инвариант, не цель | formalized |
| Намерение | `U.WorkPlan` | PD.METHOD.008 | Направление, выбранное из ценностей | formalized |
| Неудовлетворённость | `U.Episteme` | PD.METHOD.008 | Сигнал разрыва между текущим и желаемым | formalized |
| Сверхцель | `U.Commitment` | docs | Долгосрочный ориентир | formalized |
| Active Inference | `U.Episteme` | (cited Friston) | Теория свободной энергии | formalized |
| Принцип оптимизма Дойча | `U.Episteme` | (cited Deutsch) | «Всё, что не запрещено законами физики, возможно» | formalized |
| Быстрое мышление (S1) | `U.Episteme` | (cited Kahneman) | Интуитивное | formalized |
| Медленное мышление (S2) | `U.Episteme` | (cited Kahneman) | Аналитическое | formalized |
| Меметика | `U.Episteme` | (cited) | Дисциплина культурной передачи | formalized |
| Мем | `U.Kind` | (cited) | Вид/единица культурной передачи — классификационная сущность | formalized |
| Техноэволюция | `U.Episteme` | docs (Левенчук) | Эволюция через накопление технологий — vs биологическая эволюция через гены | formalized |
| Экзотело | `U.System` | docs (киберличность) | Физическое расширение человека: одежда, инструменты, деньги, имущество | formalized |
| 6 киберхарактеристик | `U.Kind` | docs | Классификация: агентность, интеллектуальная развитость, стрессоустойчивость, ресурсность, техноинтеграция, калибр | formalized |
| Компиляция знаний | `U.Method` | docs | Перевод знаний в мировоззрение через цикл «прочитал → применил → отразил → повторил» | formalized |
| Аудит Болида | `U.Method` | 1.S2.SS7 | Диагностика трёх компонентов: Пилот (мышление) + Машина (экзотело + экзокортекс) | formalized |
| Эшелонированная оборона | `U.Method` | PD.FORM.066 | Микро/мезо/макро досуг | — |
| Удовольствие как топливо | `U.Episteme` | PD.METHOD.022 | Состояние как ресурс | — |
| Мыслительный резонанс | `U.Episteme` | docs | Признак продуктивности | formalized |
| Тройной контур | `U.System` | docs (киберличность) | Тело + личность + мастерство | formalized |
| Киберличность | `U.System` | docs | Современная модель личности | formalized |
| Киберхарактеристика | `U.Characteristic` | docs | 6 характеристик киберчеловека | formalized |
| Три потока личной жизни | `U.Flow` | PD.METHOD.023 | Рабочие продукты + информация + энергия | formalized |
| Систематичность | `U.Characteristic` | docs 1-3 | Регулярность, дисциплина | formalized |
| Системность | `U.Characteristic` | docs 1-3 | Способность видеть системы | formalized |

### Руководство 2 — Методы саморазвития

| Понятие | parent (U.*) | Источник | Комментарий | Статус |
|---------|--------------|----------|-------------|--------|
| Метод саморазвития M001-M009 | `U.Method` | PD.METHOD.001-009 | Базовые методы (уже как Method-сущности в Pack) | — |
| Pomodoro / Помидорка | `U.Method` | PD.METHOD.001 | Интервал фокуса (cited Cirillo) | formalized |
| Наградная помидорка | `U.Method` | docs 1-2 | Лайфхак сопротивления | formalized |
| Бюджет времени | `U.WorkPlan` | docs 1-2 | 168 часов недели | formalized |
| 5 классов работы | `U.Kind` | docs 1-2 | Классификация: постоянные/временные/важные/текущие/срочные | formalized |
| Ритуал входа в роль | `U.Method` | docs 1-2 | Триггер: роль + метод + рабочий продукт | formalized |
| Образовательная заметка | `U.Work` | docs 1-2 § 3 | Артефакт медленного чтения | formalized |
| Систематическое медленное чтение | `U.Method` | PD.METHOD.003 | Чтение для мышления | formalized |
| Мышление письмом | `U.Method` | PD.METHOD.004 | Внешнизация мыслей | formalized |
| Черновик | `U.Work` | docs 1-2 § 4 | Стадия мышления письмом | formalized |
| Заготовка | `U.Work` | docs 1-2 § 4 | Стадия после черновика | formalized |
| Пост / Публикация | `U.Work` | docs 1-2 § 4 | Финальный рабочий продукт | formalized |
| Freewriting / Свободное письмо | `U.Method` | docs 1-2 § 4 | Письмо без тормозов | formalized |
| Мышление проговариванием | `U.Method` | PD.METHOD.005 | Прокладка нейронных связей | formalized |
| Голосовая заметка | `U.Work` | docs 1-2 § 5 | Артефакт проговаривания | formalized |
| Транскрибация | `U.Method` | docs | Перевод речи в текст | formalized |
| Эхо (отсроченный пересказ) | `U.Method` | docs 1-2 § 5 | Проверка усвоения | formalized |
| Правило паузы | `U.Method` | docs 1-2 § 3 | Остановка для рефлексии | formalized |
| Правило связи | `U.Method` | docs 1-2 § 3 | Соединение нового с известным | formalized |
| Активный досуг | `U.Method` | PD.METHOD.006 | Восстановление через действие | formalized |
| Пассивный досуг | `U.Method` | PD.METHOD.006 | Восстановление через покой | formalized |
| Микро / мезо / макро досуг | `U.Method` | PD.METHOD.006 (FORM.066) | Уровни эшелонированной обороны | formalized |
| Шкала состояния | `U.Characteristic` | PD.METHOD.022 | 0-5 | formalized |
| Продуктивное состояние | `U.Flow` | PD.METHOD.022 | Целевой режим работы | formalized |
| Неваляшка (протокол восстановления) | `U.Method` | docs | Восстановление при падении | formalized |
| Формирование окружения | `U.Method` | PD.METHOD.007 | Проектирование среды | formalized |
| Агент окружения (усилитель/тормоз/зеркало) | `U.RoleAssignment` | PD.METHOD.007 | Типология агентов | formalized |
| Аудит окружения | `U.Method` | PD.METHOD.007 | Инвентаризация влияний | formalized |
| Карта окружения | `U.Work` | PD.METHOD.007 | Артефакт аудита | formalized |
| Стратегирование | `U.Method` | PD.METHOD.008 | Выбор направления | formalized |
| Каскад ВДВ (Вектор-Домен-Веха) | `U.Method` | METHOD.008 | Три уровня плана | formalized |
| Вектор / Домен / Веха | `U.Kind` | METHOD.008 | Уровни каскада | formalized |
| Планирование | `U.Method` | PD.METHOD.009 | Год → день | formalized |
| Каскад планирования | `U.Method` | PD.METHOD.009 | Уровни планов | formalized |
| WeekPlan | `U.WorkPlan` | DP.M.008 | Расписание недели | — |
| DayPlan | `U.WorkPlan` | DP.M.008 | Расписание дня | — |
| Правило 3 приоритетов | `U.Method` | docs | Фокус против перегрузки | formalized |
| Микрорешение | `U.Method` | docs | Малый итеративный шаг | formalized |
| Управление тремя потоками | `U.Method` | PD.METHOD.023 | Tame Flow адаптация | formalized |
| Месячный аудит | `U.Method` | DP.M.008 § Month Close | Замкнутый цикл развития | formalized |
| Личный стиль саморазвития | `U.Episteme` | docs | Индивидуальная комбинация методов | formalized |
| Чтение для информации | `U.Method` | docs (антитеза 1-2 § 3) | Антипод медленного чтения | formalized |
| Жаргон | `U.Episteme` | docs 1-2 § 5 | Антитеза «бытовому языку» | formalized |

### Руководство 3 — IWE: работа и развитие

| Понятие | parent (U.*) | Источник | Комментарий | Статус |
|---------|--------------|----------|-------------|
| IWE | `U.System` | DP.IWE.* | Интеллектуальное рабочее окружение | formalized |
| 4 природы IWE | `U.Kind` | DP.IWE.001 | Наставник + мастерская + сотворец + аватар — классификация видов | formalized |
| Pack | `U.BoundedContext` | SPF.SPEC.002, DP.D.* | Семантическая рамка | formalized |
| DS (Derivative System) | `U.System` | SPF.SPEC.002 | Производное окружение | formalized |
| ZP / SPF / FPF (как уровни) | `U.Episteme` | SPF.SPEC.002 | Уровни мета-онтологии | formalized |
| Иерархия знаний | `U.Episteme` | SPF.SPEC.002 § 1.1 | ZP→SPF→FPF→Pack→DS | formalized |
| Манифест Pack | `U.Episteme` | PACK-template | Корневой документ Pack | formalized |
| Сущность Pack (M, WP, FAIL, D, R, CHR, SOTA, MAP, SC, FORM, STATE, QUAL) | `U.Kind` | SPF.SPEC.002 § 3 | Виды сущностей Pack | formalized |
| Семейство документов | `U.Kind` | SPF | Группа однотипных документов | formalized |
| Шаблон | `U.MethodDescription` | SPF | Заготовка-рецепт | formalized |
| Артефакт | `U.Work` | FPF A.7 | Носитель знания — производное рабочего действия | formalized |
| ADR (Architectural Decision Record) | `U.Work` | DP.ARCH.* | Запись архитектурного решения | formalized |
| АрхГейт | `U.Method` | DP.M.008 § АрхГейт | Оценка по 7 характеристикам | formalized |
| Агент | `U.System` | DP.ROLE.* | Модель + контекст + инструменты — автономная система, не просто роль | formalized |
| MCP (Model Context Protocol) | `U.System` | (cited Anthropic) | Протокол интеграции | formalized |
| Тип агента | `U.Kind` | DP.D.048 | Скрипт vs Агент | formalized |
| IntegrationGate | `U.Method` | DP.M.008 § 8 | Контракт подключения нового агента | formalized |
| Контур (агента) | `U.BoundedContext` | DP.ROLE.* | Граница ответственности | formalized |
| Контекстная изоляция | `U.Method` | DP.M.008 § 10 | Защита от загрязнения контекста | formalized |
| Экзоскелетный режим | `U.Episteme` | DP.M.008 § 11, DP.D.046 | ИИ усиливает, не заменяет | formalized |
| Автопилот (антипаттерн) | `U.Method` | DP.D.046 | Антипод экзоскелетного режима — LLM действует без участия пилота | formalized |
| Замещение | `U.Method` | DP.D.046 | Антипод делегирования с сохранением навыка | formalized |
| Когнитивная независимость | `U.Characteristic` | DP.D.046 | Тест: «уберу ИИ — останется ли навык?» | formalized |
| ОРЗ (Открытие-Работа-Закрытие) | `U.Method` | DP.M.008 § 1 | Базовый протокол | formalized |
| Архитектура внимания | `U.System` | DP.M.008 | Система управления вниманием: структура из ролей, сигналов, приоритетов | formalized |
| Стоп-кран | `U.Method` | DP.M.008 § 8 | Pre-action gate | formalized |
| Pre-action gate | `U.Method` | DP.M.008 § 8 | Проверка перед действием | formalized |
| Критерий приёмки | `U.Episteme` | FPF A.10 | Свойство рабочего продукта | formalized |
| Capture-to-Pack | `U.Method` | DP.M.008 § 6 | Захват знания на рубеже | formalized |
| Knowledge Extraction | `U.Method` | DP.AISYS.013 | Извлечение паттернов в Pack | formalized |
| Различение (Pack-сущность D) | `U.Kind` | SPF.SPEC.002 § 3 (D) | Вид документа в Pack, фиксирующего концептуальную границу (≠ Различение (FPF) → U.Episteme) | formalized |
| Паттерн | `U.Kind` | Capture-to-Pack | Вид наблюдения: повторяющаяся регулярность, идентифицируемая как класс | formalized |
| Мультиагентность | `U.Method` | DP.M.008 § 10 | Несколько моделей | formalized |
| Делегирование вниз | `U.Method` | DP.M.008 § 10 | Opus → Sonnet → Haiku | formalized |
| Мультисессионность | `U.Method` | DP.M.008 § 9 | Параллельные сессии | formalized |
| Многозадачность (антипаттерн) | `U.Method` | DP.M.008 § 9 | Антипод мультисессионности: хаотичное переключение без carry-over | formalized |
| Мультипликатор времени | `U.Characteristic` | DP.M.008 § 9 | Сумма закрытых РП / WakaTime | formalized |
| Бюджет РП | `U.WorkPlan` | DP.M.008 | Плановое время | formalized |
| Фокусный РП | `U.Kind` | DP.M.008 § 9 | Тип РП ≥1h | formalized |
| Coordination cost | `U.Characteristic` | DP.M.008 § 9 | Накладные расходы параллелизма | formalized |
| ТО (Техническое обслуживание) | `U.Method` | DP.M.008 § 12 | Журнал паттернов | formalized |
| Журнал паттернов | `U.Work` | DP.M.008 § 12 | Артефакт ТО | formalized |
| Эволюция системы (4 вопроса) | `U.Method` | DP.M.008 § 14 | Ежедневная ретро | formalized |
| Стоп-лист | `U.Method` | DP.M.008 § 13 | Критерии прерывания | formalized |
| Full Kitting | `U.Method` | Tame Flow / D-004 | Предварительная подготовка | formalized |
| Стоп-момент | `U.Method` | PD.FORM.051 | Точка осознанного выбора | formalized |
| Drift-detection | `U.Method` | DP.M.008 § 4 | Проверка Pack ↔ DS | formalized |
| Хук (Git/Claude) | `U.MethodDescription` | DP.M.008 | Автоматизация | formalized |
| Алерт / Обратная связь от машины | `U.Episteme` | DP.M.008 | Сигнал расхождения | formalized |
| Контекстное окно | `U.Characteristic` | (cited LLM) | Размер ввода LLM | formalized |
| Prompt | `U.MethodDescription` | (cited LLM) | Промпт-инструкция | formalized |
| Context Engineering | `U.Method` | SOTA.002 | Проектирование контекста | formalized |
| Эпистемический граф | `U.Episteme` | DS-Knowledge-Index | Граф знаний с epistemic_status | formalized |
| Epistemic status | `U.Characteristic` | DS-Knowledge-Index | Статус достоверности (гипотеза/факт) | formalized |

### Руководство 4 — Введение в системное мышление

| Понятие | parent (U.*) | Источник | Комментарий | Статус |
|---------|--------------|----------|-------------|
| Системное мышление | `U.Method` | docs 1-3, FPF A.7 | Инструмент анализа | formalized |
| Различение (трансдисциплинарное) | `U.Episteme` | FPF A.7 | Атом мышления | formalized |
| Граница системы | `U.Boundary` | FPF A.1 | Линия раздела | formalized |
| Окружение системы | `U.System` | FPF A.1 | Внешние системы | formalized |
| Эмерджентность | `U.Episteme` | FPF C.* | Новые свойства целого | formalized |
| Системный уровень | `U.Kind` | FPF A.9 | Уровень в иерархии | formalized |
| Функциональный объект | `U.Kind` | FPF A.7 | Объект, определённый функцией | formalized |
| Физический объект | `U.Kind` | FPF A.7 | Материальное воплощение | formalized |
| Воплощение системы | `U.System` | FPF A.7 | Физическое существование | formalized |
| Описание системы | `U.Episteme` | FPF A.7 | Ментальное представление | formalized |
| Документация системы | `U.Work` | FPF A.7 | Артефакт описания | formalized |
| Ролевое описание | `U.Episteme` | FPF A.2 | Описание через роль | formalized |
| Концепция использования | `U.Episteme` | docs | Как система применяется | formalized |
| Модули взаимодействия | `U.System` | docs | Внешние интерфейсы | formalized |
| Предмет интереса | `U.Episteme` | docs (Левенчук) | Область внимания роли | formalized |
| Ролевой интерес | `U.Episteme` | docs | Интерес роли (не личный) | formalized |
| Потребность | `U.Episteme` | docs | Что система должна обеспечить | formalized |
| Требование | `U.Commitment` | docs | Проверяемое утверждение | formalized |
| Ограничение (системное) | `U.Episteme` | docs / Tame Flow | Условие функционирования | formalized |
| Предприниматель | `U.RoleAssignment` | docs | Роль видения | formalized |
| Инженер | `U.RoleAssignment` | docs | Роль проектирования | formalized |
| Менеджер | `U.RoleAssignment` | docs | Роль организации ресурсов | formalized |
| Архитектор предприятия | `U.RoleAssignment` | docs | Уровень оргсистемы | formalized |
| Директор по развитию | `U.RoleAssignment` | docs | Управление эволюцией | formalized |
| Проектировщик организации | `U.RoleAssignment` | docs | Оргструктуры | formalized |
| Продукт | `U.Work` | docs | Передаваемый получателю | formalized |
| Услуга | `U.ServiceClause` | SPF | Контракт сервиса | formalized |
| Целевая система | `U.System` | FPF A.1 | Для которой создаётся решение | formalized |
| Надсистема | `U.System` | FPF A.1 | Содержащая целевую | formalized |
| Подсистема | `U.System` | FPF A.1 | Компонент целевой | formalized |
| Система создания | `U.System` | FPF A.3 | Создающая целевую | formalized |
| Цепочка создания | `U.System` | FPF | Pipeline создания | formalized |
| Мета-системный переход | `U.Method` | docs | Переход на уровень выше | formalized |
| 4 вопроса разбора | `U.Method` | docs | Зачем, что, как, когда | formalized |
| Системная карта | `U.Work` | docs | Артефакт разбора | formalized |
| Таблица 3×3 | `U.Episteme` | docs | Роли × системы | formalized |
| Процесс | `U.Method` | FPF | Не система | formalized |
| Проект | `U.Work` | FPF A.15 | Временная деятельность | formalized |
| Стадия / Этап | `U.Kind` | docs | Уровни жизненного цикла | formalized |
| Ключевая сущность проекта (альфа) | `U.Kind` | docs (Essence) | Объект, состояние которого = зрелость | formalized |
| Рабочий продукт | `U.Work` | SPF (WP) | Уже в Pack | formalized |
| Приёмка | `U.Method` | docs | Соответствие критериям | formalized |
| Валидация | `U.Method` | docs | «Делаем правильную вещь» | formalized |
| Верификация | `U.Method` | docs | «Делаем вещь правильно» | formalized |
| Чёрный ящик | `U.Episteme` | FPF A.7 | Внешнее описание | formalized |
| Прозрачный ящик | `U.Episteme` | FPF A.7 | Внутреннее описание | formalized |
| Виды описаний (4 типа) | `U.Episteme` | FPF | Функциональное/модульное/пространственное/стоимостное | formalized |
| Модель | `U.Episteme` | FPF | Базовое описание | formalized |
| Мета-модель | `U.Episteme` | docs | Модель моделей | formalized |
| Мульти-модель | `U.Episteme` | docs | Множество моделей | formalized |
| Интегральная (мега-) модель | `U.Episteme` | docs | Сборка моделей | formalized |
| Интерфейс | `U.Episteme` | FPF | Правила взаимодействия | formalized |
| Tame Flow | `U.Method` | (cited Tendon) | Метод операционного менеджмента | formalized |
| Закон Литтла | `U.Episteme` | (cited) | WIP = Flow Time × Throughput | formalized |
| Flow Time / Lead Time | `U.Characteristic` | Tame Flow | Время процесса | formalized |
| Touch Time | `U.Characteristic` | Tame Flow | Активное время | formalized |
| Wait Time | `U.Characteristic` | Tame Flow | Ожидание | formalized |
| Flow Efficiency | `U.Characteristic` | Tame Flow | Touch/Flow | formalized |
| WIP | `U.Characteristic` | Tame Flow | Незавершённая работа | formalized |
| Five Focusing Steps | `U.Method` | (cited Goldratt) | 5 шагов TOC | formalized |
| Трихотомия ограничений | `U.Episteme` | Tame Flow | WF/WP/WE constraint | formalized |
| Throughput Accounting | `U.Method` | (cited Goldratt) | T/I/OE | formalized |
| Inventory (T/I/OE) | `U.Characteristic` | Tame Flow | Незавершённый капитал | formalized |
| Evaporating Cloud | `U.Method` | (cited Goldratt) | Разрешение конфликта | formalized |
| Negative Branch Reservation | `U.Method` | (cited Goldratt) | Проверка рисков | formalized |
| Скрытое допущение | `U.Episteme` | Goldratt | Основа конфликта | formalized |
| Поток работ / поток ценности | `U.Flow` | Tame Flow | Движение РП | formalized |
| Безмасштабность | `U.Episteme` | SST 3.0 | Универсальность системного подхода | formalized |
| Деантропоморфность | `U.Episteme` | SST 3.0 | Отказ от антропоцентризма | formalized |
| Системный подход 1.0 / 2.0 / 3.0 | `U.Episteme` | docs (Левенчук) | Поколения СП | formalized |

---

## Кандидаты на расширение SPF (нет родителя U.*)

Эти концепты могут не находить чистого родителя из текущего SPF.SPEC.002 § 2. Решение принимает Knowledge Extractor (возможно, нужно поднимать в FPF):

| Концепт | Гипотеза | Что предложить SPF/FPF |  | — |
|---------|----------|------------------------|
| Эмерджентное свойство (как самостоятельный концепт) | `U.Episteme`? `U.Characteristic`? | Уточнить связь с FPF C.* эмерджентностью |  | — |
| Эпистемический статус (как тип) | `U.Characteristic`? | Возможно расширение FPF A.10 (Evidence Graph) |  | — |
| Mental model (Tame Flow) | `U.Episteme`? | Уточнить отношение к `U.Episteme` |  | formalized |

---

*Следующий шаг: пилот ревизует список (понятие / кейс / аналогия) → Knowledge Extractor (DP.AISYS.013) формализует утверждённые понятия в `PACK-personal/ontology.md` § 2.*
