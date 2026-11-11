# Skeleton change
- CHANGE `esper/__init__.py::World.create_entity(self, *components: _C) -> int` — always registers the new entity in `_entities` (as empty if no components are given), then attaches any components
- CHANGE `esper/__init__.py::World.add_component(self, entity: int, component_instance: _C, type_alias: _Optional[_Type[_C]] = None) -> None` — adds a component to an existing entity only; raises KeyError if the entity was never created, and no longer creates entities
- CHANGE `esper/__init__.py::World.remove_component(self, entity: int, component_type: _Type[_C]) -> int` — removes the component but keeps the entity registered even when it has no components left
- CHANGE `esper/__init__.py::World.entity_exists(self, entity: int) -> bool` — True for any created, not-deleted entity, including empty ones
- RULE `esper/__init__.py::World.add_component` may not create entries in `World._entities` — only `World.create_entity` registers entities (single responsibility)
