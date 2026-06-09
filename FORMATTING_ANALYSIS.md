# Formatting Analysis and Implementation Options

## Executive Summary

Analysis of 15 Word documents reveals extensive use of **bold**, *italic*, and `code` (monospace) formatting across all extracts. The current conversion script (`convert_docx.py`) **ignores all inline formatting**, converting only paragraph-level styles.

### Key Findings

- **598 bold runs** across all documents
- **199 italic runs** across all documents  
- **5 code/verbatim runs** (Courier New font)
- **53 combined bold+italic runs**
- **2 combined bold+code runs** (ISO 14823-1 only)
- **1 combined italic+code run** (ISO 14823-1 only)
- **2 underline runs** (rare, appears to be unintentional)

Only **ISO 14823-1** uses monospace/verbatim formatting for technical identifiers like OIDs.

---

## Current Behavior

The `render_paragraph()` function (convert_docx.py:229-244) processes paragraphs as plain text:

```python
def render_paragraph(p) -> str:
    style = p.style.name or ""
    txt = clean(p.text).replace("\t", " — ")  # ← loses all run-level formatting
    ...
```

**Example from ISO 14823-1, Clause 7.3:**

**Source (Word):**
> describes the OID hierarchy registered under `{joint-iso-itut(2) its(28) gdd(5)}` and...

**Current output (Markdown):**
> describes the OID hierarchy registered under {joint-iso-itut(2) its(28) gdd(5)} and...

The monospace formatting is lost.

---

## Use Cases by Category

### 1. Bold Formatting

**Primary uses:**
- **Term definitions** (e.g., "**Graphic Data Dictionary (GDD)**")
- **Emphasized concepts** (e.g., "**efficient transmission**, **interpretation**, and **display**")
- **Cross-references** (e.g., "**Table 1**", "**Clause 7.3**")
- **Document structure** (e.g., "**current**" vs "**deprecated**")

**Frequency:** Very high (598 instances). Appears in every document.

**Semantic value:** High — distinguishes key terms and improves readability.

### 2. Italic Formatting

**Primary uses:**
- **Standard boilerplate** (e.g., "*This Extract does not replace...*")
- **Notes and asides** (e.g., "*Note: This Extract presents...*")
- **References to external resources** (e.g., "*ITS Terminology*", "*StandardLand*")
- **Emphasis within technical expressions** (e.g., "*chapters*", "*numbering*")

**Frequency:** Medium (199 instances). Appears in every document.

**Semantic value:** Medium — aids skimmability, but often redundant with paragraph style.

### 3. Monospace/Code Formatting (Courier New)

**Primary uses:**
- **Technical identifiers** (e.g., `{joint-iso-itut(2) its(28) gdd(5)}`)
- **Code-like expressions** (e.g., `trafficSign (1) + regulatory (2) + mandatory (7) + xx`)
- **Formal syntax** (e.g., `{1 2 7 xx}`)

**Frequency:** Very low (5 instances, only in ISO 14823-1).

**Semantic value:** High where present — critical for distinguishing formal syntax from prose.

### 4. Combined Formatting

**Bold+Italic:**
- Mostly the **annotation line** ("*This Extract does not replace...*") which appears **bolded and italicized** in some documents.
- Some **mathematical symbols** or **special variables** (e.g., *θH*, *θV* in ISO 21214).

**Italic+Code:**
- `trafficSign (1) + regulatory (2) + mandatory (7) + xx` — a technical expression in both italic and monospace (ISO 14823-1:49).

**Bold+Code:**
- `{1 2 7 xx}` — a formal identifier in bold monospace (ISO 14823-1:49).

**Frequency:** Low (56 combined instances total).

**Semantic value:** Variable — annotation is stylistic; technical symbols are semantic.

### 5. Underline

**Frequency:** Negligible (2 instances across 15 docs).

**Semantic value:** None — appears accidental.

---

## Implementation Options

### Option 1: Full Inline Formatting Conversion

**Description:**  
Convert all run-level formatting to Markdown equivalents:
- Bold → `**text**`
- Italic → `*text*`
- Monospace → `` `text` ``
- Bold+Italic → `***text***`
- Bold+Code → `` **`text`** ``
- Italic+Code → `` *`text`* ``

**Implementation:**
Rewrite `render_paragraph()` to iterate over `paragraph.runs` and emit Markdown formatting per run.

