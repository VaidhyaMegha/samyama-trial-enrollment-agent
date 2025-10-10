# Complex Criteria Design Document

**Feature:** Complex Logical Criteria Support (AND/OR/NOT)
**Status:** In Development
**Priority:** HIGH
**Complexity:** HIGH

---

## Overview

This document describes the design and implementation of complex logical criteria support for the AWS Trial Enrollment Agent. This feature enables evaluation of nested logical combinations (AND, OR, NOT) of clinical trial eligibility criteria.

## Problem Statement

Current implementation only supports simple, independent criteria. Real-world trials often have complex logical requirements:
- "(Diabetes OR Pre-diabetes) AND No insulin use"
- "ECOG 0-1 AND (No prior chemotherapy OR Completed >6 months ago)"
- "NOT (Pregnant OR Breastfeeding)"

## Solution Design

### JSON Structure

#### Simple Criterion (Current - Backward Compatible)
```json
{
  "type": "inclusion",
  "category": "demographics",
  "description": "Age ≥ 18",
  "attribute": "age",
  "operator": "greater_than",
  "value": 18,
  "fhir_resource": "Patient"
}
```

#### Complex Criterion (New)
```json
{
  "type": "inclusion",
  "logic_operator": "AND",
  "description": "(Diabetes OR Pre-diabetes) AND No insulin use",
  "criteria": [
    {
      "logic_operator": "OR",
      "description": "Diabetes or Pre-diabetes",
      "criteria": [
        {
          "category": "condition",
          "description": "Type 2 Diabetes",
          "attribute": "diagnosis",
          "operator": "contains",
          "value": "Type 2 Diabetes",
          "fhir_resource": "Condition"
        },
        {
          "category": "condition",
          "description": "Pre-diabetes",
          "attribute": "diagnosis",
          "operator": "contains",
          "value": "Pre-diabetes",
          "fhir_resource": "Condition"
        }
      ]
    },
    {
      "category": "medication",
      "description": "No insulin use",
      "attribute": "insulin",
      "operator": "not_contains",
      "value": "insulin",
      "fhir_resource": "MedicationStatement"
    }
  ]
}
```

### Key Design Principles

1. **Backward Compatibility**: Simple criteria without `logic_operator` work unchanged
2. **Recursive Structure**: Criteria can contain nested `criteria` arrays
3. **Tree Evaluation**: Evaluation follows tree structure (post-order traversal)
4. **Fail-Fast**: Stop evaluation early when outcome is determined

### Logic Operators

| Operator | Description | Evaluation Rule |
|----------|-------------|-----------------|
| `AND` | All must be true | `all(sub_criteria_results)` |
| `OR` | At least one true | `any(sub_criteria_results)` |
| `NOT` | Negate result | `not sub_criteria_result` |

## Implementation Details

### Recursive Evaluation Algorithm

```python
def evaluate_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively evaluate a criterion (simple or complex).

    Args:
        patient_id: Patient identifier
        criterion: Criterion to evaluate (simple or complex)

    Returns:
        Result dict with met status, reason, and evidence
    """
    # Base case: Simple criterion (leaf node)
    if 'criteria' not in criterion or criterion.get('criteria') is None:
        return check_simple_criterion(patient_id, criterion)

    # Recursive case: Complex criterion (branch node)
    logic_op = criterion.get('logic_operator', 'AND')
    sub_criteria = criterion['criteria']

    # Evaluate all sub-criteria recursively
    sub_results = []
    for sub_criterion in sub_criteria:
        result = evaluate_criterion(patient_id, sub_criterion)
        sub_results.append(result)

    # Apply logical operator
    if logic_op == 'AND':
        met = all(r['met'] for r in sub_results)
        reason = f"All {len(sub_results)} sub-criteria must be met" if met else "Not all sub-criteria met"

    elif logic_op == 'OR':
        met = any(r['met'] for r in sub_results)
        met_count = sum(1 for r in sub_results if r['met'])
        reason = f"At least 1 of {len(sub_results)} sub-criteria met ({met_count} met)" if met else "No sub-criteria met"

    elif logic_op == 'NOT':
        if len(sub_results) != 1:
            raise ValueError("NOT operator requires exactly one sub-criterion")
        met = not sub_results[0]['met']
        reason = f"Negation of: {sub_results[0]['reason']}"

    else:
        raise ValueError(f"Unknown logic operator: {logic_op}")

    return {
        'met': met,
        'reason': reason,
        'evidence': {
            'logic_operator': logic_op,
            'sub_results': sub_results
        },
        'criterion': {
            'type': criterion.get('type'),
            'description': criterion.get('description'),
            'logic_operator': logic_op
        }
    }
```

