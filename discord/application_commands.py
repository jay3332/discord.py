"""
The MIT License (MIT)

Copyright (c) 2021-present Rapptz & jay3332

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

import inspect
import sys

from collections import defaultdict
from dataclasses import dataclass

from .abc import GuildChannel, Messageable, Snowflake
from .channel import (
    TextChannel,
    VoiceChannel,
    CategoryChannel,
    StoreChannel,
    StageChannel,
    Thread,
    _threaded_guild_channel_factory,
)
from .enums import ApplicationCommandType, ApplicationCommandOptionType, ChannelType, try_enum
from .errors import IncompatibleCommandSignature
from .member import Member
from .message import Attachment, Message
from .object import Object
from .role import Role
from .user import User
from .utils import get, find, MISSING, resolve_annotation

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Final,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Sequence,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    from .guild import Guild
    from .interactions import Interaction, AutocompleteChoicesT
    from .state import ConnectionState

    from .types.interactions import (
        ApplicationCommand as ApplicationCommandPayload,
        ApplicationCommandOption as ApplicationCommandOptionPayload,
        ApplicationCommandOptionChoice as ApplicationCommandOptionChoicePayload,
        ApplicationCommandInteractionData,
        ApplicationCommandInteractionDataOption,
        ApplicationCommandInteractionDataResolved,
    )

    ApplicationCommandOptionChoiceT = Union[
        Dict[str, Union[str, float]],
        Sequence['ApplicationCommandOptionChoice'],
        Sequence[Union[str, float]]
    ]

    ApplicationCommandOptionTypeT = Union[
        ApplicationCommandType,
        Literal[
            str,
            int,
            bool,
            User,
            Member,
            Messageable,
            TextChannel,
            Thread,
            VoiceChannel,
            StageChannel,
            StoreChannel,
            CategoryChannel,
            GuildChannel,
            Role,
            Object,
            Snowflake,
            Attachment,
            float,
        ]
    ]

    AutocompleteCallbackT = Callable[['ApplicationCommandMeta', Interaction], Awaitable[AutocompleteChoicesT]]

_PY_310 = sys.version_info >= (3, 10)

if _PY_310:
    from types import UnionType

OPTION_TYPE_MAPPING: Final[Dict[type, ApplicationCommandOptionType]] = {
    str: ApplicationCommandOptionType.string,
    int: ApplicationCommandOptionType.integer,
    bool: ApplicationCommandOptionType.boolean,
    User: ApplicationCommandOptionType.user,
    Member: ApplicationCommandOptionType.user,
    Messageable: ApplicationCommandOptionType.channel,
    TextChannel: ApplicationCommandOptionType.channel,
    Thread: ApplicationCommandOptionType.channel,
    VoiceChannel: ApplicationCommandOptionType.channel,
    StageChannel: ApplicationCommandOptionType.channel,
    StoreChannel: ApplicationCommandOptionType.channel,
    CategoryChannel: ApplicationCommandOptionType.channel,
    GuildChannel: ApplicationCommandOptionType.channel,
    Role: ApplicationCommandOptionType.role,
    Object: ApplicationCommandOptionType.mentionable,
    Snowflake: ApplicationCommandOptionType.mentionable,
    Attachment: ApplicationCommandOptionType.attachment,
    float: ApplicationCommandOptionType.number,
}

CHANNEL_TYPE_MAPPING: Final[Dict[type, ChannelType]] = {
    Messageable: (
        ChannelType.text,
        ChannelType.news,
        ChannelType.news_thread,
        ChannelType.public_thread,
        ChannelType.private_thread,
    ),
    TextChannel: (ChannelType.text, ChannelType.news),
    Thread: (ChannelType.news_thread, ChannelType.public_thread, ChannelType.private_thread),
    VoiceChannel: ChannelType.voice,
    StageChannel: ChannelType.stage_voice,
    StoreChannel: ChannelType.store,
    CategoryChannel: ChannelType.category,
}

APPLICABLE_CHANNEL_TYPES: Final[Tuple[Union[Type[GuildChannel], Type[Messageable]], ...]] = tuple(CHANNEL_TYPE_MAPPING)

RESERVED_ATTRIBUTE_NAMES: Final[Tuple[str, ...]] = (
    '__application_command_type__',
    '__application_command_name__',
    '__application_command_description__',
    '__application_command_default_option__',
    '__application_command_options__',
    '__application_command_parent__',
    '__application_command_children__',
    '__application_command_guild_id__',
    '__application_command_tree__',
)

__all__ = (
    'ApplicationCommand',
    'ApplicationCommandMeta',
    'ApplicationCommandOption',
    'ApplicationCommandOptionChoice',
    'ApplicationCommandTree',
    'SlashCommand',
    'MessageCommand',
    'UserCommand',
    'option',
)


class ApplicationCommandTree:
    """Represents a category of application commands.

    Parameters
    ----------
    name: str
        The name of this tree. Defaults to ``None``.
    """

    def __init__(self, name: str = None, *, guild_id: int = MISSING) -> None:
        self.name: Optional[str] = name
        self._guild_id: int = guild_id

        self._global_commands: Set[ApplicationCommandMeta] = set()
        self._guild_commands: Dict[int, Set[ApplicationCommandMeta]] = defaultdict(set)

    @property
    def commands(self) -> List[ApplicationCommandMeta]:
        """List[Type[:class:`.ApplicationCommand`]]: A list of all application commands this tree holds.

        .. note::
            There may be duplicate commands in the returned list if a command is present
            in multiple guilds.

        .. versionadded:: 2.0
        """
        result = [command for v in self._guild_commands.values() for command in v]
        result.extend(self._global_commands)
        return result

    @property
    def global_commands(self) -> List[ApplicationCommandMeta]:
        """List[Type[:class:`.ApplicationCommand`]]: A list of all global application commands this tree holds.

        .. versionadded:: 2.0
        """
        return list(self._global_commands)

    def guild_commands_for(self, guild_id: int, /) -> None:
        """Returns a list of all application commands this tree holds that are in the given guild.

        Parameters
        ----------
        guild_id: int
            The ID of the guild.

        Returns
        -------
        List[Type[:class:`.ApplicationCommand`]]
        """
        return list(self._guild_commands[guild_id])

    def add_command(self, command: ApplicationCommandMeta, *, guild_id: int = MISSING) -> None:
        """Adds a command to this tree.

        Parameters
        ----------
        command: Type[:class:`.ApplicationCommand`]
            The command to add.
        guild_id: int
            The ID of the guild that this command will be in.
            Leave as ``None`` to make this command global.
        """
        if (
            guild_id := guild_id
            or command.__application_command_guild_id__
            or self._guild_id
        ):
            self._guild_commands[guild_id].add(command)

        else:
            self._global_commands.add(command)
        command.__application_command_tree__ = self

    def add_commands(self, *commands: ApplicationCommandMeta, guild_id: int = MISSING) -> None:
        """Adds multiple commands to this tree at once.

        Parameters
        ----------
        *commands: Type[:class:`.ApplicationCommand`]
            The commands to add.
        guild_id: int
            The ID of the guild that these commands will be in.
            Leave as ``None`` to make these commands global.
        """
        for command in commands:
            self.add_command(command, guild_id=guild_id)


class ApplicationCommandOptionChoice(NamedTuple):
    """Represents a choice of an :class:`.ApplicationCommandOption`.

    Parameters
    ----------
    name: str
        The name of this choice.
    value: Union[str, int, float]
        The value that should be returned when this choice is selected.
    """
    name: str
    value: Union[str, float]  # float is almost identical to Union[int, float]

    def to_dict(self) -> ApplicationCommandOptionChoicePayload:
        return {
            'name': self.name,
            'value': self.value
        }

    def __repr__(self) -> str:
        return f'<ApplicationCommandOptionChoice name={self.name!r} value={self.value!r}>'


@dataclass
class ApplicationCommandOption:
    """Represents an option of an :class:`.ApplicationCommand`.

    These should be constructed via :func:`.option`.
    """
    type: ApplicationCommandOptionType
    name: str
    description: str
    required: bool = False
    choices: List[ApplicationCommandOptionChoice] = MISSING
    channel_types: List[ChannelType] = MISSING
    min_value: float = MISSING
    max_value: float = MISSING
    default: Any = MISSING
    _autocomplete_callback: AutocompleteCallbackT = MISSING

    def _update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if not getattr(self, k, False):
                setattr(self, k, v)

    def autocomplete(self, callback: AutocompleteCallbackT) -> AutocompleteCallbackT:
        """Makes this option an auto-complete option with the given callback.

        The callback should take two parameters: ``self`` and ``interaction``.
        The value that is returned will then be passed into :meth:`~.InteractionResponse.update_autocomplete_choices`.
        See it's documentation for information on the return types.

        You can access the inputted value using :attr:`~.Interaction.value`.

        .. note:: There can only be a maximum of 25 choices.

        .. note::
            Some attributes that have not been filled in will be empty.
            That is, trying to access them will raise an :exc:`AttributeError`.

        Usage: ::

            class AutoComplete(ApplicationCommand, name='autocomplete-test'):
                \"""Test autocomplete options\"""
                text: str = option(description='Type here')

                @text.autocomplete
                async def autocomplete_text(self, interaction: discord.Interaction):
                    return get_matches(['apple', 'banana'], interaction.value)

        Raises
        ------
        ValueError
            There is already an autocomplete callback for this option.
        TypeError
            This cannot be used in conjunction with ``choices``.
        """
        if self._autocomplete_callback:
            raise ValueError('There is already an autocomplete callback for this option.')

        if self.choices:
            raise TypeError('Cannot be used in conjunction with "choices" parameter')

        self._autocomplete_callback = callback
        return callback

    def to_dict(self) -> ApplicationCommandOptionPayload:
        payload = {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'required': bool(self.required),
        }

        if self.choices is not MISSING:
            payload['choices'] = [choice.to_dict() for choice in self.choices]

        if self.channel_types is not MISSING:
            payload['channel_types'] = [type.value for type in self.channel_types]

        if self._autocomplete_callback is not MISSING:
            payload['autocomplete'] = True

        if self.min_value is not MISSING:
            payload['min_value'] = self.min_value

        if self.max_value is not MISSING:
            payload['max_value'] = self.max_value

        return payload

    def _match_key(self) -> Tuple[Any, ...]:
        return (
            self.type,
            self.name,
            self.description,
            bool(self.required),
            None,  # No children
            frozenset((choice.name, choice.value) for choice in self.choices) if self.choices else None,
            frozenset(self.channel_types) if self.channel_types else None,
            bool(self._autocomplete_callback),
        )

    def __repr__(self) -> str:
        return f'<ApplicationCommandOption type={self.type.name!r} name={self.name!r} required={self.required}>'


