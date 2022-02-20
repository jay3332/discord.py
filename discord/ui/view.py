"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from functools import partial
from typing import (
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    TYPE_CHECKING,
    Tuple,
    TypeVar,
)

from .abc import ItemContainer, _component_to_item, _walk_all_components
from .item import Item, ItemCallbackType, ViewItem
from ..components import (
    Component,
    _component_factory,
)

if TYPE_CHECKING:
    from ..interactions import Interaction
    from ..message import Message
    from ..types.components import Component as ComponentPayload
    from ..state import ConnectionState

I = TypeVar("I", bound=Item, covariant=True)

__all__ = (
    'View',
)


class View(ItemContainer[ViewItem], max_width=5, max_children=25):
    """Represents a UI view.

    This object must be inherited to create a UI within Discord.

    .. versionadded:: 2.0

    Parameters
    -----------
    timeout: Optional[:class:`float`]
        Timeout in seconds from last interaction with the UI before no longer accepting input.
        If ``None`` then there is no timeout.

    Attributes
    ------------
    timeout: Optional[:class:`float`]
        Timeout from last interaction with the UI before no longer accepting input.
        If ``None`` then there is no timeout.
    children: List[:class:`Item`]
        The list of children attached to this view.
    """

    __discord_ui_view__: ClassVar[bool] = True
    __view_children_items__: ClassVar[List[ItemCallbackType]] = []

    def __init_subclass__(cls, **kwargs) -> None:
        children: List[ItemCallbackType] = []
        for base in reversed(cls.__mro__):
            children.extend(member for member in base.__dict__.values() if (
                    hasattr(member, '__discord_ui_model_type__')
                    and issubclass(member.__discord_ui_model_type__, ViewItem)
                ))
        if len(children) > 25:
            raise TypeError('View cannot have more than 25 children')

        cls.__view_children_items__ = children

    def __init__(self, *, timeout: Optional[float] = 180.0):
        super().__init__(timeout=timeout)

        for func in self.__view_children_items__:
            item: Item = func.__discord_ui_model_type__(**func.__discord_ui_model_kwargs__)  # type: ignore
            item.callback = partial(func, self, item)
            item._view = self
            setattr(self, func.__name__, item)
            self.add_item(item)

        self.id: str = os.urandom(16).hex()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} timeout={self.timeout} children={len(self.children)}>'

    @classmethod
    def from_message(cls, message: Message, /, *, timeout: Optional[float] = 180.0) -> View:
        """Converts a message's components into a :class:`View`.

        The :attr:`.Message.components` of a message are read-only
        and separate types from those in the ``discord.ui`` namespace.
        In order to modify and edit message components they must be
        converted into a :class:`View` first.

        Parameters
        -----------
        message: :class:`discord.Message`
            The message with components to convert into a view.
        timeout: Optional[:class:`float`]
            The timeout of the converted view.

        Returns
        --------
        :class:`View`
            The converted view. This always returns a :class:`View` and not
            one of its subclasses.
        """
        view = View(timeout=timeout)
        for component in _walk_all_components(message.components):
            view.add_item(_component_to_item(component))  # type: ignore
        return view

    async def on_error(self, error: Exception, item: Item, interaction: Interaction) -> None:
        """|coro|

        A callback that is called when an item's callback or :meth:`interaction_check`
        fails with an error.

        The default implementation prints the traceback to stderr.

        Parameters
        -----------
        error: :class:`Exception`
            The exception that was raised.
        item: :class:`Item`
            The item that failed the dispatch.
        interaction: :class:`~discord.Interaction`
            The interaction that led to the failure.
        """
        print(f'Ignoring exception in view {self} for item {item}:', file=sys.stderr)
        traceback.print_exception(error.__class__, error, error.__traceback__, file=sys.stderr)

    async def _scheduled_task(self, item: ViewItem, interaction: Interaction):
        try:
            if self.timeout:
                self._timeout_expiry = time.monotonic() + self.timeout

            allow = await self.interaction_check(interaction)
            if not allow:
                return

            await item.callback(interaction)
            if not interaction.response._responded:
                await interaction.response.defer()
        except Exception as e:
            return await self.on_error(e, item, interaction)

    def _start_listening_from_store(self, store: ViewStore) -> None:
        self._cancel_callback = partial(store.remove_view)
        if self.timeout:
            loop = asyncio.get_running_loop()
            if self._timeout_task is not None:
                self._timeout_task.cancel()

            self._timeout_expiry = time.monotonic() + self.timeout
            self._timeout_task = loop.create_task(self._timeout_task_impl())

    def _dispatch_timeout(self):
        if self._stopped.done():
            return

        self._stopped.set_result(True)
        asyncio.create_task(self.on_timeout(), name=f'discord-ui-view-timeout-{self.id}')

    def _dispatch_item(self, item: ViewItem, interaction: Interaction):
        if self._stopped.done():
            return

        asyncio.create_task(self._scheduled_task(item, interaction), name=f'discord-ui-view-dispatch-{self.id}')

    def refresh(self, components: Iterable[Component]):
        # This is pretty hacky at the moment
        # fmt: off
        old_state: Dict[Tuple[int, str], Item] = {
            (item.type.value, item.custom_id): item  # type: ignore
            for item in self.children
            if item.is_dispatchable()
        }
        # fmt: on
        children: List[Item] = []
        for component in _walk_all_components(components):
            try:
                older = old_state[(component.type.value, component.custom_id)]  # type: ignore
            except (KeyError, AttributeError):
                children.append(_component_to_item(component))  # type: ignore
            else:
                older.refresh_component(component)
                children.append(older)

        self.children = children

    def is_dispatching(self) -> bool:
        """:class:`bool`: Whether the view has been added for dispatching purposes."""
        return self._cancel_callback is not None

    def is_persistent(self) -> bool:
        """:class:`bool`: Whether the view is set up as persistent.

        A persistent view has all their components with a set ``custom_id`` and
        a :attr:`timeout` set to ``None``.
        """
        return self.timeout is None and all(item.is_persistent() for item in self.children)


