---
id: PD.GUIDE.1.STRUCTURE
title: "Тестовая СЛОМАННАЯ структура — содержит все типичные нарушения"
status: draft
---

# Сломанная структура — все типичные нарушения

## Раздел 1. Раздел один (нарушение: SS пропущен; can_do не с «Могу»)

```yaml
section_id: PD.GUIDE.1.S1
title: "Раздел один"
order: 1
stage_relevant: [1]
cp_check: [cp.wld]
bh_check: [bh.awr]
```

### 1.01 Первый подраздел

```yaml
subsection_id: PD.GUIDE.1.S1.SS1
title: "Первый подраздел"
mastery_node: [саморазвитие]
stage_relevant: [1]
introduces: ["U.Episteme", "Понятие-Х"]
uses: []
prerequisites: [PD.GUIDE.1.S99.SS99]
can_do:
  - Знать понятие Х без «Могу»
cp_check: [cp.unknownslot]
bh_check: [bh.fakemetric]
```

**Понятия:**
- вводится: Понятие-Х → `U.Episteme`
- неизвестно: Х какая-то метка
- вводится: (опечатка-в-имени) → `U.System`
- используется: Сирота-без-определения → `U.Method`
- сослан: Машина → 1.S2.SS1
- произвольная строка-без-маркера

**Содержание:** Текст подраздела.

---

### 1.02 Подраздел с превышением A.11 (4 понятия «вводится»)

```yaml
subsection_id: PD.GUIDE.1.S1.SS2
title: "Перебор понятий"
mastery_node: [iwe]
stage_relevant: [1]
introduces: ["А", "Б", "В", "Г"]
uses: []
prerequisites: []
can_do:
  - "Могу применить четыре понятия одновременно"
cp_check: [cp.iwe]
bh_check: [bh.met]
```

**Понятия:**
- вводится: Понятие-А → `U.Episteme` (PD.FORM.001)
- вводится: Понятие-Б → `U.Episteme` (PD.FORM.002)
- вводится: Понятие-В → `U.Episteme` (PD.FORM.003)
- вводится: Понятие-Г → `U.Episteme` (PD.FORM.004)

---

### 1.03 Третий подраздел — SS2 пропущен (на самом деле — SS3)

```yaml
subsection_id: PD.GUIDE.1.S1.SS3
title: "Третий подраздел"
mastery_node: [несуществующий-узел]
stage_relevant: [9]
introduces: []
uses: []
prerequisites: []
can_do: []
cp_check: []
bh_check: []
```

**Понятия:**
- вводится: Понятие-Y → `U.Method`

**Содержание:** ...

---

### 1.05 Подраздел с кейсом-в-introduces (SS4 пропущен)

```yaml
subsection_id: PD.GUIDE.1.S1.SS5
title: "Земмельвейс как понятие — ошибка"
mastery_node: [саморазвитие]
stage_relevant: [2]
introduces: ["Эффект Земмельвейса"]
uses: []
prerequisites: []
can_do:
  - "Могу распознать сопротивление простой практике"
cp_check: [cp.wld]
bh_check: [bh.awr]
```

**Понятия:**
- вводится: Эффект Земмельвейса → `U.Episteme` (PD.FORM.099)
- вводится: Хохланд → `U.System` (PD.FORM.099)

**Содержание:** Кейс ошибочно помечен как `вводится`.

---

## Раздел 2. Раздел два — омоним: Понятие-Х с другим parent

```yaml
section_id: PD.GUIDE.1.S2
title: "Раздел два"
order: 2
stage_relevant: [2]
cp_check: [cp.wld]
bh_check: [bh.awr]
```

### 2.01 Подраздел омонима

```yaml
subsection_id: PD.GUIDE.1.S2.SS1
title: "Подраздел омонима"
mastery_node: [саморазвитие]
stage_relevant: [2]
introduces: ["Понятие-Х"]
uses: []
prerequisites: []
can_do:
  - "Могу применить понятие Х"
cp_check: [cp.wld]
bh_check: [bh.awr]
```

**Понятия:**
- вводится: Понятие-Х → `U.Method` (PD.FORM.099)

**Содержание:** Тут понятие-Х уже как Method — омоним с раздела 1.

---

## Раздел 10. Десятый раздел (тест на сортировку — должен быть после раздела 2)

```yaml
section_id: PD.GUIDE.1.S10
title: "Десятый раздел"
order: 10
stage_relevant: [5]
cp_check: [cp.agt]
bh_check: [bh.agn]
```

### 10.01 Подраздел десятого

```yaml
subsection_id: PD.GUIDE.1.S10.SS1
title: "Подраздел десятого"
mastery_node: [iwe]
stage_relevant: [5]
introduces: ["Десятое понятие"]
uses: []
prerequisites: []
can_do:
  - "Могу..."
cp_check: [cp.agt]
bh_check: [bh.agn]
```

**Понятия:**
- вводится: Десятое понятие → `U.System` (PD.METHOD.099)