def option(
    *,
    type: ApplicationCommandOptionTypeT = MISSING,
    name: str = MISSING,
    description: str,
    required: bool = MISSING,
    optional: bool = MISSING,
    choices: ApplicationCommandOptionChoiceT = MISSING,
    channel_types: Iterable[ChannelType] = MISSING,
    min_value: float = MISSING,
    max_value: float = MISSING,
    default: Any = None,
) -> ApplicationCommandOption:
    """Creates an application command option which can be used on :class:`.ApplicationCommand`.

    All parameters here are keyword-only.

    Parameters
    ----------
    type: Union[:class:`~.ApplicationCommandType`, :class:`type`]
        The type of this option. Defaults to the annotation given with this option, or ``str``.
    name: str
        The name of this option.
    description: str
        The description of this option. Required.
    required: bool
        Whether or not this option is required. Defaults to ``False``.
    optional: bool
        An inverted alias for ``required``. This cannot be used with ``required``, and vice-versa.
    choices
        If specified, only the choices given will be available to be selected by the user.

        Argument should either be a mapping of choice names to their return values,
        A sequence of the possible choices, or a sequence of :class:`.ApplicationCommandOptionChoice`.
    channel_types: Iterable[:class:`ChannelType`]
        An iterable of all the channel types this option will take.
        Defaults to taking all channel types.

        Only applicable for ``channel`` types.
    min_value: Union[:class:`int`, :class:`float`]
        The minimum numerical value that this option can have.
        Defaults to no minimum value.

        Only applicable for ``integer`` or ``number`` types.
    max_value: Union[:class:`int`, :class:`float`]
        The maximum numerical value that this option can have. Must greater than or equal to ``min_value`` if it is provided.
        Defaults to no maximum value.

        Only applicable for ``integer`` or ``number`` types.
    default
        The default value passed to the attribute if the option is not passed.
        Defaults to ``None``.

    Returns
    -------
    :class:`.ApplicationCommandOption`
    """

    if required is not MISSING and optional is not MISSING:
        raise ValueError('only one of required and optional parameters can be specified.')

    if required is MISSING:
        required = False if optional is MISSING else not optional

    if type is not MISSING and not isinstance(type, ApplicationCommandOptionType):
        try:
            type = OPTION_TYPE_MAPPING[type]
        except KeyError:
            raise ValueError(f'{type!r} is an incompatable option type.')

    if choices is not MISSING:
        if isinstance(choices, dict):
            choices = [
                ApplicationCommandOptionChoice(name=k, value=v)
                for k, v in choices.items()
            ]

        elif isinstance(choices, Sequence):
            if isinstance(choices[0], ApplicationCommandOptionChoice):
                choices = list(choices)
            else:
                choices = [
                    ApplicationCommandOptionChoice(name=str(choice), value=choice)
                    for choice in choices
                ]

    if channel_types is not MISSING and not channel_types:
        channel_types = MISSING

    return ApplicationCommandOption(
        type=type,
        name=name and name.casefold(),
        description=description,
        required=required,
        choices=choices,
        channel_types=channel_types and list(channel_types),
        min_value=min_value,
        max_value=max_value,
        default=default,
    )


