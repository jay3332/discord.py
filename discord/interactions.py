# -*- coding: utf-8 -*-

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
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Type, TYPE_CHECKING, Tuple, TypeVar, Union

from . import utils
from .mixins import Hashable
from .enums import try_enum, InteractionType, InteractionResponseType, ApplicationCommandType, ApplicationCommandOptionType
from .errors import InteractionResponded, HTTPException, ClientException
from .channel import PartialMessageable, ChannelType

from .user import User
from .file import File
from .member import Member
from .message import Message, Attachment
from .object import Object
from .permissions import Permissions
from .webhook.async_ import async_context, Webhook, handle_message_parameters

__all__ = (
    'Interaction',
    'InteractionMessage',
    'InteractionResponse',
    'ApplicationCommand',
    'ApplicationCommandOption',
    'ApplicationCommandOptionChoice',
    'PartialApplicationCommand',
)

if TYPE_CHECKING:
    from datetime import datetime
    from aiohttp import ClientSession

    from .types.interactions import (
        Interaction as InteractionPayload,
        InteractionData,
        ApplicationCommand as ApplicationCommandPayload,
        ApplicationCommandOption as ApplicationCommandOptionPayload,
    )

    from .application_commands import (
        ApplicationCommandOption as NativeCommandOption,
        ApplicationCommandOptionChoice as NativeCommandChoice,
        ApplicationCommandMeta as NativeApplicationCommand,
    )
    from .client import Client
    from .enums import (
        ApplicationCommandType,
        ApplicationCommandOptionType,
        try_enum
    )
    from .guild import Guild
    from .state import ConnectionState
    from .mentions import AllowedMentions
    from .embeds import Embed
    from .ui.modal import Modal
    from .ui.view import View
    from .channel import VoiceChannel, StageChannel, TextChannel, CategoryChannel, StoreChannel, PartialMessageable
    from .threads import Thread

    InteractionChannel = Union[
        VoiceChannel, StageChannel, TextChannel, CategoryChannel, StoreChannel, Thread, PartialMessageable
    ]

    AutocompleteChoicesT = Union[Iterable[NativeCommandChoice], Iterable[str], Dict[str, str]]
    OptionT = TypeVar('OptionT', bound='ApplicationCommandOption')

MISSING: Any = utils.MISSING


class ApplicationCommandOptionChoice(NamedTuple):
    """Represents a choice of an :class:`.ApplicationCommandOption`.
    This is not to be confused with :class:`.application_commands.ApplicationCommandOptionChoice`.

    .. versionadded:: 2.0

    .. note::
        The type annotation and purpose of the ``name_localizations`` attribute is inferred and is
        only present in order to patch a bug - the actual feature is currently undocumented.
        It is recommended to not utilize this attribute as it may change in the future.

    Attributes
    ----------
    name: str
        The name of this option choice.
    name_localizations: Optional[Dict[str, str]]
        A mapping of localization language codes to their localized names.
    value: Union[str, int, float]
        The value that will be returned when this choice is chosen.
    """
    name: str
    value: Union[str, float]
    name_localizations: Optional[Dict[str, str]] = None


class ApplicationCommandOption(NamedTuple):
    """Represents an option of an :class:`.ApplicationCommand`.

    This is not to be confused with :class:`.application_commands.ApplicationCommandOption`.

    .. versionadded:: 2.0

    Attributes
    ----------
    type: :class:`.ApplicationCommandOptionType`
        The type of this option.
    name: str
        The name of this option.
    description: str
        The description of this option.
    required: bool
        Whether or not this option is required.
    choices: Optional[List[:class:`.ApplicationCommandOptionChoice`]]
        A list of choices this option takes.
    options: Optional[List[:class:`.ApplicationCommandOption`]]
        The parameters/subcommands this option takes.
        ``None`` unless this has a ``type`` of ``subcommand`` or ``subcommand_group``.
    channel_types: Optional[List[:class:`.ChannelType`]]
        The channel types this option will only take.
        ``None`` if it can take all channels, or if this option is not a ``CHANNEL`` option.
    autocomplete: bool
        Whether or not this option is an autocomplete option, where choices are dynamically populated.
    """
    type: ApplicationCommandOptionType
    name: str
    description: str
    required: bool = False
    choices: Optional[List[ApplicationCommandOptionChoice]] = None
    options: Optional[List[ApplicationCommandOption]] = None
    channel_types: Optional[List[ChannelType]] = None
    autocomplete: bool = False

    @classmethod
    def from_dict(cls: Type[OptionT], data: ApplicationCommandOptionPayload) -> OptionT:
        kwargs = {
            'type': ApplicationCommandOptionType(data['type']),
            'name': data['name'],
            'description': data['description'],
            'required': data.get('required', False),
            'choices': None,
            'options': None,
            'channel_types': None,
            'autocomplete': data.get('autocomplete', False),
        }

        if 'choices' in data:
            kwargs['choices'] = [ApplicationCommandOptionChoice(**choice) for choice in data['choices']]

        if 'options' in data:
            kwargs['options'] = [ApplicationCommandOption.from_dict(option) for option in data['options']]

        if 'channel_types' in data:
            kwargs['channel_types'] = [try_enum(ChannelType, t) for t in data['channel_types']]

        return cls(**kwargs)

    def _match_key(self) -> Tuple[Any, ...]:
        return (
            self.type,
            self.name,
            self.description,
            bool(self.required),
            frozenset(option._match_key() for option in self.options) if self.options else None,
            frozenset((choice.name, choice.value) for choice in self.choices) if self.choices else None,
            frozenset(self.channel_types) if self.channel_types else None,
            bool(self.autocomplete),
        )


