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
prerequisites: [PD.GUIDE.1.S1.SS99]
can_do:
  - "Знать понятие Х"
cp_check: [cp.unknownslot]
bh_check: [bh.fakemetric]
```

**Понятия:**
- вводится: Понятие-Х → `U.Episteme`
- неизвестно: Х какая-то метка
- вводится: (опечатка-в-имени) → `U.System`

**Содержание:** Текст подраздела.

---

### 1.03 Третий подраздел — SS2 пропущен

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
- вводится: Понятие-Х → `U.Method`

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
- вводится: Десятое понятие → `U.System`