```python
def render_paragraph(p) -> str:
    style = p.style.name or ""
    chunks = []
    
    for run in p.runs:
        text = clean(run.text)
        if not text:
            continue
        
        # Detect monospace fonts
        is_code = run.font.name and run.font.name.lower() in [
            'courier', 'courier new', 'consolas', 'monaco'
        ]
        
        # Apply Markdown formatting
        if run.bold and run.italic and is_code:
            text = f"***`{text}`***"
        elif run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold and is_code:
            text = f"**`{text}`**"
        elif run.italic and is_code:
            text = f"*`{text}`*"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        elif is_code:
            text = f"`{text}`"
        
        chunks.append(text)
    
    txt = ''.join(chunks).replace("\t", " — ")
    
    # Apply paragraph-level styles as before
    if style.startswith("Heading") or style == "Nadpis":
        ...
```

**Pros:**
- Maximum fidelity to source documents
- Preserves all semantic distinctions (terms, references, technical syntax)
- Improves readability and navigation in mdBook output
- Future-proof for documents with richer formatting

**Cons:**
- **Complexity:** More code to maintain; edge cases (nested formatting, whitespace, special chars)
- **Markdown noise:** Heavy formatting may clutter source files
- **Rendering quirks:** mdBook may render `` **`code`** `` inconsistently
- **Breaking change:** Existing output files will change (requires review)

**Risk level:** Medium

---

### Option 2: Selective Formatting (Code + Bold Terms)

**Description:**  
Convert only:
1. **Monospace → backticks** (`` `text` ``)
2. **Bold for term definitions** (detect first occurrence in a clause)

Skip italic and other bold uses.

**Implementation:**
Same as Option 1, but:
```python
if is_code:
    text = f"`{text}`"
elif run.bold and is_definition_context(p, run):  # heuristic
    text = f"**{text}**"
```

**Pros:**
- **Lower noise:** Only formats what's semantically critical
- **Easier to implement:** Fewer edge cases
- **Preserves technical syntax** (the primary user complaint)

**Cons:**
- **Heuristics required:** Detecting "definition context" is non-trivial
- **Inconsistency:** Some bold terms formatted, others not
- **User confusion:** "Why is *this* bold but not *that*?"

**Risk level:** Medium-High (heuristics may fail)

---

### Option 3: Code-Only Formatting

**Description:**  
Convert only monospace/code formatting; ignore bold and italic entirely.

**Implementation:**
```python
for run in p.runs:
    text = clean(run.text)
    if not text:
        continue
    
    is_code = run.font.name and run.font.name.lower() in [
        'courier', 'courier new', 'consolas', 'monaco'
    ]
    
    if is_code:
        text = f"`{text}`"
    
    chunks.append(text)
```

**Pros:**
- **Minimal change:** Addresses the specific example (OID formatting)
- **Low risk:** Monospace is unambiguous and rare
- **Easy to test:** Only 5 instances across all docs

**Cons:**
- **Limited benefit:** Doesn't improve readability for bold/italic terms
- **Incomplete solution:** Doesn't address term definitions, cross-references

**Risk level:** Low

---

### Option 4: No Formatting Conversion (Status Quo)

**Description:**  
Keep the current behavior; document the limitation.

**Pros:**
- **Zero implementation cost**
- **No breaking changes**
- **No risk of introducing bugs**

**Cons:**
- **User complaint remains unaddressed**
- **Lost semantic information** (especially for ISO 14823-1)
- **Reduced readability** in mdBook output

**Risk level:** None (but user dissatisfaction)

---

## Edge Cases and Risks

### 1. Markdown Escaping
**Problem:** If a bold run contains `*`, `_`, or backticks, the output Markdown may break.

**Example:**
- Word: **`foo*bar`** (bold, monospace)
- Naive output: `` **`foo*bar`** ``
- Rendered: **`foo*bar`** (works in most parsers)

**Mitigation:** Escape special characters inside backticks if needed.

---

### 2. Whitespace Preservation
**Problem:** Word runs often split mid-word due to formatting changes. Joining them naively may lose spaces.

**Example:**
- Run 1: "hello " (normal)
- Run 2: "world" (bold)
- Naive: "hello **world**" ✓
- Run 1: "hello" (normal)
- Run 2: " " (normal)
- Run 3: "world" (bold)
- Naive: "hello **world**" ✗ (missing space)

**Mitigation:** Preserve run text exactly; don't strip spaces inside formatting markers.

---

### 3. Nested Formatting
**Problem:** Markdown doesn't support arbitrary nesting (e.g., bold inside code).

**Example:**
- Word: `{1 2 **7** xx}` (monospace with bold "7")
- Markdown limitation: Can't represent this directly

**Mitigation:**
- **Option A:** Flatten to `` `{1 2 7 xx}` `` (lose bold)
- **Option B:** HTML fallback: `` `{1 2 <strong>7</strong> xx}` ``
- **Option C:** Ignore (very rare)

