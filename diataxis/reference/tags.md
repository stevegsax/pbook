+++
title = "Tag System Reference"
weight = 84
description = "Namespaced tags and their role in retrieval"
topic = "tags"
covers = ["All five tag namespaces with valid values", "General vs extracted tier distinction", "Tag validation rules", "Tag inference from file extensions and keywords"]
detail = "Tabular. One table per namespace with valid values and sources."
+++
All tags use `namespace:value` format. Five namespaces are defined across two tiers.

## Namespaces

| Namespace  | Tier      | Purpose          | Example              |
|------------|-----------|------------------|----------------------|
| `lang:`    | General   | Programming language | `lang:python`    |
| `lib:`     | General   | Library/framework | `lib:sqlalchemy`    |
| `domain:`  | General   | Problem domain   | `domain:testing`     |
| `project:` | Extracted | Source project   | `project:forge`      |
| `pattern:` | Extracted | Lesson type      | `pattern:failure-pattern` |

General tags represent cross-project, human-curated knowledge. Extracted tags are LLM-produced and project-specific.

## Language inference

File extensions map to `lang:` tags automatically.

| Extension | Tag                |
|-----------|--------------------|
| `.py`     | `lang:python`      |
| `.ts`     | `lang:typescript`  |
| `.tsx`    | `lang:typescript`  |
| `.js`     | `lang:javascript`  |
| `.jsx`    | `lang:javascript`  |
| `.go`     | `lang:go`          |
| `.rs`     | `lang:rust`        |
| `.java`   | `lang:java`        |
| `.rb`     | `lang:ruby`        |

## Domain inference

Keywords in description text map to `domain:` tags.

| Keyword    | Tag                   |
|------------|-----------------------|
| `test`     | `domain:testing`      |
| `refactor` | `domain:refactoring`  |
| `api`      | `domain:api`          |
| `database` | `domain:database`     |
| `migration`| `domain:migration`    |
| `cli`      | `domain:cli`          |
| `validate` | `domain:validation`   |
| `bug`      | `domain:bug-fix`      |
| `fix`      | `domain:bug-fix`      |

Keywords are matched case-insensitively against the description string. Multiple keywords can match, producing multiple tags.

## Validation rules

Tags must conform to `namespace:value` format. The following constraints apply:

- The namespace must be one of the five defined namespaces.
- The value must be non-empty.
- Unknown namespaces are rejected.

### Functions

| Function                    | Signature                                                        | Returns            |
|-----------------------------|------------------------------------------------------------------|--------------------|
| `parse_tag()`               | `parse_tag(tag: str) -> tuple[str, str]`                         | `(namespace, value)` — raises `ValueError` on invalid input |
| `validate_tag()`            | `validate_tag(tag: str) -> bool`                                 | `True` if the tag is well-formed |
| `validate_tags()`           | `validate_tags(tags: list[str]) -> list[str]`                    | List of error messages; empty list means all valid |
| `is_general_tag()`          | `is_general_tag(tag: str) -> bool`                               | `True` if the tag belongs to `lang:`, `lib:`, or `domain:` |
| `is_extracted_tag()`        | `is_extracted_tag(tag: str) -> bool`                             | `True` if the tag belongs to `project:` or `pattern:` |
| `infer_tags_from_context()` | `infer_tags_from_context(file_extensions, description) -> list[str]` | Sorted, deduplicated list of inferred tags |

All functions are defined in `pbook.tags`.

For how tags affect retrieval scoring, see [Retrieval Ranking](/explanation/retrieval-ranking/). For practical tag usage in queries, see [How to Retrieve Entries](/howto/retrieve-entries/).