def _get_namespaces(attrs: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    try:
        global_ns = sys.modules[attrs['__module__']].__dict__
    except KeyError:
        global_ns = {}

    frame = inspect.currentframe()
    try:
        if frame is None:
            local_ns = {}
        else:
            parent = frame if frame.f_back is None else frame.f_back
            local_ns = parent.f_locals
    finally:
        del frame

    return local_ns, global_ns


def _resolve_union_type_annotation(
    *,
    option: ApplicationCommandOption,
    args: Iterable[Type[Any]],
) -> None:
    if not all(arg in APPLICABLE_CHANNEL_TYPES or isinstance(arg, ChannelType) for arg in args):
        raise TypeError('union types for options are not supported.')

    if not option.channel_types:
        channel_types = set()

        for arg in args:
            if arg is GuildChannel:
                return

            try:
                entry = CHANNEL_TYPE_MAPPING[arg]
            except KeyError:
                raise TypeError(f'{arg!r} is an incompatible option type.')

            if isinstance(entry, ChannelType):
                channel_types.add(entry)
            else:
                channel_types.update(entry)

        option.channel_types = list(channel_types) or MISSING


def _resolve_option_annotation(
    option: ApplicationCommandOption,
    annotation: str,
    *,
    args: Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]],
) -> None:
    annotation = resolve_annotation(annotation, *args)

    if not isinstance(annotation, ApplicationCommandOptionType):
        try:
            if _PY_310 and isinstance(annotation, UnionType):
                origin = Union
            else:
                origin = annotation.__origin__
        except AttributeError:
            pass
        else:
            if origin is Union:
                args = annotation.__args__

                if args[-1] is type(None):
                    args = annotation.__args__[:-1]
                    option.required = False

                if len(args) == 1:
                    annotation = args[0]
                else:
                    annotation = GuildChannel
                    _resolve_union_type_annotation(option=option, args=args)

            elif origin is Literal:
                annotation = type(annotation.__args__[0])
                option.choices = [
                    ApplicationCommandOptionChoice(name=str(arg), value=arg)
                    for arg in args
                ]

        if annotation in APPLICABLE_CHANNEL_TYPES and not option.channel_types:
            entry = CHANNEL_TYPE_MAPPING[annotation]
            option.channel_types = [entry] if isinstance(entry, ChannelType) else list(entry)

        try:
            annotation = OPTION_TYPE_MAPPING[annotation]
        except KeyError:
            raise TypeError(f'{annotation!r} is an incompatable option type.')

    option.type = annotation