**Recommended:** Option A (flatten). This is extremely rare.

---

### 4. Table Cell Formatting
**Problem:** `cell_html()` (convert_docx.py:167-175) already ignores formatting inside tables.

**Impact:** If we add inline formatting to paragraphs, should we also add it to tables?

**Recommendation:** Separate decision. Tables use HTML `<br>`, so we could inject `<strong>`, `<em>`, `<code>` if needed. But this adds complexity to an already complex function.

**Suggested approach:** Start with paragraphs only; add table support in a future iteration if needed.

---

### 5. Performance
**Problem:** Iterating over runs is slower than `paragraph.text`.

**Impact:** Negligible. The bottleneck is LibreOffice rasterization, not paragraph parsing.

---

### 6. Test Coverage
**Problem:** Current tests don't verify formatting preservation.

**Required new tests:**
1. **Unit test:** `render_paragraph()` with formatted runs → correct Markdown
2. **Integration test:** Real document with code formatting (ISO 14823-1) → output contains backticks
3. **Regression test:** Documents without special formatting → unchanged output

**Estimated effort:** 3-4 test cases

---

## Compatibility with mdBook

### Markdown Rendering
mdBook uses **pulldown-cmark** (CommonMark parser). Supported formatting:

| Word            | Markdown         | mdBook Rendering | Notes                          |
|-----------------|------------------|------------------|--------------------------------|
| Bold            | `**text**`       | **text**         | ✓ Full support                 |
| Italic          | `*text*`         | *text*           | ✓ Full support                 |
| Code            | `` `text` ``     | `text`           | ✓ Full support                 |
| Bold+Italic     | `***text***`     | ***text***       | ✓ Full support                 |
| Bold+Code       | `` **`text`** `` | **`text`**       | ⚠ Render as code, not bold[^1] |
| Italic+Code     | `` *`text`* ``   | *`text`*         | ⚠ Render as code, not italic[^1] |

[^1]: CommonMark prioritizes code over emphasis. `` **`text`** `` renders as `text` (monospace, no bold). This is a Markdown limitation, not a bug.

**Recommendation:** For combined bold+code or italic+code, choose which formatting to preserve. **Code is more semantically important** → use backticks alone.

---

## Recommended Approach

### Phase 1: Code-Only Formatting (Low Risk, High Value)
**Rationale:** Addresses the specific user complaint (ISO 14823-1 OID syntax) with minimal risk.

**Implementation:**
1. Modify `render_paragraph()` to detect Courier New font and emit backticks
2. Add unit test for code formatting
3. Add integration test for ISO 14823-1 (verify `{joint-iso-itut...}` becomes backticked)
4. Run `mise run all` and verify no breaking changes in other documents

**Effort estimate:** 2-3 hours (implementation + testing)

**Deliverable:** ISO 14823-1 output contains `` `{joint-iso-itut(2) its(28) gdd(5)}` ``

---

### Phase 2: Bold + Italic Formatting (Medium Risk, Medium Value)
**Rationale:** Improve readability for term definitions and cross-references.

**Implementation:**
1. Extend `render_paragraph()` to handle bold (`**`) and italic (`*`)
2. Add tests for bold-only, italic-only, and combined formatting
3. Review output for all 15 documents (spot-check key sections)
4. Document any edge cases discovered

**Effort estimate:** 4-6 hours (implementation + review)

**Deliverable:** All documents preserve inline formatting; readability improved in mdBook.

---

### Phase 3: Edge Case Refinement (Optional)
**Rationale:** Handle nested formatting, table cells, and escaping edge cases.

**Implementation:**
1. Add table cell formatting (modify `cell_html()`)
2. Add Markdown escaping for special characters
3. Comprehensive test suite (10+ test cases)

**Effort estimate:** 6-8 hours

**Deliverable:** Production-ready inline formatting with full test coverage.

---

## Decision Criteria

| Criterion                     | Option 1 (Full) | Option 2 (Selective) | Option 3 (Code-only) | Option 4 (None) |
|-------------------------------|-----------------|----------------------|----------------------|-----------------|
| **Addresses user complaint**  | ✓✓✓             | ✓✓                   | ✓                    | ✗               |
| **Improves readability**      | ✓✓✓             | ✓✓                   | ✓                    | ✗               |
| **Implementation complexity** | High            | Medium               | Low                  | None            |
| **Risk of breaking changes**  | Medium          | Medium-High          | Low                  | None            |
| **Future-proof**              | ✓✓✓             | ✓                    | ✓                    | ✗               |
| **Test coverage required**    | High            | High                 | Low                  | None            |

---

## Open Questions

