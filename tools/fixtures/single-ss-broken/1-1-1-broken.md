---
subsection_id: PD.GUIDE.1.S1.SS1
title: "Образец некорректного одиночного SS"
mastery_node: [саморазвитие]
stage_relevant: [1, 2]
introduces: ["Нормальное понятие", "PD.FORM.089", "cp.wld"]
uses: []
prerequisites: ["§1.05", "PD.GUIDE.1.S1.SS999"]
can_do:
  - "Могу что-то"
cp_check: [cp.wld]
bh_check: [bh.awr]
---

# Образец некорректного одиночного SS

Этот фикстюр должен вызывать 4 FAIL:
- A.10: `PD.FORM.089` в `introduces` (шифр Pack)
- A.10: `cp.wld` в `introduces` (RCS-индекс)
- A.11: `§1.05` в `prerequisites` (legacy формат)
- B.9: отсутствует `format_version` (main подраздел)
