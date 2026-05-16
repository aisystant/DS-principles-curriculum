---
id: PD.GUIDE.1.STRUCTURE
title: "Тестовая валидная структура руководства 1"
status: draft
---

# Тестовая валидная структура руководства 1

## Раздел 1. Тест-раздел

```yaml
section_id: PD.GUIDE.1.S1
title: "Тест-раздел"
order: 1
stage_relevant: [1, 2, 3]
cp_check: [cp.wld]
bh_check: [bh.awr]
```

### 1.01 Первый подраздел

```yaml
subsection_id: PD.GUIDE.1.S1.SS1
title: "Первый подраздел"
mastery_node: [саморазвитие]
stage_relevant: [1, 2]
introduces: ["Тестовое понятие А"]
uses: []
prerequisites: []
can_do:
  - "Могу объяснить тестовое понятие А своими словами"
cp_check: [cp.wld]
bh_check: [bh.awr]
bottleneck_hint: "Если застрял — проверь cp.wld"
```

**Понятия:**
- вводится: Тестовое понятие А → `U.Episteme` (PD.FORM.001)

**Содержание:** Описание тестового понятия А.

**Практика (15 мин):** Записать применение.

---

### 1.02 Второй подраздел

```yaml
subsection_id: PD.GUIDE.1.S1.SS2
title: "Второй подраздел"
mastery_node: [мыслительное]
stage_relevant: [2, 3]
introduces: ["Тестовое понятие Б"]
uses: ["Тестовое понятие А — см. 1.S1.SS1"]
prerequisites: [PD.GUIDE.1.S1.SS1]
can_do:
  - "Могу связать понятие Б с понятием А"
cp_check: [cp.int]
bh_check: [bh.met]
bottleneck_hint: "Если застрял — проверь cp.int"
```

**Понятия:**
- вводится: Тестовое понятие Б → `U.Method` (PD.METHOD.002)
- используется: Тестовое понятие А — см. 1.S1.SS1

**Содержание:** Связь Б с А.

**Практика (15 мин):** Применить.

---

## Раздел 2. Второй раздел

```yaml
section_id: PD.GUIDE.1.S2
title: "Второй раздел"
order: 2
stage_relevant: [3]
cp_check: [cp.skl]
bh_check: [bh.inv]
```

### 2.01 Подраздел второго раздела

```yaml
subsection_id: PD.GUIDE.1.S2.SS1
title: "Подраздел второго раздела"
mastery_node: [саморазвитие]
stage_relevant: [3]
introduces: ["Тестовое понятие В"]
uses: []
prerequisites: []
can_do:
  - "Могу применить понятие В в практике"
cp_check: [cp.skl]
bh_check: [bh.inv]
```

**Понятия:**
- вводится: Тестовое понятие В → `U.Capability` (PD.CAT.003)
- кейс в тексте: Земмельвейс как иллюстрация сопротивления

**Содержание:** Описание.

**Практика (15 мин):** Применить.