1. **Should we convert bold+italic in the annotation line?**
   - Current behavior: Annotation is italicized by `frontmatter_preprocessor.py` (strips YAML, wraps in `*...*`)
   - If we also convert bold+italic in the source → `***..***` → conflict?
   - **Recommendation:** Let preprocessor handle annotation; skip bold+italic in source paragraph.

2. **Should we handle underline?**
   - Only 2 instances across 15 docs (likely accidental)
   - Markdown has no underline (could use HTML `<u>`, but unnecessary)
   - **Recommendation:** Ignore underline.

3. **Should we preserve formatting in table captions?**
   - Current behavior: `cell_html()` uses `clean(text)` (strips formatting)
   - Tables are already HTML, so we could inject `<strong>`, `<em>`, `<code>`
   - **Recommendation:** Defer to Phase 3 (low priority).

4. **How to handle formatting that spans multiple runs?**
   - Example: "**hello world**" might be two runs: "**hello **" + "**world**"
   - Naive: `**hello ****world**` (broken Markdown)
   - **Mitigation:** Merge adjacent runs with identical formatting before emitting Markdown.
   - **Recommendation:** Add run-merging logic in Phase 2.

---

## Summary

### Recommended Implementation Plan

**Immediate (Phase 1):** Implement **Option 3 (Code-only)**
- Addresses the specific user issue (ISO 14823-1 OIDs)
- Low risk, low effort
- Can be deployed immediately

**Short-term (Phase 2):** Implement **Option 1 (Full formatting)** minus edge cases
- Convert bold, italic, code, and common combinations
- Skip table cells and complex nesting
- Comprehensive testing before deployment

**Long-term (Phase 3):** Edge case refinement
- Table formatting
- Run merging
- Markdown escaping

**Estimated total effort:** 12-17 hours across all phases

---

## Next Steps

1. **User confirmation:** Does the user want full formatting or just code/verbatim?
2. **Prototype Phase 1:** Implement code-only conversion and test on ISO 14823-1
3. **Review output:** Share sample Markdown with user for approval
4. **Decide on Phase 2:** If user wants more formatting, proceed with bold/italic
5. **Update tests:** Add test cases for all implemented formatting

---

## Appendix: Sample Output Comparison

### Current Output (No Formatting)
```markdown
Clause 7.3 Relative object identifier (relative OID) describes the OID hierarchy 
registered under {joint-iso-itut(2) its(28) gdd(5)} and the way pictograms can be 
generalized according to the required level of detail.

Clause 7.5 Pictogram code and OID contains Table 1, which defines the structure 
and numbering of pictograms for version 1 in the form "service category → 
subcategory → nature → sequence number" (e.g. trafficSign (1) + regulatory (2) + 
mandatory (7) + xx ⇒ {1 2 7 xx}).
```

### Option 3 Output (Code-only)
```markdown
Clause 7.3 Relative object identifier (relative OID) describes the OID hierarchy 
registered under `{joint-iso-itut(2) its(28) gdd(5)}` and the way pictograms can 
be generalized according to the required level of detail.

Clause 7.5 Pictogram code and OID contains Table 1, which defines the structure 
and numbering of pictograms for version 1 in the form "service category → 
subcategory → nature → sequence number" (e.g. `trafficSign (1) + regulatory (2) + 
mandatory (7) + xx` ⇒ `{1 2 7 xx}`).
```

### Option 1 Output (Full Formatting)
```markdown
Clause **7.3 Relative object identifier (relative OID)** describes the OID hierarchy 
registered under `{joint-iso-itut(2) its(28) gdd(5)}` and the way pictograms can 
be generalized according to the required level of detail.

Clause **7.5 Pictogram code and OID** contains **Table 1**, which defines the structure 
and numbering of pictograms for version 1 in the form **"service category → 
subcategory → nature → sequence number"** (e.g. `trafficSign (1) + regulatory (2) + 
mandatory (7) + xx` ⇒ `{1 2 7 xx}`).
```

**Visual comparison in rendered HTML:**

| Version                | Readability | Technical Clarity | Noise Level |
|------------------------|-------------|-------------------|-------------|
| Current (no format)    | Fair        | Poor              | Low         |
| Code-only             | Fair        | Good              | Low         |
| Full formatting       | Excellent   | Excellent         | Medium      |

---

## Conclusion

Implementing inline formatting conversion is **feasible and valuable**. The recommended **phased approach** balances risk, effort, and user benefit:

1. **Phase 1 (Code-only)** solves the immediate problem with minimal risk
2. **Phase 2 (Full formatting)** significantly improves readability
3. **Phase 3 (Edge cases)** polishes the implementation for production

The user should decide whether to proceed with all phases or stop after Phase 1.