class ViewStore:
    def __init__(self, state: ConnectionState):
        # (component_type, message_id, custom_id): (View, Item)
        self._views: Dict[Tuple[int, Optional[int], str], Tuple[View, ViewItem]] = {}
        # message_id: View
        self._synced_message_views: Dict[int, View] = {}
        self._state: ConnectionState = state

    @property
    def persistent_views(self) -> List[View]:
        # fmt: off
        views = {
            view.id: view
            for view, _ in self._views.values()
            if view.is_persistent()
        }
        # fmt: on
        return list(views.values())

    def __verify_integrity(self):
        to_remove: List[Tuple[int, Optional[int], str]] = [
            k for (k, (view, _)) in self._views.items() if view.is_finished()
        ]

        for k in to_remove:
            del self._views[k]

    def add_view(self, view: View, message_id: Optional[int] = None):
        self.__verify_integrity()

        view._start_listening_from_store(self)
        for item in view.children:
            if item.is_dispatchable():
                self._views[item.type.value, message_id, item.custom_id] = view, item  # type: ignore

        if message_id is not None:
            self._synced_message_views[message_id] = view

    def remove_view(self, view: View):
        for item in view.children:
            if item.is_dispatchable():
                self._views.pop((item.type.value, item.custom_id), None)  # type: ignore

        for key, value in self._synced_message_views.items():
            if value.id == view.id:
                del self._synced_message_views[key]
                break

    def dispatch(self, component_type: int, custom_id: str, interaction: Interaction):
        self.__verify_integrity()
        message_id: Optional[int] = interaction.message and interaction.message.id
        key = (component_type, message_id, custom_id)
        # Fallback to None message_id searches in case a persistent view
        # was added without an associated message_id
        value = self._views.get(key) or self._views.get((component_type, None, custom_id))
        if value is None:
            return

        view, item = value
        item.refresh_state(interaction)
        view._dispatch_item(item, interaction)

    def is_message_tracked(self, message_id: int):
        return message_id in self._synced_message_views

    def remove_message_tracking(self, message_id: int) -> Optional[View]:
        return self._synced_message_views.pop(message_id, None)

    def update_from_message(self, message_id: int, components: List[ComponentPayload]):
        # pre-req: is_message_tracked == true
        view = self._synced_message_views[message_id]
        view.refresh(map(_component_factory, components))