def _get_application_command_options(
    attrs: Dict[str, Any],
    *,
    option_kwargs: Dict[str, Any] = MISSING
) -> Dict[str, ApplicationCommandOption]:
    if option_kwargs is MISSING:
        option_kwargs = {}

    local_ns, global_ns = _get_namespaces(attrs)
    annotations = attrs.get('__annotations__', {})

    result = {}
    args = global_ns, local_ns, {}

    for name, value in attrs.items():
        if not isinstance(value, ApplicationCommandOption):
            continue

        value._update(**option_kwargs)

        if value.type is MISSING:
            try:
                _resolve_option_annotation(value, annotations[name], args=args)
            except KeyError:
                value.type = ApplicationCommandOptionType.string

        if value.name is MISSING:
            value.name = name.casefold()

        result[name] = value

    if option_kwargs:
        for attr, annotation in annotations.items():
            if attr in result:
                continue

            result[attr] = res = option(**option_kwargs)
            if res.name is MISSING:
                res.name = attr.casefold()

            if res.type is MISSING:
                _resolve_option_annotation(res, annotation, args=args)

    return result


class ApplicationCommandMeta(type):
    """The metaclass for defining an application command.

    See :class:`.ApplicationCommand` for an example on defining one.

    Parameters
    ----------
    type: :class:`~.ApplicationCommandType`
        The type of command this is. Defaults to ``chat_input`` (slash commands).
    name: str
        The name of this application command. Defaults to the class name.
    description: str
        The description of this command. Must be present here or as a doc-string.
    parent: Type[:class:`.ApplicationCommand`]
        The parent command of this command. Note that parent commands can't have callbacks.
    default_permission: bool
        Whether or not this command is enabled by default when added to a guild.
        Defaults to ``True``
    option_kwargs: Dict[str, Any]
        Default kwargs to pass in for each option.
    guild_id: int
        The ID of the guild that this command will automatically be added to.
        Leave blank to make this a global command.
    tree: :class:`.ApplicationCommandTree`
        The command tree this command will be added to.
    """

    if TYPE_CHECKING:
        __application_command_type__: ApplicationCommandType
        __application_command_name__: str
        __application_command_description__: str
        __application_command_default_permission__: bool
        __application_command_options__: Dict[str, ApplicationCommandOption]
        __application_command_parent__: ApplicationCommandMeta
        __application_command_children__: Dict[str, ApplicationCommand]
        __application_command_guild_id__: int
        __application_command_tree__: ApplicationCommandTree

    def __new__(
        mcs: Type[ApplicationCommandMeta],
        cls_name: str,
        bases: Tuple[type, ...],
        attrs: Dict[str, Any],
        *,
        type: ApplicationCommandType = MISSING,
        name: str = MISSING,
        description: str = MISSING,
        parent: ApplicationCommandMeta = MISSING,
        default_permission: bool = True,
        option_kwargs: Dict[str, Any] = MISSING,
        guild_id: int = MISSING,
        tree: ApplicationCommandTree = MISSING,
        **kwargs,
    ) -> ApplicationCommandMeta:
        if type is MISSING:
            try:
                base = bases[0]
            except IndexError:
                base = None

            if isinstance(base, mcs):
                type = base.__application_command_type__
            else:
                type = ApplicationCommandType.chat_input

        if not isinstance(type, ApplicationCommandType):
            type = try_enum(ApplicationCommandType, type)

        if not isinstance(type, ApplicationCommandType):
            raise TypeError('application command types must be an ApplicationCommandType.')

        if 'callback' in attrs and not callable(attrs['callback']):
            raise TypeError('application command callback must be callable.')

        if name is MISSING:
            name = cls_name

        if description is MISSING and type is ApplicationCommandType.chat_input:
            try:
                description = inspect.cleandoc(attrs['__doc__'])
            except (AttributeError, KeyError):  # AttributeError if docstring is None
                raise TypeError('chat input commands must have a description.')

        if type is ApplicationCommandType.chat_input:
            name = name.casefold()
        else:
            description = MISSING

        attrs.update(
            __application_command_type__=type,
            __application_command_name__=name,
            __application_command_description__=description,
            __application_command_parent__=parent,
            __application_command_default_permission__=default_permission,
            __application_command_guild_id__=guild_id,
        )

        attrs['__application_command_options__'] = _get_application_command_options(attrs, option_kwargs=option_kwargs)
        attrs['__application_command_children__'] = children = {}

        cls = super().__new__(mcs, cls_name, bases, attrs, **kwargs)

        if parent is not MISSING:
            parent.__application_command_children__[cls.__application_command_name__] = cls

        for name, value in attrs.items():
            if name not in RESERVED_ATTRIBUTE_NAMES and isinstance(value, mcs):
                children[value.__application_command_name__] = value
                value.__application_command_parent__ = cls

        if tree is not MISSING:
            tree.add_command(cls)

        return cls

    def to_option_dict(cls) -> ApplicationCommandOptionPayload:
        payload = {
            'name': cls.__application_command_name__,
            'description': cls.__application_command_description__,
            'options': [],
        }

        if children := cls.__application_command_children__:
            option_type = ApplicationCommandOptionType.subcommand_group
            payload['options'].extend(command.to_option_dict() for command in children.values())
        else:
            option_type = ApplicationCommandOptionType.subcommand

        if options := cls.__application_command_options__:
            payload['options'].extend(option.to_dict() for option in options.values())

        if not payload['options']:
            del payload['options']

        payload['type'] = option_type.value
        return payload

    def to_dict(cls) -> ApplicationCommandPayload:
        payload = {
            'type': cls.__application_command_type__.value,
            'name': cls.__application_command_name__,
            'default_permission': cls.__application_command_default_permission__,
            'options': [],
        }

        if cls.__application_command_type__ is ApplicationCommandType.chat_input:
            payload['description'] = cls.__application_command_description__

        if children := cls.__application_command_children__:
            payload['options'].extend(command.to_option_dict() for command in children.values())

        if options := cls.__application_command_options__:
            payload['options'].extend(option.to_dict() for option in options.values())

        if not payload['options']:
            del payload['options']

        return payload

    def _match_key(cls) -> Tuple[Any, ...]:
        options = []

        if children := cls.__application_command_children__:
            options.extend(command._option_match_key() for command in children.values())

        if options_ := cls.__application_command_options__:
            options.extend(option._match_key() for option in options_.values())

        return (
            cls.__application_command_type__,
            cls.__application_command_name__,
            cls.__application_command_description__ or '',
            bool(cls.__application_command_default_permission__),
            frozenset(options) if options else None,
        )

    def _option_match_key(cls) -> Tuple[Any, ...]:
        options = []

        if has_children := len(children := cls.__application_command_children__):
            options.extend(command._option_match_key() for command in children.values())

        if options_ := cls.__application_command_options__:
            options.extend(option._match_key() for option in options_.values())

        return (
            ApplicationCommandOptionType.subcommand_group if has_children else ApplicationCommandOptionType.subcommand,
            cls.__application_command_name__,
            cls.__application_command_description__ or '',
            False,
            frozenset(options) if options else None,
            None,
            None,
            False,
        )


