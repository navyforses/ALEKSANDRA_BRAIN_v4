"""
ontology.py — MEM-06 loader.

Reads the project-wide `graph_ontology.yaml`, which is the single source of
truth for which entity types Graphiti is allowed to extract into Neo4j, and
builds the `entity_types` dict that gets passed to `graphiti.add_episode`.

Each type's `description` field from the YAML becomes the class docstring of
a dynamically-generated Pydantic BaseModel. Graphiti's extractor prompt
reads that docstring and uses it as the type definition shown to the LLM,
so changing the YAML changes what the LLM is told without redeploying code.

Combined with `excluded_entity_types=['Entity']` in the add_episode call,
this enforces MEM-06's "ad-hoc node labels are rejected at write time"
contract — anything the LLM can't classify into one of these types gets
dropped instead of polluting the graph as a generic Entity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, create_model

ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "graph_ontology.yaml"


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict[str, Any]:
    """Return the parsed YAML document. Raises FileNotFoundError if missing."""
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or "entity_types" not in doc:
        raise ValueError(
            f"{path}: malformed ontology (missing top-level `entity_types`)"
        )
    return doc


def build_entity_types(
    path: Path = ONTOLOGY_PATH,
) -> tuple[dict[str, type[BaseModel]], str]:
    """
    Return ({type_name: PydanticModel}, version) suitable for passing as
    Graphiti's `entity_types=` kwarg.

    Each generated model is an empty BaseModel — Graphiti reads only the
    class docstring (the YAML `description`) for its extractor prompt and
    does not need custom fields here. Custom field expansion is reserved
    for a future minor bump (would add typed attributes like
    `Drug.mechanism: str` and surface them to the LLM as required fields).
    """
    doc = load_ontology(path)
    version = str(doc.get("version", "0.0"))
    types_doc = doc["entity_types"]
    if not isinstance(types_doc, dict):
        raise ValueError(f"{path}: `entity_types` must be a mapping")

    models: dict[str, type[BaseModel]] = {}
    for type_name, spec in types_doc.items():
        if not isinstance(spec, dict) or "description" not in spec:
            raise ValueError(
                f"{path}: entity_type '{type_name}' is missing `description`"
            )
        desc = str(spec["description"]).strip()
        model = create_model(type_name, __base__=BaseModel)
        model.__doc__ = desc
        models[type_name] = model
    return models, version


__all__ = ["load_ontology", "build_entity_types", "ONTOLOGY_PATH"]
