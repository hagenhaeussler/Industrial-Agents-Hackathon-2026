"""Provider grammar adaptation; domain validation stays in the tool registry."""

import anthropic


def strict_schema(schema: dict) -> dict:
    """Adapt provider grammar while the registry validates original constraints.

    The SDK moves unsupported numeric/string bounds into descriptions rather
    than sending them as grammar keywords. Optional nulls use omission instead:
    Callers omit unused fields. This avoids consuming a nullable union for every
    optional argument. Required nullable fields remain nullable.
    """
    def optional_fields(value):
        result = dict(value)
        result.pop("default", None)
        # Traverse schemas rather than arbitrary dictionaries: a property named
        # "default" is data, whereas a schema's default keyword is metadata.
        for key in ("properties", "$defs", "definitions"):
            if isinstance(result.get(key), dict):
                result[key] = {name: optional_fields(item) for name, item in result[key].items()}
        for key in ("anyOf", "oneOf", "allOf"):
            if isinstance(result.get(key), list):
                result[key] = [optional_fields(item) for item in result[key]]
        if isinstance(result.get("items"), dict):
            result["items"] = optional_fields(result["items"])
        if result.get("type") == "object":
            required = set(result.get("required", []))
            for name, field_schema in result.get("properties", {}).items():
                variants = field_schema.get("anyOf")
                if name in required or not isinstance(variants, list):
                    continue
                non_null = [variant for variant in variants if variant.get("type") != "null"]
                if not non_null or len(non_null) == len(variants):
                    continue
                metadata = {key: item for key, item in field_schema.items() if key != "anyOf"}
                if len(non_null) == 1:
                    field_schema = {**non_null[0], **metadata}
                else:
                    field_schema = {**metadata, "anyOf": non_null}
                description = field_schema.get("description", "")
                field_schema["description"] = (description + "\n\n" if description else "") + "Optional: omit when unused."
                result["properties"][name] = field_schema
        return result

    return anthropic.transform_schema(optional_fields(schema))
