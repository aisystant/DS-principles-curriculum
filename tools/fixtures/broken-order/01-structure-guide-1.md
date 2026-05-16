---
id: PD.GUIDE.1.STRUCTURE
title: "Фикстура для проверки численной сортировки разделов"
status: draft
---

# Численная сортировка нарушена: S1, S10, S2

## Раздел 1. Первый

```yaml
section_id: PD.GUIDE.1.S1
title: "Первый"
order: 1
stage_relevant: [1]
cp_check: [cp.wld]
bh_check: [bh.awr]
```

### 1.01 Подраздел

```yaml
subsection_id: PD.GUIDE.1.S1.SS1
title: "Подраздел"
mastery_node: [саморазвитие]
stage_relevant: [1]
introduces: ["А"]
uses: []
prerequisites: []
can_do:
  - "Могу А"
cp_check: [cp.wld]
bh_check: [bh.awr]
```

**Понятия:**
- вводится: А → `U.Episteme`

---

## Раздел 10. Десятый — НЕ ДОЛЖЕН быть на этом месте при численной сортировке

```yaml
section_id: PD.GUIDE.1.S10
title: "Десятый"
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
introduces: ["Десятое"]
uses: []
prerequisites: []
can_do:
  - "Могу десятое"
cp_check: [cp.agt]
bh_check: [bh.agn]
```

**Понятия:**
- вводится: Десятое → `U.System`

---

## Раздел 2. Второй — должен быть до десятого

```yaml
section_id: PD.GUIDE.1.S2
title: "Второй"
order: 2
stage_relevant: [2]
cp_check: [cp.wld]
bh_check: [bh.awr]
```

### 2.01 Подраздел второго

```yaml
subsection_id: PD.GUIDE.1.S2.SS1
title: "Подраздел второго"
mastery_node: [саморазвитие]
stage_relevant: [2]
introduces: ["Б"]
uses: []
prerequisites: []
can_do:
  - "Могу Б"
cp_check: [cp.wld]
bh_check: [bh.awr]
```

**Понятия:**
- вводится: Б → `U.Method`
