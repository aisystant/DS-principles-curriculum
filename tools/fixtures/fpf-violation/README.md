# Fixture: FPF violations (Ф14 тест)

Намеренные FPF-нарушения для теста `verify-fpf-subsection` vs `verify-pedagogy-subsection`.

## Файлы

- `1-1-1-fpf-fail.md` — SS с явными FPF-нарушениями, педагогика не нарушена

## Нарушения в `1-1-1-fpf-fail.md`

| Блок | Пункт | Нарушение |
|------|-------|-----------|
| G | G.2 | Тавтология: «развитие — это процесс развития себя» |
| H | H.1 | Нет цепочки мем→метод→мировоззрение: сразу «метод развития» без мема |
| H | H.3 | Обрыв без моста: нет «что дальше» |
| H | H.4 | Нет формулировки мировоззренческого сдвига |

## Ожидаемый результат теста

```
/verify-fpf-subsection tools/fixtures/fpf-violation/1-1-1-fpf-fail.md
→ FAIL (G.2 критический, H.1/H.3/H.4 высокие)

/verify-pedagogy-subsection tools/fixtures/fpf-violation/1-1-1-fpf-fail.md
→ PASS (педагогические параметры корректны)
```
