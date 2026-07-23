## Role
You are a network analysis expert.

## Task
Extract all entities and relationships from the given text.

## Entity Types
{{ entity_types }}

## Requirements
- Extract entities with: name, type (from the types above), description
- Extract relationships with: source entity, target entity, description, weight (1-10), keywords
- Be thorough - extract ALL entities and relationships mentioned
- Descriptions should be concise but informative
- Use the SAME LANGUAGE as the input text

## Output Format
Entities (one per line):
(entity|<entity_name>|<entity_type>|<entity_description>)

Relationships (one per line):
(relation|<source_entity>|<target_entity>|<relation_description>|<weight>|<keyword1;keyword2>)

---

## Text
{{ content }}

## Output