class PartialApplicationCommand:
    """Represents an application command with minimal data.
    This is typically retrieved through :attr:`Interaction.command`.

    .. versionadded:: 2.0

    Attributes
    ----------
    type: :class:`ApplicationCommandType`
        The type of this command.
    name: str
        The name of this command.
    id: int
        The ID of this command.
    application_id: int
        The ID of the application that this command belongs to.
    """

    __slots__ = (
        '_state',
        'type',
        'name',
        'id',
        'application_id',
    )

    def __init__(
        self,
        *,
        state: ConnectionState,
        type: ApplicationCommandType,
        name: str,
        id: int,
        application_id: int,
    ) -> None:
        self._state: ConnectionState = state
        self.type: ApplicationCommandType = type
        self.name: str = name
        self.id: int = id
        self.application_id: int = application_id

    def __repr__(self) -> str:
        return f'<PartialApplicationCommand type={self.type.name!r} name={self.name!r} id={self.id}>'

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, (PartialApplicationCommand, ApplicationCommand)) and self.id == other.id

    def __hash__(self) -> int:
        return self.id >> 22

    @property
    def resolved(self) -> Optional[ApplicationCommand]:
        """Optional[:class:`ApplicationCommand`]: The resolved application command.

        This gets the command from the internal cache - if it is not stored there, this will be ``None``.
        """
        return self._state.cached_application_commands.get(self.id)


