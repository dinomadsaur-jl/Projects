```markdown
# BOOK MERGE: PRESERVATION MODE
**Title:** [BOOK]  
**Author:** [AUTHOR]

**CRITICAL:** Preserve ALL HTML formatting, code syntax, math notation exactly as provided.

---

## RUNNING DOCUMENTS (Maintain after each chunk)
- **ELEMENT_REGISTRY:** `{headings: [], code_blocks: {lang, lines}, formulas: {type, count}, tables: [], ids: []}`
- **CROSS_REFS:** `{links: [], targets: [], figure_nums: []}`
- **ISSUE_LOG:** [corruptions, boundary breaks]

---

## PROCESSING RULES
- Chunks overlap by last 2-3 paragraphs
- Compare new chunk with registry before merging
- Flag any malformed HTML immediately
- Track continuity for code/formulas spanning chunks

---

## FORMAT PRESERVATION
- **LaTeX:** Keep `\(...\)` and `$$...$$` intact
- **MathML:** Preserve all `<math>` tags
- **Code:** Maintain indentation, classes, line numbers
- **Tables:** Keep structure, merging, formatting

---

## OUTPUT AFTER EACH CHUNK
```

CHUNK [N]: pages [X-Y]
+Registry updates: [summary]
+Issues: [count] → [details]
+Ready for next? [Y/N]

```

---

## CHUNK SUBMISSION TEMPLATE
```

Chunk [N]: pages [X-Y] (overlap: last [Z] paras)
Special: [formulas/code/tables on pX]
HTML:
[paste]

```

---

## RECOVERY SHORTCUTS
- **CORRUPTION:** Stop. Rebuild from [point] using raw: [paste]
- **FORMULA:** Show raw HTML for [area]. Restore exact.
- **CODE:** Restore [block] with original indentation from chunk [N]

---

## FINAL MERGE
```

All chunks done. Export complete HTML + validation:

· Formulas intact: [Y/N] (issues:)
· Code preserved: [Y/N]
· References resolved: [Y/N]

```

---

**INITIAL CONFIRMATION NEEDED:** Reply "READY" and I'll send Chunk 1.
```

Copy this entire markdown block and use it as your prompt!