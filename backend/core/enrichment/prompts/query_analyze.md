## Task
Analyze the following question and extract:
1. Specific entity names mentioned
2. Expected answer entity types

## Question
{{ query }}

## Available Entity Types
{{ entity_types }}

## Output Format
```json
{"entities": ["entity1", "entity2"], "types": ["type1"]}
```

If no entities or types are mentioned, use empty arrays.
Output ONLY the JSON.