### Parser Prompt Enhancement

Add to criteria parser prompt:

```
**Complex Criteria with Logical Operators:**

When criteria involve logical combinations (AND, OR, NOT), create nested structures:

- Use "logic_operator": "AND" for all conditions that must be true
- Use "logic_operator": "OR" for any condition that can be true
- Use "logic_operator": "NOT" to negate a condition
- Place sub-criteria in "criteria" array
- Each sub-criterion follows the same format

Examples:

Input: "Patient has Diabetes OR Pre-diabetes"
Output:
{
  "type": "inclusion",
  "logic_operator": "OR",
  "description": "Diabetes or Pre-diabetes",
  "criteria": [
    {
      "category": "condition",
      "description": "Type 2 Diabetes",
      "operator": "contains",
      "value": "Type 2 Diabetes",
      "fhir_resource": "Condition"
    },
    {
      "category": "condition",
      "description": "Pre-diabetes",
      "operator": "contains",
      "value": "Pre-diabetes",
      "fhir_resource": "Condition"
    }
  ]
}

Input: "(Diabetes OR Pre-diabetes) AND No insulin use"
Output:
{
  "type": "inclusion",
  "logic_operator": "AND",
  "description": "(Diabetes OR Pre-diabetes) AND No insulin",
  "criteria": [
    {
      "logic_operator": "OR",
      "description": "Diabetes or Pre-diabetes",
      "criteria": [
        {<Type 2 Diabetes criterion>},
        {<Pre-diabetes criterion>}
      ]
    },
    {
      "category": "medication",
      "description": "No insulin use",
      "operator": "not_contains",
      "value": "insulin",
      "fhir_resource": "MedicationStatement"
    }
  ]
}

Input: "NOT (Pregnant OR Breastfeeding)"
Output:
{
  "type": "exclusion",
  "logic_operator": "NOT",
  "description": "NOT (Pregnant OR Breastfeeding)",
  "criteria": [
    {
      "logic_operator": "OR",
      "criteria": [
        {<Pregnant criterion>},
        {<Breastfeeding criterion>}
      ]
    }
  ]
}
```

## Test Cases

### Test 1: Simple AND
**Input**: "Age ≥40 AND ECOG 0-1"
**Expected**: Both criteria must pass

### Test 2: Simple OR
**Input**: "Diabetes OR Pre-diabetes"
**Expected**: Either criterion can pass

### Test 3: NOT Logic
**Input**: "NOT Pregnant"
**Expected**: Criterion must fail for patient to pass

### Test 4: Nested AND/OR
**Input**: "(Diabetes OR Pre-diabetes) AND (ECOG 0-1)"
**Expected**: At least one from first group AND the ECOG criterion

### Test 5: Complex Nested
**Input**: "((A OR B) AND C) OR D"
**Expected**: Either ((A or B) and C) or D

### Test 6: Multiple Levels
**Input**: "(A AND B) OR (C AND D) OR (E AND F)"
**Expected**: Any of the three AND pairs can be true

## Edge Cases

1. **Empty criteria array**: Treat as always false
2. **Single criterion in complex**: Evaluate normally
3. **Invalid logic operator**: Raise validation error
4. **NOT with multiple criteria**: Raise validation error (NOT requires single criterion)
5. **Mixed simple and complex**: Support both in same criteria list

## Performance Considerations