class ApplicationCommand(metaclass=ApplicationCommandMeta):
    """Represents an application command.

    Example
    -------

    .. code-block:: python3

        import discord
        from discord.application_commands import ApplicationCommand, option

        class Hello(ApplicationCommand, name='hello'):
            \"""Greet someone\"""
            user: discord.Member = option(description='The member to greet')

            async def callback(self, interaction: discord.Interaction):
                user = self.user or interaction.user
                await interaction.response.send_message(f'Hello {user.mention}!')
    """

    async def command_check(self, interaction: Interaction) -> bool:
        """|coro|

        The check for when this command is invoked.

        If an error is raised, or this check fails, the callback will not be ran.
        You should respond to the interaction here to prevent client-side errors.

        Parameters
        ----------
        interaction: :class:`~.Interaction`
            The interaction to check.

        Returns
        -------
        bool
            Whether or not this check succeeded or not.
        """
        return True

    async def command_error(self, interaction: Interaction, error: Exception) -> None:
        """|coro|

        The error handler for when an error is raised either during the :meth:`command_check`
        or during the :meth:`callback`.

        If an error is raised here, :func:`on_application_command_error` will be dispatched.

        Parameters
        ----------
        interaction: :class:`~.Interaction`
            The interaction that caused this error.
        error: :exc:`Exception`
            The exception that was raised.
        """
        raise error

    async def callback(self, interaction: Interaction) -> None:
        """|coro|

        The callback for when this command is invoked.

        Parameters
        ----------
        interaction: :class:`~.Interaction`
            The interaction created when this command was invoked.
        """


