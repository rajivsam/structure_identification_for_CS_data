# Documentation Index — structure_id v2.0

**Date:** 2026-11-15  
**Version:** 2.0 (Refactored for Stateless Execution & Gram-Schmidt Orthogonalization)  
**Status:** ✅ Ready for Implementation

---

## Navigation Guide

This index helps you find the right document for your role and task.

### 🎯 **Quick Start (5 minutes)**

**Start here if you're:** New to the project, need a 30,000-foot overview

→ Read: [**QUICK_REFERENCE.md**](./QUICK_REFERENCE.md)
- Public API signature
- 4-stage pipeline overview
- Configuration defaults
- Example workflow
- Common mistakes to avoid

---

### 📊 **For Project Stakeholders & Architects**

**If you want to:** Understand what changed from v1.0 to v2.0

→ Read: [**REFACTORING_SUMMARY.md**](./REFACTORING_SUMMARY.md)
- Before/after comparison table
- Section mapping
- New acceptance criteria
- Design decisions preserved
- Files modified

**Time:** 15 minutes

---

### 👨‍💻 **For Implementation Team**

**If you're:** Writing the code to implement structure_id

→ Read in order:
1. [**structure_identification_requirements.md**](./structure_identification_requirements.md) — Sections 1–9
   - Official specification
   - 4-stage pipeline with algorithms
   - Result object definitions
   - Acceptance criteria
   
   **Time:** 30 minutes

2. [**TABULAR_REPORTING_SPECIFICATION.md**](./TABULAR_REPORTING_SPECIFICATION.md) — For Stage 2 reporting
   - Method signature: `get_orthogonal_feature_interpretation_report()`
   - Four output formats (table, structured, summary, metadata)
   - Schema and formatting rules
   - Implementation checklist
   - Unit test examples
   
   **Time:** 30 minutes

3. [**QUICK_REFERENCE.md**](./QUICK_REFERENCE.md) — For quick lookup during coding
   - API signatures
   - Algorithm pseudocode
   - Common data structures
   
   **Time:** 5 minutes (reference)

---

### 📈 **For Data Scientists & Analysts**

**If you want to:** Use structure_id output to understand your data

→ Read: [**GRAM_SCHMIDT_INTERPRETATION_GUIDE.md**](./GRAM_SCHMIDT_INTERPRETATION_GUIDE.md)
- How orthogonalized features are constructed
- Understanding the tabular interpretation format
- Worked example (SBA loan data)
- Interpretation of weights and signs
- Three output formats with examples
- Troubleshooting guide
- Practical analysis workflow

**Time:** 20 minutes

---

### 🔬 **For QA & Testing Teams**

**If you're:** Writing tests to verify the implementation

→ Sources:
1. [**structure_identification_requirements.md**](./structure_identification_requirements.md) — Section 9 (Acceptance Criteria)
   - 9 testable criteria
   - Edge case handling
   
2. [**TABULAR_REPORTING_SPECIFICATION.md**](./TABULAR_REPORTING_SPECIFICATION.md) — Section "Testing Guidance"
   - Unit test examples
   - Integration test guidance
   - Performance expectations

3. [**QUICK_REFERENCE.md**](./QUICK_REFERENCE.md) — Section "Testing Checklist"
   - Quick verification list

**Time:** 20 minutes + implementation time

---

## Document Descriptions

### 1. **structure_identification_requirements.md** ⭐ PRIMARY
**Size:** 20 KB | **Sections:** 13 | **Audience:** Everyone (especially developers)

The authoritative specification for structure_id v2.0. Defines the 4-stage pipeline, input/output contracts, edge cases, and acceptance criteria.

**Key Sections:**
- Section 3: Public API
- Section 6: Pipeline Specification (Stage 0–4)
- Section 9: Acceptance Criteria

**When to read:** Before implementing any stage; for validation questions

---

### 2. **QUICK_REFERENCE.md** 🚀 FASTEST OVERVIEW
**Size:** 10.8 KB | **Audience:** Everyone

One-page visual reference card with all essential information in tabular form. Best for quick lookup during development.

**Includes:**
- API signatures
- Configuration defaults
- Stage overview table
- Example code workflow
- Testing checklist
- Common mistakes

**When to read:** Daily during development; for reference lookups

---

### 3. **REFACTORING_SUMMARY.md** 📝 CHANGE LOG
**Size:** 9.6 KB | **Audience:** Stakeholders, architects, project leads

Detailed before/after comparison showing exactly what changed from v1.0 to v2.0. Useful for understanding rationale and impact.

**Includes:**
- Architecture changes (stateless)
- Gram-Schmidt specification details
- New interpretation reporting
- Instance labeling clarification
- Removed content
- Design decisions formalized

**When to read:** To understand scope of refactoring; for project planning

---

### 4. **GRAM_SCHMIDT_INTERPRETATION_GUIDE.md** 📚 ANALYST GUIDE
**Size:** 12 KB | **Audience:** Data scientists, analysts, stakeholders

Practical guide explaining how to interpret orthogonalized features and use the reporting output. Includes worked examples and troubleshooting.

**Includes:**
- Tabular format walkthrough
- Weight matrix explanation
- Sign convention (+ / -)
- Percentage contribution derivation
- Three output formats with examples
- SBA loan data worked example
- Troubleshooting common issues
- Practical analysis workflow

**When to read:** To understand structure_id output; before analyzing results

---

### 5. **TABULAR_REPORTING_SPECIFICATION.md** 🔧 API SPEC
**Size:** 16 KB | **Audience:** Implementation team, code reviewers

