## Task
Determine if each pair of entity names refers to the SAME real-world entity.

## Requirements
- Consider abbreviations, aliases, different spellings
- For Chinese entities, consider character overlap
- Output ONLY valid JSON

## Pairs
{% for pair in pairs %}
{{ loop.index }}. "{{ pair[0] }}" vs "{{ pair[1] }}"
{% endfor %}

## Output Format
```json
[{"name1": "...", "name2": "...", "same": true}, ...]
```

Output ONLY the JSON array.