class ApplicationCommand(Hashable):
    """Represents an application command.

    This is not to be confused with :class:`.application_commands.ApplicationCommand`.
    See that if you want to construct your own application commands.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: x == y

            Checks if two commands are equal.

        .. describe:: x != y

            Checks if two commands are not equal.

        .. describe:: hash(x)

            Returns the command's hash.

    Attributes
    ----------
    type: :class:`.ApplicationCommandType`
        The type of this command.
    name: str
        The name of this command.
    description: str
        The description of this command.
        This is always an empty string if the ``type`` of this command is not ``chat_input``.
    id: int
        The snowflake ID of this command.
    guild_id: Optional[int]
        The ID of the guild this belongs to.
        If this is a global command, this will be ``None``.
    application_id: int
        The ID of the application that this command belongs to.
    options: Optional[List[:class:`.ApplicationCommandOption`]
        A list of parameters that this command takes.
    default_permission: bool
        Whether or not this command is enabled by default when it is added to a guild.
    version: int
        Auto-incrementing version identifier updated during substantial record changes.
    """

    if TYPE_CHECKING:
        _state: ConnectionState
        type: ApplicationCommandType
        name: str
        description: str
        id: int
        guild_id: Optional[int]
        application_id: int
        options: Optional[List[ApplicationCommandOption]]
        default_permission: bool
        version: int

    __slots__: Tuple[str, ...] = (
        '_state',
        'type',
        'name',
        'description',
        'id',
        'guild_id',
        'application_id',
        'options',
        'default_permission',
        'version',
    )

    def __init__(self, *, data: ApplicationCommandPayload, state: ConnectionState) -> None:
        self._state: ConnectionState = state
        self._from_data(data)

    def __repr__(self) -> str:
        guild_id = f' guild_id={self.guild_id}' if self.guild_id else ''
        return f'<ApplicationCommand id={self.id}{guild_id} name={self.name!r} type={self.type.name!r}>'

    def _from_data(self, data: ApplicationCommandPayload) -> None:
        self.type = try_enum(ApplicationCommandType, data.get('type', 1))
        self.name = data['name']
        self.description = data.get('description')
        self.id = utils._get_as_snowflake(data, 'id')
        self.guild_id = utils._get_as_snowflake(data, 'guild_id')
        self.application_id = utils._get_as_snowflake(data, 'application_id')
        self.default_permission = data.get('default_permission', True)
        self.version = int(data.get('version', 0))

        if 'options' in data:
            self.options = [
                ApplicationCommandOption.from_dict(option)
                for option in data['options']
            ]
        else:
            self.options = None

    @property
    def guild(self) -> Optional[Guild]:
        """:class:`.Guild`: The guild that this command belongs to.

        This is retrieved from the internal cache.
        If this is a global command or if the guild isn't stored in the cache,
        this will be ``None``.
        """
        if not self.guild_id:
            return None

        return self._state._get_guild(self.guild_id)

    def is_global(self) -> bool:
        """Whether or not this command is a global command.

        Returns
        -------
        bool
            Whether or not this command is global.
        """
        return self.guild_id is None

    async def edit(
        self,
        *,
        name: str = MISSING,
        description: str = MISSING,
        options: List[NativeCommandOption] = MISSING,
        default_permission: bool = MISSING,
    ) -> ApplicationCommand:
        """|coro|

        Modifies this application command.
        All parameters here are keyword-only and optional.

        Parameters
        ----------
        name: str
            The new name of this command.
        description: str
            The new description of this command.
        options: List[:class:`.application_commands.ApplicationCommandOption`]
            A new list of options for this command.
            These should be made using the :func:`.application_commands.option` factory.
        default_permission: bool
            Whether or not this command should be enabled by default when added to a guild.

        Raises
        ------
        Forbidden
            You do not own this application command.
        HTTPException
            There was an error creating this command.

        Returns
        -------
        :class:`.ApplicationCommand`
            The newly edited command.
        """
        payload = {}

        if name is not MISSING:
            payload['name'] = name

        if description is not MISSING:
            payload['description'] = description

        if options is not MISSING:
            payload['options'] = [option.to_dict() for option in options]

        if default_permission is not MISSING:
            payload['default_permission'] = default_permission

        if self.guild_id:
            coro = self._state.http.edit_guild_command(
                self.application_id,
                self.guild_id,
                self.id,
                payload
            )
        else:
            coro = self._state.http.edit_global_command(
                self.application_id,
                self.id,
                payload
            )

        new = ApplicationCommand(data=await coro, state=self._state)
        self._state.cached_application_commands[self.id] = new
        return new

    async def delete(self) -> None:
        """|coro|

        Deletes this application command.

        Raises
        ------
        Forbidden
            You cannot delete this command.
        HTTPException
            There was an error deleting this command.
        """
        if self.guild_id:
            coro = self._state.http.delete_guild_command(
                self.application_id,
                self.guild_id,
                self.id,
            )
        else:
            coro = self._state.http.delete_global_command(
                self.application_id,
                self.id,
            )

        await coro
        self._state.cached_application_commands.pop(self.id, None)

    def _match_key(self) -> Tuple[Any, ...]:
        return (
            self.type,
            self.name,
            self.description,
            self.default_permission,
            frozenset(option._match_key() for option in self.options) if self.options else None,
        )

    @classmethod
    def from_native(
        cls,
        native_command: NativeApplicationCommand,
        *,
        id: int,
        guild_id: int = MISSING,
        state: ConnectionState
    ):
        data = native_command.to_dict()
        data['id'] = id
        if guild_id is not MISSING:
            data['guild_id'] = guild_id
        return cls(data=data, state=state)