class ApplicationCommandStore:
    def __init__(self, state: ConnectionState) -> None:
        self.state: ConnectionState = state
        self.commands: Dict[int, ApplicationCommandMeta] = {}

    def store_command(self, id: int, command: ApplicationCommandMeta) -> None:
        self.commands[id] = command

    async def _handle_error(
        self,
        command: ApplicationCommand,
        interaction: Interaction,
        error: Exception,
    ) -> None:
        try:
            await command.command_error(interaction, error)
        except Exception as exc:
            self.state.dispatch('application_command_error', interaction, exc)

    async def invoke(self, command: ApplicationCommand, interaction: Interaction) -> None:
        self.state.dispatch('application_command', interaction)

        try:
            can_run = await command.command_check(interaction)
        except Exception as exc:
            return await self._handle_error(command, interaction, exc)

        if can_run:
            try:
                await command.callback(interaction)
            except Exception as exc:
                return await self._handle_error(command, interaction, exc)
            else:
                self.state.dispatch('application_command_completion', interaction)

    async def request_autocomplete_choices(
        self,
        command: ApplicationCommand,
        option: ApplicationCommandOption,
        interaction: Interaction,
    ) -> None:
        if interaction.response.is_done():
            return
        try:
            result = option._autocomplete_callback(command, interaction)
            if inspect.isasyncgen(result):
                result = [choice async for choice in result]
            else:
                result = await result

            await interaction.response.update_autocomplete_choices(result)
        except Exception as exc:
            return await self._handle_error(command, interaction, exc)

    @staticmethod
    def _sanitize_command(
        *,
        options: Sequence[ApplicationCommandInteractionDataOption],
        command: ApplicationCommandMeta,
    ) -> Tuple[ApplicationCommand, List[ApplicationCommandInteractionDataOption]]:
        result = options

        for option in result:
            if option['type'] < 3:
                command = command.__application_command_children__[option['name']]
                result = option.get('options', [])

                if option['type'] == 2:
                    command = command.__application_command_children__[result[0]['name']]
                    result = result[0].get('options', [])

                break
        return command(), result

    def _resolve_user(
        self,
        *,
        resolved: Dict[str, Dict[str, Dict[str, Any]]],
        guild: Optional[Guild],
        user_id: str,
    ) -> Union[User, Member]:
        user_data = member_data = None

        if user_id in resolved['users']:
            user_data = resolved['users'][user_id]

        if user_id in resolved['members']:
            member_data = resolved['members'][user_id]

        if user_data and member_data:
            member_data['user'] = user_data

        if member_data is not None and guild:
            return Member(data=member_data, state=self.state, guild=guild)

        return User(data=user_data, state=self.state)

    def _parse_context_menu(
        self,
        *,
        data: ApplicationCommandInteractionData,
        resolved: Dict[str, Dict[str, Dict[str, Any]]],
        interaction: Interaction,
        guild: Guild,
    ) -> None:
        target_id = data['target_id']

        if data['type'] == 2:
            interaction.target = self._resolve_user(
                resolved=resolved,
                guild=guild,
                user_id=target_id,
            )
            return

        data = resolved['messages'][target_id]
        data['guild_id'] = interaction.guild_id
        channel, _ = self.state._get_guild_channel(data)

        interaction.target = Message(
            data=data,
            channel=channel,
            state=self.state,
        )

    def _parse_options(
        self,
        *,
        options: List[ApplicationCommandInteractionDataOption],
        resolved: ApplicationCommandInteractionDataResolved,
        command: ApplicationCommand,
        guild: Optional[Guild],
    ) -> None:
        for option in options:
            value = option['value']
            type = option['type']

            if type == 6:
                value = self._resolve_user(resolved=resolved, guild=guild, user_id=value)

            elif type == 7:
                # Prefer from cache (Data is only partial)
                cached = (guild.get_channel_or_thread if guild else self.state.get_channel)(int(value))
                if cached is None:
                    channel_data = defaultdict(lambda: None)
                    channel_data.update(resolved['channels'][value])
                    factory, _ = _threaded_guild_channel_factory(channel_data['type'])
                    value = factory(state=self.state, data=channel_data, guild=guild)
                else:
                    value = cached

            elif type == 8:
                # Here we prefer from payload instead, as the data
                # is more up to date.
                role_data = resolved['roles'][value]
                value = Role(state=self.state, data=role_data, guild=guild)

            elif type == 9:
                try:
                    role_data = resolved['roles'][value]
                    value = Role(state=self.state, data=role_data, guild=guild)
                except KeyError:
                    value = self._resolve_user(resolved=resolved, guild=guild, user_id=value)

            elif type == 11:
                attachment = resolved['attachments'][value]
                value = Attachment(state=self.state, data=attachment)

            for k, v in command.__class__.__application_command_options__.items():
                if v.name == option['name']:
                    setattr(command, k, value)
                    break

    def _sanitize_data(
        self,
        data: ApplicationCommandInteractionData,
        command: ApplicationCommandMeta,
        interaction: Interaction,
    ) -> Tuple[
        List[ApplicationCommandInteractionDataOption],
        ApplicationCommandInteractionDataResolved,
        ApplicationCommandMeta,
        Guild,
    ]:
        options = data.get('options', [])
        resolved = data.get('resolved', {})
        command, options = self._sanitize_command(options=options, command=command)
        maybe_guild = self.state._get_guild(interaction.guild_id)

        return options, resolved, command, maybe_guild

    def _parse_autocomplete_options(
        self,
        *,
        data: ApplicationCommandInteractionData,
        command: ApplicationCommandMeta,
        interaction: Interaction,
    ) -> Tuple[ApplicationCommand, ApplicationCommandOption]:
        options, resolved, command, guild = self._sanitize_data(data=data, command=command, interaction=interaction)

        option = find(lambda o: o.get('focused'), options)
        interaction.value = option['value']

        self._parse_options(options=options, resolved=resolved, command=command, guild=guild)

        focused_option = get(command.__class__.__application_command_options__.values(), name=option['name'])
        return command, focused_option

    def _parse_application_command_options(
        self,
        *,
        data: ApplicationCommandInteractionData,
        command: ApplicationCommandMeta,
        interaction: Interaction,
    ) -> ApplicationCommand:
        options, resolved, command, guild = self._sanitize_data(data=data, command=command, interaction=interaction)

        if data['type'] > 1:
            # Not a slash command
            self._parse_context_menu(
                data=data,
                resolved=resolved,
                guild=guild,
                interaction=interaction,
            )
            return command

        for name, option in command.__class__.__application_command_options__.items():
            setattr(command, name, option.default)  # For options that were not given

        self._parse_options(options=options, resolved=resolved, command=command, guild=guild)
        return command

    def _get_command(self, interaction: Interaction) -> ApplicationCommandMeta:
        try:
            return self.commands[interaction.command.id]
        except KeyError:
            message = f'Received command {interaction.command.name!r} with ID {interaction.command.id}, but it is not stored'
            raise RuntimeError(message) from None

    def dispatch(self, data: ApplicationCommandInteractionData, interaction: Interaction) -> None:
        try:
            command_factory = self._get_command(interaction)
            kwargs = {'data': data, 'command': command_factory, 'interaction': interaction}

            try:
                command = self._parse_application_command_options(**kwargs)
            except (KeyError, IndexError):
                raise IncompatibleCommandSignature(**kwargs)
        except Exception as exc:
            return self.state.dispatch('application_command_error', interaction, exc)

        self.state.loop.create_task(
            self.invoke(command, interaction), name=f'discord-application-commands-dispatch-{interaction.id}'
        )

    def dispatch_autocomplete(self, data: ApplicationCommandInteractionData, interaction: Interaction) -> None:
        try:
            command_factory = self._get_command(interaction)
            kwargs = {'data': data, 'command': command_factory, 'interaction': interaction}

            try:
                command, option = self._parse_autocomplete_options(**kwargs)
            except (KeyError, IndexError):
                raise IncompatibleCommandSignature(**kwargs)
        except Exception as exc:
            return self.state.dispatch('application_command_error', interaction, exc)

        self.state.loop.create_task(
            self.request_autocomplete_choices(command, option, interaction),
            name=f'discord-application-commands-dispatch-{interaction.id}',
        )


# shortcuts

class SlashCommand(ApplicationCommand, type=ApplicationCommandType.chat_input):
    """A shortcut for doing ``class Command(ApplicationCommand, type=ApplicationCommandType.chat_input)``."""


class MessageCommand(ApplicationCommand, type=ApplicationCommandType.message):
    """A shortcut for doing ``class Command(ApplicationCommand, type=ApplicationCommandType.message)``."""


class UserCommand(ApplicationCommand, type=ApplicationCommandType.user):
    """A shortcut for doing ``class Command(ApplicationCommand, type=ApplicationCommandType.user)``."""