- **Fail-Fast for AND**: Stop evaluating once any sub-criterion fails
- **Fail-Fast for OR**: Stop evaluating once any sub-criterion passes
- **Caching**: Cache sub-criterion results to avoid re-evaluation
- **Depth Limit**: Enforce max nesting depth (default: 10 levels)

## Backward Compatibility

- Simple criteria without `logic_operator` field work unchanged
- Existing parser outputs remain valid
- Existing FHIR search evaluations remain valid
- New logic is opt-in (requires `logic_operator` field)

## Validation Rules

1. **logic_operator presence**: If present, `criteria` array must exist
2. **criteria array**: Must contain at least 1 element
3. **NOT operator**: Must have exactly 1 sub-criterion
4. **Nesting depth**: Maximum 10 levels (configurable)
5. **Type consistency**: All criteria must have valid `type` field

## Implementation Checklist

### Phase 1: Core Logic (Complete)
- [x] Design JSON structure
- [x] Document evaluation algorithm
- [x] Define test cases

### Phase 2: Parser Updates (In Progress)
- [ ] Update PARSING_PROMPT with complex criteria examples
- [ ] Test parser with complex criteria inputs
- [ ] Validate nested structure output

### Phase 3: Evaluator Implementation (Pending)
- [ ] Implement recursive `evaluate_criterion` function
- [ ] Add AND logic evaluation
- [ ] Add OR logic evaluation
- [ ] Add NOT logic evaluation
- [ ] Add depth limit check
- [ ] Add validation for structure

### Phase 4: Testing (Pending)
- [ ] Test AND: (A AND B)
- [ ] Test OR: (A OR B)
- [ ] Test NOT: NOT(A)
- [ ] Test nested: (A AND B) OR C
- [ ] Test complex: (A OR B) AND (C OR D) AND NOT(E)
- [ ] Test edge cases
- [ ] Load test with deep nesting

### Phase 5: Integration (Pending)
- [ ] Deploy updated parser Lambda
- [ ] Deploy updated FHIR search Lambda
- [ ] End-to-end testing with real trials
- [ ] Performance testing
- [ ] Documentation updates

## Example Real-World Scenarios

### Scenario 1: Diabetes Trial
**Criteria**: "(Type 2 Diabetes OR Pre-diabetes with HbA1c >6.5%) AND (ECOG 0-1) AND NOT (Currently on insulin)"

**JSON**:
```json
{
  "type": "inclusion",
  "logic_operator": "AND",
  "criteria": [
    {
      "logic_operator": "OR",
      "criteria": [
        {<Type 2 Diabetes criterion>},
        {
          "logic_operator": "AND",
          "criteria": [
            {<Pre-diabetes criterion>},
            {<HbA1c >6.5% criterion>}
          ]
        }
      ]
    },
    {<ECOG 0-1 criterion>},
    {
      "logic_operator": "NOT",
      "criteria": [{<Insulin medication criterion>}]
    }
  ]
}
```

### Scenario 2: Oncology Trial
**Criteria**: "(Breast Cancer OR Ovarian Cancer) AND (Stage II OR Stage III) AND (No prior chemotherapy OR Completed >12 months ago)"

### Scenario 3: Cardiovascular Trial
**Criteria**: "((Hypertension AND Diabetes) OR (Prior MI)) AND (eGFR >30) AND NOT (NYHA Class IV)"

## Limitations

1. **Maximum Nesting**: 10 levels deep (configurable)
2. **Evaluation Time**: Complex criteria may take longer (optimize with fail-fast)
3. **Parser Accuracy**: LLM may struggle with very complex logic (validate output)
4. **Cache Invalidation**: Complex criteria harder to cache effectively

## Future Enhancements

1. **Visual Editor**: UI for building complex criteria
2. **Query Optimization**: Reorder sub-criteria for optimal evaluation
3. **Probabilistic Logic**: Support for "at least N of M" criteria
4. **Temporal Logic**: "A within 6 months of B"
5. **Quantifiers**: "At least 2 of the following"

---

**Version**: 1.0
**Last Updated**: October 7, 2025
**Author**: Development Team
