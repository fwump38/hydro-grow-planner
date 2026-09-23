"""Grow task list for Hydro Grow Planner.

Holds the current stage's plan tasks (with due dates from the stage start) plus
any items added by hand. Plan tasks can be checked off or removed for this stage
run; to change them permanently, edit the plan.
"""

from __future__ import annotations

from datetime import date, datetime
import uuid

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager

TASK_PREFIX = "task_"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the task list."""
    async_add_entities([GrowTodoList(entry.runtime_data)])


class GrowTodoList(GrowEntity, TodoListEntity):
    """The grow's task list."""

    _attr_translation_key = "tasks"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, manager: GrowManager) -> None:
        """Initialize."""
        super().__init__(manager, "tasks")

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return plan tasks followed by hand-added items."""
        items = [
            TodoItem(
                uid=t.uid,
                summary=t.task.title,
                description=t.task.description or None,
                due=t.due,
                status=TodoItemStatus.COMPLETED if t.completed else TodoItemStatus.NEEDS_ACTION,
            )
            for t in self.manager.task_items
        ]
        items.extend(
            TodoItem(
                uid=i["uid"],
                summary=i["summary"],
                description=i.get("description"),
                due=date.fromisoformat(i["due"]) if i.get("due") else None,
                status=TodoItemStatus(i["status"]),
            )
            for i in self.manager.custom_items
        )
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add a hand-made item."""
        await self.manager.async_upsert_custom_item(
            _serialize(item, f"custom_{uuid.uuid4().hex[:12]}")
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item; plan tasks only accept status changes."""
        assert item.uid is not None
        if item.uid.startswith(TASK_PREFIX):
            current = next((t for t in self.manager.task_items if t.uid == item.uid), None)
            if current is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="unknown_task"
                )
            if item.summary != current.task.title or item.due != current.due:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="plan_task_readonly"
                )
            await self.manager.async_set_task_completed(
                item.uid, item.status == TodoItemStatus.COMPLETED
            )
            return
        await self.manager.async_upsert_custom_item(_serialize(item, item.uid))

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items; plan tasks are hidden for the rest of this stage run."""
        for uid in uids:
            if uid.startswith(TASK_PREFIX):
                await self.manager.async_dismiss_task(uid)
        await self.manager.async_delete_custom_items(
            {uid for uid in uids if not uid.startswith(TASK_PREFIX)}
        )


def _serialize(item: TodoItem, uid: str) -> dict[str, str | None]:
    due = item.due
    if isinstance(due, datetime):
        # Items are all-day; keep the date part of a datetime.
        due = dt_util.as_local(due).date()
    return {
        "uid": uid,
        "summary": item.summary or "",
        "description": item.description,
        "due": due.isoformat() if due else None,
        "status": (item.status or TodoItemStatus.NEEDS_ACTION).value,
    }