Complete specification of the tabular reporting method and supporting data structures. Defines exact format, schema, and integration points.

**Includes:**
- Method signature
- Four output formats (table, structured dict, summary, metadata)
- Schema definitions
- Formatting rules
- JSON serialization
- Implementation checklist
- Unit test examples
- Performance notes

**When to read:** When implementing `get_orthogonal_feature_interpretation_report()`; for code review

---

### 6. **DOCUMENTATION_INDEX.md** 📋 THIS FILE
**Size:** 4 KB | **Audience:** Everyone

Navigation guide to all documentation. Helps you find the right document for your role and task.

**When to read:** First time; whenever you're lost in the docs

---

## Document Relationships

```
┌─────────────────────────────────────────────────┐
│  DOCUMENTATION_INDEX.md (You are here)          │
└────────────────┬────────────────────────────────┘
                 │
      ┌──────────┴──────────┬────────────────┬─────────────┐
      │                     │                │             │
      ▼                     ▼                ▼             ▼
  QUICK_REFERENCE    structure_id_      REFACTORING_   GRAM_SCHMIDT_
  .md (overview)     requirements.md    SUMMARY.md      INTERPRETATION
                     (specification)    (changes)       _GUIDE.md
                     │                                  (guide)
                     │
                     ├─→ TABULAR_REPORTING_
                     │   SPECIFICATION.md
                     │   (API details)
                     │
                     └─→ copilot_init.md
                         (project context)
```

**Reading Paths:**

**Path A: I'm new to the project**
1. QUICK_REFERENCE.md (5 min)
2. copilot_init.md (5 min)
3. (Optional) REFACTORING_SUMMARY.md (10 min)

**Path B: I'm implementing structure_id**
1. structure_identification_requirements.md (30 min)
2. TABULAR_REPORTING_SPECIFICATION.md (30 min)
3. QUICK_REFERENCE.md (reference, 5 min)

**Path C: I'm analyzing structure_id output**
1. QUICK_REFERENCE.md (5 min)
2. GRAM_SCHMIDT_INTERPRETATION_GUIDE.md (20 min)
3. TABULAR_REPORTING_SPECIFICATION.md (10 min, optional)

**Path D: I'm reviewing changes**
1. REFACTORING_SUMMARY.md (15 min)
2. structure_identification_requirements.md (for details, 30 min)

---

## Key Concepts Quick Lookup

| Concept | Document | Section |
|---------|----------|---------|
| 4-stage pipeline overview | QUICK_REFERENCE.md | "Pipeline: 4 Stages" |
| Modified Gram-Schmidt algorithm | QUICK_REFERENCE.md | "Stage 2: Gram-Schmidt" |
| Tabular interpretation format | QUICK_REFERENCE.md | "Stage 2: Gram-Schmidt" |
| Full Gram-Schmidt spec | structure_identification_requirements.md | Section 6, Stage 2 |
| Interpretation reporting API | TABULAR_REPORTING_SPECIFICATION.md | Section "Method Signature" |
| How to interpret weights | GRAM_SCHMIDT_INTERPRETATION_GUIDE.md | Section "The Weight Matrix W" |
| Example interpretation | GRAM_SCHMIDT_INTERPRETATION_GUIDE.md | Section "Worked Example: SBA Loan Data" |
| Instance labeling ("independent") | QUICK_REFERENCE.md | "Stage 3: Row Clustering" |
| Configuration parameters | QUICK_REFERENCE.md | "Configuration Defaults" |
| Unit test examples | TABULAR_REPORTING_SPECIFICATION.md | Section "Testing Guidance" |
| Common mistakes | QUICK_REFERENCE.md | "Common Mistakes to Avoid" |
| Design decisions | structure_identification_requirements.md | Section 12 |
| Edge case handling | structure_identification_requirements.md | Section 10 |

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| v2.0 | 2026-11-15 | Stateless execution; Gram-Schmidt orthogonalization; interpretable reporting | ✅ Current |
| v1.0 | (prior) | Original specification with partition-centric design | 🔄 Superseded |

---

## Next Steps

1. **Everyone:** Read [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (5 min)
2. **Implementers:** Read [structure_identification_requirements.md](./structure_identification_requirements.md) (30 min)
3. **Implementers:** Read [TABULAR_REPORTING_SPECIFICATION.md](./TABULAR_REPORTING_SPECIFICATION.md) (30 min)
4. **Analysts:** Read [GRAM_SCHMIDT_INTERPRETATION_GUIDE.md](./GRAM_SCHMIDT_INTERPRETATION_GUIDE.md) (20 min)
5. **Stakeholders:** Read [REFACTORING_SUMMARY.md](./REFACTORING_SUMMARY.md) (15 min)

---

## Questions & Support

| Question | Check Document | Section |
|----------|---|---|
| "What is the overall structure?" | QUICK_REFERENCE.md | Top half |
| "How do I implement Stage 2?" | structure_identification_requirements.md + TABULAR_REPORTING_SPECIFICATION.md | Stage 2 |
| "What does this orthogonal component mean?" | GRAM_SCHMIDT_INTERPRETATION_GUIDE.md | Multiple |
| "What are the acceptance criteria?" | structure_identification_requirements.md | Section 9 |
| "What changed from v1.0?" | REFACTORING_SUMMARY.md | All sections |
| "How do I format the tabular output?" | TABULAR_REPORTING_SPECIFICATION.md | "Output Format 1: Tabular" |

---

**Last Updated:** 2026-11-15  
**Maintainer:** Refactoring Team  
**Status:** ✅ Complete and ready for implementation