class Interaction:
    """Represents a Discord interaction.

    An interaction happens when a user does an action that needs to
    be notified. Current examples are application commands and components.

    .. versionadded:: 2.0

    Attributes
    -----------
    id: :class:`int`
        The interaction's ID.
    type: :class:`InteractionType`
        The interaction type.
    guild_id: Optional[:class:`int`]
        The guild ID the interaction was sent from.
    channel_id: Optional[:class:`int`]
        The channel ID the interaction was sent from.
    target_id: Optional[:class:`int`]
        For context menus, the ID of the target user or message.
    application_id: :class:`int`
        The application ID that the interaction was for.
    user: Optional[Union[:class:`User`, :class:`Member`]]
        The user or member that sent the interaction.
    locale: Optional[:class:`str`]
        The selected language of the invoking user.
    guild_locale: Optional[:class:`str`]
        The guilds preferred locale, if in a guild context.
    message: Optional[:class:`Message`]
        The message that sent this interaction.
    target: Optional[Union[:class:`User`, :class:`Member`, :class:`Message`]]
        The resolved target user or message. Only applicable for context menus.

        This attribute is only resolved during application command option parsing.
    command: Optional[:class:`PartialApplicationCommand`]
        A partial representation of the command this interaction invoked.
        Use :attr:`PartialApplicationCommand.resolved` to try retrieving it from cache.
        Only applicable for application command interactions.
    token: :class:`str`
        The token to continue the interaction. These are valid
        for 15 minutes.
    client: :class:`Client`
        The client that dispatched the interaction.
        This is useful when handling interactions in a separate file.
    value: Optional[:class:`str`]
        The current text input to be used to find auto-complete choices.
        Only applicable for auto-complete interactions.

        This attribute is only resolved during application command option parsing.
    version: :class:`int`
        The auto-incrementing version identifier used by Discord.
    data: Dict[str, Any]
        The raw interaction data.
    """

    __slots__: Tuple[str, ...] = (
        'id',
        'type',
        'guild_id',
        'channel_id',
        'data',
        'application_id',
        'target_id',
        'message',
        'user',
        'target',
        'command',
        'token',
        'version',
        'client',
        'value',
        'locale',
        'guild_locale',
        '_permissions',
        '_state',
        '_session',
        '_original_message',
        '_cs_response',
        '_cs_followup',
        '_cs_channel',
        '_cs_native_command',
    )

    def __init__(self, *, data: InteractionPayload, state: ConnectionState, client: Client):
        self.client: Client = client
        self._state: ConnectionState = state
        self._session: ClientSession = state.http._HTTPClient__session
        self._original_message: Optional[InteractionMessage] = None
        self._from_data(data)

    def _from_data(self, data: InteractionPayload):
        self.id: int = int(data['id'])
        self.type: InteractionType = try_enum(InteractionType, data['type'])
        self.data: Optional[InteractionData] = data.get('data')
        self.token: str = data['token']
        self.version: int = data['version']
        self.channel_id: Optional[int] = utils._get_as_snowflake(data, 'channel_id')
        self.guild_id: Optional[int] = utils._get_as_snowflake(data, 'guild_id')
        self.application_id: int = int(data['application_id'])
        self.locale: Optional[str] = data.get('locale')
        self.guild_locale: Optional[str] = data.get('guild_locale')

        self.message: Optional[Message]
        try:
            self.message = Message(state=self._state, channel=self.channel, data=data['message'])  # type: ignore
        except KeyError:
            self.message = None

        self.user: Optional[Union[User, Member]] = None
        self._permissions: int = 0

        # TODO: there's a potential data loss here
        if self.guild_id:
            guild = self.guild or Object(id=self.guild_id)
            try:
                member = data['member']  # type: ignore
            except KeyError:
                pass
            else:
                self.user = Member(state=self._state, guild=guild, data=member)  # type: ignore
                self._permissions = int(member.get('permissions', 0))
        else:
            try:
                self.user = User(state=self._state, data=data['user'])
            except KeyError:
                pass

        # application command data
        self.target_id: int = utils._get_as_snowflake(self.data, 'target_id')
        self.target: Optional[Union[User, Member, Message]] = None
        self.value: Optional[str] = None

        self.command: Optional[PartialApplicationCommand]

        if self.type is InteractionType.application_command or self.type is InteractionType.autocomplete:
            self.command = PartialApplicationCommand(
                state=self._state,
                type=try_enum(ApplicationCommandType, self.data['type']),
                name=self.data['name'],
                id=int(self.data['id']),
                application_id=self.application_id,
            )
        else:
            self.command = None

    @property
    def created_at(self) -> datetime:
        """:class:`datetime.datetime`: When this interaction was created in UTC."""
        return utils.snowflake_time(self.id)

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild the interaction was sent from."""
        return self._state and self._state._get_guild(self.guild_id)

    @utils.cached_slot_property('_cs_channel')
    def channel(self) -> Optional[InteractionChannel]:
        """Optional[Union[:class:`abc.GuildChannel`, :class:`PartialMessageable`, :class:`Thread`]]: The channel the interaction was sent from.

        Note that due to a Discord limitation, DM channels are not resolved since there is
        no data to complete them. These are :class:`PartialMessageable` instead.
        """
        guild = self.guild
        channel = guild and guild._resolve_channel(self.channel_id)
        if channel is None:
            if self.channel_id is not None:
                type = ChannelType.text if self.guild_id is not None else ChannelType.private
                return PartialMessageable(state=self._state, id=self.channel_id, type=type)
            return None
        return channel

    @property
    def permissions(self) -> Permissions:
        """:class:`Permissions`: The resolved permissions of the member in the channel, including overwrites.

        In a non-guild context where this doesn't apply, an empty permissions object is returned.
        """
        return Permissions(self._permissions)

    @utils.cached_slot_property('_cs_response')
    def response(self) -> InteractionResponse:
        """:class:`InteractionResponse`: Returns an object responsible for handling responding to the interaction.

        A response can only be done once. If secondary messages need to be sent, consider using :attr:`followup`
        instead.
        """
        return InteractionResponse(self)

    @utils.cached_slot_property('_cs_followup')
    def followup(self) -> Webhook:
        """:class:`Webhook`: Returns the follow up webhook for follow up interactions."""
        payload = {
            'id': self.application_id,
            'type': 3,
            'token': self.token,
        }
        return Webhook.from_state(data=payload, state=self._state)

    @utils.cached_slot_property('_cs_native_command')
    def native_command(self) -> Optional[NativeApplicationCommand]:
        """Type[:class:`application_commands.ApplicationCommand`]: The native command object which was declaratively defined in your codebase.

        This is only available if this interaction is a command interaction, otherwise this will be ``None``.
        Additionally, the command must be actually defined and stored.
        """
        return self.command and self._state._application_commands_store.commands.get(self.command.id)

    async def original_message(self) -> InteractionMessage:
        """|coro|

        Fetches the original interaction response message associated with the interaction.

        If the interaction response was :meth:`InteractionResponse.send_message` then this would
        return the message that was sent using that response. Otherwise, this would return
        the message that triggered the interaction.

        Repeated calls to this will return a cached value.

        Raises
        -------
        HTTPException
            Fetching the original response message failed.
        ClientException
            The channel for the message could not be resolved.

        Returns
        --------
        InteractionMessage
            The original interaction response message.
        """

        if self._original_message is not None:
            return self._original_message

        # TODO: fix later to not raise?
        channel = self.channel
        if channel is None:
            raise ClientException('Channel for message could not be resolved')

        adapter = async_context.get()
        data = await adapter.get_original_interaction_response(
            application_id=self.application_id,
            token=self.token,
            session=self._session,
        )
        state = _InteractionMessageState(self, self._state)
        message = InteractionMessage(state=state, channel=channel, data=data)  # type: ignore
        self._original_message = message
        return message

    async def edit_original_message(
        self,
        *,
        content: Optional[str] = MISSING,
        embeds: List[Embed] = MISSING,
        embed: Optional[Embed] = MISSING,
        file: File = MISSING,
        files: List[File] = MISSING,
        view: Optional[View] = MISSING,
        allowed_mentions: Optional[AllowedMentions] = None,
    ) -> InteractionMessage:
        """|coro|

        Edits the original interaction response message.

        This is a lower level interface to :meth:`InteractionMessage.edit` in case
        you do not want to fetch the message and save an HTTP request.

        This method is also the only way to edit the original message if
        the message sent was ephemeral.

        Parameters
        ------------
        content: Optional[:class:`str`]
            The content to edit the message with or ``None`` to clear it.
        embeds: List[:class:`Embed`]
            A list of embeds to edit the message with.
        embed: Optional[:class:`Embed`]
            The embed to edit the message with. ``None`` suppresses the embeds.
            This should not be mixed with the ``embeds`` parameter.
        file: :class:`File`
            The file to upload. This cannot be mixed with ``files`` parameter.
        files: List[:class:`File`]
            A list of files to send with the content. This cannot be mixed with the
            ``file`` parameter.
        allowed_mentions: :class:`AllowedMentions`
            Controls the mentions being processed in this message.
            See :meth:`.abc.Messageable.send` for more information.
        view: Optional[:class:`~discord.ui.View`]
            The updated view to update this message with. If ``None`` is passed then
            the view is removed.

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Edited a message that is not yours.
        TypeError
            You specified both ``embed`` and ``embeds`` or ``file`` and ``files``
        ValueError
            The length of ``embeds`` was invalid.

        Returns
        --------
        :class:`InteractionMessage`
            The newly edited message.
        """

        previous_mentions: Optional[AllowedMentions] = self._state.allowed_mentions
        params = handle_message_parameters(
            content=content,
            file=file,
            files=files,
            embed=embed,
            embeds=embeds,
            view=view,
            allowed_mentions=allowed_mentions,
            previous_allowed_mentions=previous_mentions,
        )
        adapter = async_context.get()
        data = await adapter.edit_original_interaction_response(
            self.application_id,
            self.token,
            session=self._session,
            payload=params.payload,
            multipart=params.multipart,
            files=params.files,
        )

        # The message channel types should always match
        state = _InteractionMessageState(self, self._state)
        message = InteractionMessage(state=state, channel=self.channel, data=data)  # type: ignore
        if view and not view.is_finished():
            self._state.store_view(view, message.id)
        return message

    async def delete_original_message(self) -> None:
        """|coro|

        Deletes the original interaction response message.

        This is a lower level interface to :meth:`InteractionMessage.delete` in case
        you do not want to fetch the message and save an HTTP request.

        Raises
        -------
        HTTPException
            Deleting the message failed.
        Forbidden
            Deleted a message that is not yours.
        """
        adapter = async_context.get()
        await adapter.delete_original_interaction_response(
            self.application_id,
            self.token,
            session=self._session,
        )


class InteractionResponse:
    """Represents a Discord interaction response.

    This type can be accessed through :attr:`Interaction.response`.

    .. versionadded:: 2.0
    """

    __slots__: Tuple[str, ...] = (
        '_responded',
        '_parent',
    )

    def __init__(self, parent: Interaction):
        self._parent: Interaction = parent
        self._responded: bool = False

    def is_done(self) -> bool:
        """:class:`bool`: Indicates whether an interaction response has been done before.

        An interaction can only be responded to once.
        """
        return self._responded

    async def defer(self, *, loading: bool = False, ephemeral: bool = False) -> None:
        """|coro|

        Defers the interaction response.

        This is typically used when the interaction is acknowledged
        and a secondary action will be done later.

        Parameters
        -----------
        loading: :class:`bool`
            Whether the user should see a loading state.

            .. note::

                You must use the ``ephemeral`` kwarg to send ephemeral followups
                when this is set to ``True``.

        ephemeral: :class:`bool`
            Indicates whether the deferred message will eventually be ephemeral.
            This only applies if ``loading`` is set to ``True`` or for interactions
            of type :attr:`InteractionType.application_command`.

        Raises
        -------
        HTTPException
            Deferring the interaction failed.
        InteractionResponded
            This interaction has already been responded to before.
        """
        if self._responded:
            raise InteractionResponded(self._parent)

        defer_type: int = 0
        data: Optional[Dict[str, Any]] = None
        parent = self._parent
        if loading or parent.type is InteractionType.application_command:
            defer_type = InteractionResponseType.deferred_channel_message.value
            if ephemeral:
                data = {'flags': 64}
        elif parent.type in (InteractionType.component, InteractionType.modal_submit):
            defer_type = InteractionResponseType.deferred_message_update.value

        if defer_type:
            adapter = async_context.get()
            await adapter.create_interaction_response(
                parent.id, parent.token, session=parent._session, type=defer_type, data=data
            )
            self._responded = True

    async def pong(self) -> None:
        """|coro|

        Pongs the ping interaction.

        This should rarely be used.

        Raises
        -------
        HTTPException
            Ponging the interaction failed.
        InteractionResponded
            This interaction has already been responded to before.
        """
        if self._responded:
            raise InteractionResponded(self._parent)

        parent = self._parent
        if parent.type is InteractionType.ping:
            adapter = async_context.get()
            await adapter.create_interaction_response(
                parent.id, parent.token, session=parent._session, type=InteractionResponseType.pong.value
            )
            self._responded = True

    async def send_message(
        self,
        content: Optional[Any] = None,
        *,
        embed: Embed = MISSING,
        embeds: List[Embed] = MISSING,
        allowed_mentions: AllowedMentions = MISSING,
        file: File = MISSING,
        files: List[File] = MISSING,
        view: View = MISSING,
        tts: bool = False,
        ephemeral: bool = False,
    ) -> None:
        """|coro|

        Responds to this interaction by sending a message.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The content of the message to send.
        embeds: List[:class:`Embed`]
            A list of embeds to send with the content. Maximum of 10. This cannot
            be mixed with the ``embed`` parameter.
        embed: :class:`Embed`
            The rich embed for the content to send. This cannot be mixed with
            ``embeds`` parameter.
        allowed_mentions: :class:`AllowedMentions`
            Controls the mentions being processed in this message.
            See :meth:`.abc.Messageable.send` for more information.

            .. versionadded:: 2.0
        file: :class:`~discord.File`
            The new file to add. Cannot be mixed with ``files``.

            .. versionadded:: 2.0
        files: List[:class:`~discord.File`]
            The new files to add. Cannot be mixed with ``file``.

            .. versionadded:: 2.0
        tts: :class:`bool`
            Indicates if the message should be sent using text-to-speech.
        view: :class:`discord.ui.View`
            The view to send with the message.
        ephemeral: :class:`bool`
            Indicates if the message should only be visible to the user who started the interaction.
            If a view is sent with an ephemeral message and it has no timeout set then the timeout
            is set to 15 minutes.

        Raises
        -------
        HTTPException
            Sending the message failed.
        TypeError
            You specified both ``embed`` and ``embeds`` or ``file`` and ``files``.
        ValueError
            The length of ``embeds`` or ``files`` was invalid.
        InteractionResponded
            This interaction has already been responded to before.
        """
        if self._responded:
            raise InteractionResponded(self._parent)

        payload: Dict[str, Any] = {
            'tts': tts,
        }

        if embed is not MISSING and embeds is not MISSING:
            raise TypeError('cannot mix embed and embeds keyword arguments')

        if embed is not MISSING:
            embeds = [embed]

        if embeds:
            if len(embeds) > 10:
                raise ValueError('embeds cannot exceed maximum of 10 elements')
            payload['embeds'] = [e.to_dict() for e in embeds]

        if content is not None:
            payload['content'] = str(content)

        previous_allowed_mentions: Optional[AllowedMentions] = getattr(self._parent._state, 'allowed_mentions', None)
        if allowed_mentions is not MISSING:
            if previous_allowed_mentions is not None:
                payload['allowed_mentions'] = previous_allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                payload['allowed_mentions'] = allowed_mentions.to_dict()
        elif previous_allowed_mentions is not None:
            payload['allowed_mentions'] = previous_allowed_mentions.to_dict()

        if ephemeral:
            payload['flags'] = 64

        if view is not MISSING:
            payload['components'] = view.to_components()

        if file is not MISSING and files is not MISSING:
            raise TypeError('cannot mix file and files keyword arugments')

        if file is not MISSING:
            files = [file]

        if files is not MISSING:
            if len(files) > 10:
                raise ValueError('files cannot exceed maximum of 10 elements')
        else:
            files = None

        parent = self._parent
        adapter = async_context.get()
        await adapter.create_interaction_response(
            parent.id,
            parent.token,
            session=parent._session,
            type=InteractionResponseType.channel_message.value,
            data=payload,
            files=files
        )

        if view is not MISSING:
            if ephemeral and view.timeout is None:
                view.timeout = 15 * 60.0

            self._parent._state.store_view(view)

        self._responded = True

    async def edit_message(
        self,
        *,
        content: Optional[Any] = MISSING,
        embed: Optional[Embed] = MISSING,
        embeds: List[Embed] = MISSING,
        file: File = MISSING,
        files: List[File] = MISSING,
        attachments: List[Attachment] = MISSING,
        view: Optional[View] = MISSING,
        allowed_mentions: AllowedMentions = MISSING,
    ) -> None:
        """|coro|

        Responds to this interaction by editing the original message of
        a component interaction.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The new content to replace the message with. ``None`` removes the content.
        embeds: List[:class:`Embed`]
            A list of embeds to edit the message with.
        embed: Optional[:class:`Embed`]
            The embed to edit the message with. ``None`` suppresses the embeds.
            This should not be mixed with the ``embeds`` parameter.
        file: :class:`~discord.File`
            The new file to add. Cannot be mixed with ``files``.

            .. versionadded:: 2.0
        files: List[:class:`~discord.File`]
            The new files to add. Cannot be mixed with ``file``.

            .. versionadded:: 2.0
        attachments: List[:class:`Attachment`]
            A list of attachments to keep in the message. If ``[]`` is passed
            then all attachments are removed.
        allowed_mentions: :class:`AllowedMentions`
            Controls the mentions being processed in this message.
            See :meth:`.abc.Messageable.send` for more information.

            .. versionadded:: 2.0
        view: Optional[:class:`~discord.ui.View`]
            The updated view to update this message with. If ``None`` is passed then
            the view is removed.

        Raises
        -------
        HTTPException
            Editing the message failed.
        TypeError
            You specified both ``embed`` and ``embeds`` or ``file`` and ``files``.
        InteractionResponded
            This interaction has already been responded to before.
        """
        if self._responded:
            raise InteractionResponded(self._parent)

        parent = self._parent
        msg = parent.message
        state = parent._state
        message_id = msg.id if msg else None
        if parent.type not in (InteractionType.component, InteractionType.modal_submit):
            return

        payload = {}
        if content is not MISSING:
            if content is None:
                payload['content'] = None
            else:
                payload['content'] = str(content)

        if embed is not MISSING and embeds is not MISSING:
            raise TypeError('cannot mix both embed and embeds keyword arguments')

        if embed is not MISSING:
            if embed is None:
                embeds = []
            else:
                embeds = [embed]

        if embeds is not MISSING:
            payload['embeds'] = [e.to_dict() for e in embeds]

        if attachments is not MISSING:
            payload['attachments'] = [a.to_dict() for a in attachments]

        previous_allowed_mentions: Optional[AllowedMentions] = getattr(self._parent._state, 'allowed_mentions', None)
        if allowed_mentions is not MISSING:
            if previous_allowed_mentions is not None:
                payload['allowed_mentions'] = previous_allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                payload['allowed_mentions'] = allowed_mentions.to_dict()
        elif previous_allowed_mentions is not None:
            payload['allowed_mentions'] = previous_allowed_mentions.to_dict()

        if view is not MISSING:
            state.prevent_view_updates_for(message_id)
            if view is None:
                payload['components'] = []
            else:
                payload['components'] = view.to_components()

        if file is not MISSING and files is not MISSING:
            raise TypeError('cannot mix file and files keyword arugments')

        if file is not MISSING:
            files = [file]

        if files is MISSING:
            files = None

        adapter = async_context.get()
        await adapter.create_interaction_response(
            parent.id,
            parent.token,
            session=parent._session,
            type=InteractionResponseType.message_update.value,
            data=payload,
            files=files,
        )

        if view and not view.is_finished():
            state.store_view(view, message_id)

        self._responded = True

    async def update_autocomplete_choices(self, choices: AutocompleteChoicesT) -> None:
        """|coro|

        Responds to an autocomplete interaction by populating it's choices.
        There can be at most, 25 choices.

        Parameters
        ----------
        choices
            The choices to populate with.

            Parameter can be an iterable of :class:`.application_commands.ApplicationCommandOptionChoice`,
            an iterable of :class:`str`, or a dictionary mapping choice names to their return values.

        Raises
        -------
        HTTPException
             Updating autocomplete choices failed.
        TypeError
            This interaction is not an autocomplete interaction.
        InteractionResponded
            This interaction has already been responded to before.
        """
        parent = self._parent

        if self._responded:
            raise InteractionResponded(parent)

        if parent.type is not InteractionType.application_command_autocomplete:
            raise TypeError('interaction must be an autocomplete interaction to use this method.')

        if isinstance(choices, dict):
            payload = [{'name': k, 'value': v} for k, v in choices.items()]

        elif isinstance(choices, Iterable):
            payload = [
                {'name': choice, 'value': choice} if isinstance(choice, str) else choice.to_dict()
                for choice in choices
            ]

        else:
            raise TypeError('invalid iterable')

        adapter = async_context.get()
        await adapter.create_interaction_response(
            parent.id,
            parent.token,
            session=parent._session,
            type=InteractionResponseType.autocomplete_result.value,
            data={'choices': payload},
        )

        self._responded = True

    async def send_modal(self, modal: Modal) -> None:
        """|coro|

        Responds to the interaction by displaying a modal.

        Parameters
        ----------
        modal: :class:`discord.ui.Modal`
            The modal to display to the user.

        Raises
        ------
        HTTPException
            Sending the modal failed.
        InteractionResponded
            This interaction has already been responded to before.
        """
        parent = self._parent

        if self._responded:
            raise InteractionResponded(parent)

        if parent.type in (InteractionType.ping, InteractionType.modal_submit):
            raise TypeError('cannot use this type of response on this type of interaction.')

        adapter = async_context.get()
        await adapter.create_interaction_response(
            parent.id,
            parent.token,
            session=parent._session,
            type=InteractionResponseType.modal.value,
            data=modal.to_dict(),
        )

        parent._state.store_modal(modal)
        self._responded = True


class _InteractionMessageState:
    __slots__ = ('_parent', '_interaction')

    def __init__(self, interaction: Interaction, parent: ConnectionState):
        self._interaction: Interaction = interaction
        self._parent: ConnectionState = parent

    def _get_guild(self, guild_id):
        return self._parent._get_guild(guild_id)

    def store_user(self, data):
        return self._parent.store_user(data)

    def create_user(self, data):
        return self._parent.create_user(data)

    @property
    def http(self):
        return self._parent.http

    def __getattr__(self, attr):
        return getattr(self._parent, attr)


class InteractionMessage(Message):
    """Represents the original interaction response message.

    This allows you to edit or delete the message associated with
    the interaction response. To retrieve this object see :meth:`Interaction.original_message`.

    This inherits from :class:`discord.Message` with changes to
    :meth:`edit` and :meth:`delete` to work.

    .. versionadded:: 2.0
    """

    __slots__ = ()
    _state: _InteractionMessageState

    async def edit(
        self,
        content: Optional[str] = MISSING,
        embeds: List[Embed] = MISSING,
        embed: Optional[Embed] = MISSING,
        file: File = MISSING,
        files: List[File] = MISSING,
        view: Optional[View] = MISSING,
        allowed_mentions: Optional[AllowedMentions] = None,
    ) -> InteractionMessage:
        """|coro|

        Edits the message.

        Parameters
        ------------
        content: Optional[:class:`str`]
            The content to edit the message with or ``None`` to clear it.
        embeds: List[:class:`Embed`]
            A list of embeds to edit the message with.
        embed: Optional[:class:`Embed`]
            The embed to edit the message with. ``None`` suppresses the embeds.
            This should not be mixed with the ``embeds`` parameter.
        file: :class:`File`
            The file to upload. This cannot be mixed with ``files`` parameter.
        files: List[:class:`File`]
            A list of files to send with the content. This cannot be mixed with the
            ``file`` parameter.
        allowed_mentions: :class:`AllowedMentions`
            Controls the mentions being processed in this message.
            See :meth:`.abc.Messageable.send` for more information.
        view: Optional[:class:`~discord.ui.View`]
            The updated view to update this message with. If ``None`` is passed then
            the view is removed.

        Raises
        -------
        HTTPException
            Editing the message failed.
        Forbidden
            Edited a message that is not yours.
        TypeError
            You specified both ``embed`` and ``embeds`` or ``file`` and ``files``
        ValueError
            The length of ``embeds`` was invalid.

        Returns
        ---------
        :class:`InteractionMessage`
            The newly edited message.
        """
        return await self._state._interaction.edit_original_message(
            content=content,
            embeds=embeds,
            embed=embed,
            file=file,
            files=files,
            view=view,
            allowed_mentions=allowed_mentions,
        )

    async def delete(self, *, delay: Optional[float] = None) -> None:
        """|coro|

        Deletes the message.

        Parameters
        -----------
        delay: Optional[:class:`float`]
            If provided, the number of seconds to wait before deleting the message.
            The waiting is done in the background and deletion failures are ignored.

        Raises
        ------
        Forbidden
            You do not have proper permissions to delete the message.
        NotFound
            The message was deleted already.
        HTTPException
            Deleting the message failed.
        """

        if delay is not None:

            async def inner_call(delay: float = delay):
                await asyncio.sleep(delay)
                try:
                    await self._state._interaction.delete_original_message()
                except HTTPException:
                    pass

            asyncio.create_task(inner_call())
        else:
            await self._state._interaction.delete_original_message()
