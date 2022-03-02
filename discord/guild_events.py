"""
The MIT License (MIT)

Copyright (c) 2022-present z03h

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

from typing import TYPE_CHECKING, Optional, Union
from .iterators import GuildEventUserIterator
from .channel import VoiceChannel, StageChannel
from .errors import InvalidArgument
from .object import Object
from .asset import Asset
import datetime

from . import utils
from .mixins import Hashable
from .user import User
from .enums import (
    GuildEventStatus,
    GuildEventLocationType,
    GuildEventPrivacyLevel,
    try_enum,
)

MISSING = utils.MISSING

__all__ = ('GuildEvent',)

if TYPE_CHECKING:
    from .guild import Guild
    from .abc import Snowflake
    from .iterators import AsyncIterator
    from .types.guild_events import GuildEvent as GuildEventPayload
    from .state import ConnectionState
    from .member import Member


class GuildEvent(Hashable):
    """Represents a Discord Guild Scheduled Event.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: x == y

            Checks if two events are equal.

        .. describe:: x != y

            Checks if two events are not equal.

        .. describe:: hash(x)

            Returns the event's hash.

        .. describe:: str(x)

            Returns the event's name.

    Attributes
    ----------
    name: :class:`str`
        The name of the  event.
    description: Optional[:class:`str`]
        The description of the  event.
    cover_image: Optional[:class:`Asset`]
        The cover image of the event.

        .. versionadded:: 2.0
    start_time: :class:`datetime.datetime`
        The time when the event will start
    end_time: Optional[:class:`datetime.datetime`]
        The time when the event is supposed to end.
    channel_id: Optional[:class:`int`]
        ID of the channel where event is scheduled to take place.
        ``None`` if type is External.
    status: :class:`GuildEventStatus`
        The status of the event.
    location_type: :class:`GuildEventLocationType`
        The type of location for where this event is scheduled to take place.
    external_location: Optional[:class:`str`]
        The external location of this event.
        Will be ``None`` for events of location type ``stage_instance`` or ``voice``.
    creator_id: Optional[:class:`int`]
        The ID of the user who created the event.
    creator: Optional[:class:`User`]
        The user who created the event.

        .. note::

            :attr:`creator` and :attr:`creator_id`Will be  ``None`` for
            events created before October 25th, 2021.

    privacy_level: :class:`GuildEventPrivacyLevel`
        The privacy level of the event.
    user_count: Otional[:class:`int`]
        The number of users interested in this event.

        .. note::

            This will only be available if event is fetch with :meth:`Guild.fetch_event`
            or :meth:`Guild.fetch_events` and ``with_user_count`` set to ``True``.

    guild: :class:`Guild`
        The guild where the event is scheduled.
    """
    __slots__ = (
        '_state',
        'guild',
        'id',
        'name',
        'description',
        'privacy_level',
        'location_type',
        'status',
        'creator_id',
        'creator',
        'start_time',
        'end_time',
        'channel_id',
        'user_count',
        'external_location',
        '_entity_id',
        '_cover_image',
    )

    def __init__(self, *, guild: Guild, data: GuildEventPayload, state: ConnectionState):
        self._state: ConnectionState = state
        self.guild: Guild = guild
        self.id: int = int(data['id'])

        self._update(guild, data, state)

    def _update(self, guild, data, state):
        self.name: str = data['name']
        self.description: Optional[str] = data.get('description')

        self.privacy_level: GuildEventPrivacyLevel = try_enum(GuildEventPrivacyLevel, data['privacy_level'])
        self.location_type: GuildEventLocationType = try_enum(GuildEventLocationType, data['entity_type'])
        self.status: GuildEventStatus = try_enum(GuildEventStatus, data['status'])

        self._entity_id = utils._get_as_snowflake(data, 'entity_id')
        self.creator_id: Optional[int] = utils._get_as_snowflake(data, 'creator_id')
        self.creator: Optional[User] = None
        # safeguard against old events not having creator_id or creator
        if self.creator_id:
            self.creator = state.get_user(self.creator_id)
        if not self.creator:
            creator_data = data.get('creator')
            if creator_data:
                self.creator = User(state=state, data=creator_data)

        self.user_count: Optional[int] = data.get('user_count')

        self.start_time: datetime.datetime = utils.parse_time(data['scheduled_start_time'])
        self.end_time: Optional[datetime.datetime] = utils.parse_time(data['scheduled_end_time'])

        self.channel_id: int = utils._get_as_snowflake(data, 'channel_id')

        self._cover_image: Optional[str] = data.get('image')

        metadata = data.get('entity_metadata')
        self._parse_metadata(metadata)

    def _parse_metadata(self, metadata):
        if not metadata:
            self.external_location: Optional[str] = None
        else:
            self.external_location: Optional[str] = metadata.get('location')

    def __repr__(self):
        return f'<GuildEvent id={self.id} name={self.name} location={self.location} status={self.status} guild={self.guild}>'

    def __str__(self):
        return self.name

    @property
    def location(self) -> Union[VoiceChannel, StageChannel, str]:
        """Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`str`]: The external location or channel of this event"""
        return self.external_location or self.channel

    @property
    def channel(self) -> Optional[Union[VoiceChannel, StageChannel, Object]]:
        """Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`Object`]]: The channel where this event is scheduled to take place.
        Can be ``None`` if location type is external.
        """
        if self.channel_id:
            return self.guild.get_channel(self.channel_id) or Object(id=self.channel_id)
        return None

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the events's creation time in UTC."""
        return utils.snowflake_time(self.id)

    @property
    def duration(self) -> Optional[datetime.timedelta]:
        """Optional[:class:`datetime.timedelta`]: How long the event will last.
        Can be ``None`` if missing :attr:`GuildEvent.end_time`
        """
        if not self.start_time or not self.end_time:
            return None
        return self.end_time - self.start_time

    @property
    def url(self) -> str:
        """:class:`str`: The url for this event."""
        return f'https://discord.com/events/{self.guild.id}/{self.id}'

    @property
    def cover_image(self) -> Optional[Asset]:
        """Optional[Asset}: The cover image for this event."""
        if self._cover_image is None:
            return None
        return Asset._from_guild_event_image(self._state, self.id, self._cover_image)

    async def edit(
        self,
        *,
        name: str = MISSING,
        description: str = MISSING,
        status: GuildEventStatus = MISSING,
        location: Union[StageChannel, VoiceChannel, str] = MISSING,
        start_time: datetime.datetime = MISSING,
        end_time: Optional[datetime.datetime] = MISSING,
        privacy_level: GuildEventPrivacyLevel = MISSING,
        cover_image: Optional[bytes] = MISSING,
        reason: Optional[str] = None
    ):
        """|coro|

        Edits the event.

        All parameters are optional unless ``location.type`` is
        :attr:`GuildEventLocationType.external`, then ``end_time``
        is required.

        Will return a new :class:`.GuildEvent` object if applicable.

        Parameters
        -----------
        name: :class:`str`
            The new name of the event.
        description: :class:`str`
            The new description of the event.
        location: Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`str`]
            The location of the event.
        status: :class:`GuildEventStatus`
            The status of the event.
        start_time: :class:`datetime.datetime`
            The new starting time for the event.
        end_time: Optional[:class:`datetime.datetime`]
            The new ending time of the event.

            Pass ``None`` to remove end time.
        privacy_level: :class:`GuildEventPrivacyLevel`
            The privacy level of the event.
        cover_image: Optional[:class:`bytes`]
            The new image of the event. Pass None to remove.
        reason: Optional[:class:`str`]
            The reason to show in the audit log.

        Raises
        -------
        InvalidArgument
            Event location type is external and doesn't have an end time set.
        Forbidden
            You do not have the Manage Events permission.
        HTTPException
            The operation failed.

        Returns
        --------
        :class:`.GuildEvent`
            The updated event.
        """
        payload = {}

        if name is not MISSING:
            payload["name"] = name

        if description is not MISSING:
            payload["description"] = description

        if status is not MISSING:
            payload["status"] = int(status)

        if privacy_level is not MISSING:
            payload["privacy_level"] = int(privacy_level)

        if location is not MISSING:
            if isinstance(location, str):
                # external
                payload['entity_metadata'] = {'location': location}
                payload['channel_id'] = None
                payload['entity_type'] = GuildEventLocationType.external.value
            else:
                payload['entity_metadata'] = None
                try:
                    payload['channel_id'] = location.id
                except AttributeError:
                    raise TypeError('location must be a VoiceChannel, StageChannel, or str.')

                if isinstance(location, VoiceChannel):
                    payload['entity_type'] = GuildEventLocationType.voice.value
                elif isinstance(location, StageChannel):
                    payload['entity_type'] = GuildEventLocationType.stage_instance.value
                else:
                    raise TypeError('location must be a VoiceChannel, StageChannel, or str.')

        if start_time is not MISSING:
            payload['scheduled_start_time'] = start_time.isoformat()
        if end_time is not MISSING:
            payload['scheduled_end_time'] = end_time.isoformat() if end_time is not None else end_time

        if cover_image is not MISSING:
            payload['image'] = utils._bytes_to_base64_data(cover_image) if cover_image is not None else cover_image

        if payload:
            data = await self._state.http.edit_guild_event(self.guild.id, self.id, reason=reason, **payload)
            return GuildEvent(data=data, guild=self.guild, state=self._state)

        return self

    async def delete(self, *, reason: Optional[str] = None):
        """|coro|

        Cancels and deletes this event.

        Parameters
        -----------
        reason: Optional[str]
            The reason for deletion.

        Raises
        -------
        Forbidden
            You do not have the Manage Events permission.
        HTTPException
            The operation failed.

        """
        await self._state.http.delete_guild_event(self.guild.id, self.id, reason=reason)

    def users(
        self,
        *,
        limit: Optional[int] = None,
        with_member: bool = False,
        before: Optional[Union[Snowflake, datetime.datetime]] = None,
        after: Optional[Union[Snowflake, datetime.datetime]] = None,
    ) -> AsyncIterator:
        """Returns an :class:`AsyncIterator` representing the users or members
        subscribed to the event.

        If ``before`` is provided, users are returned in descending order by their ID.
        otherwise users are returning in ascending order by their ID.

        Examples
        ---------
        Usage ::

            async for user in event.users(limit=100):
                print(user.name)

        Flattening all members into a list: ::

            members = await event.users(limit=None, with_member=True).flatten()

        Parameters
        -----------
        limit: Optional[:class:`int`]
            The maximum number of results to return.
        with_member: Optional[:class:`bool`]
            Whether to fetch :class:`Member` objects instead of :class:`User` objects.
        before: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
            Retrieves users before this date or object. If a datetime is provided,
            it is recommended to use a UTC aware datetime. If the datetime is naive,
            it is assumed to be local time.
        after: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
            Retrieves users after this date or object. If a datetime is provided,
            it is recommended to use a UTC aware datetime. If the datetime is naive,
            it is assumed to be local time.

        Raises
        -------
        ~discord.HTTPException
            Fetching the subscribed users failed.

        Yields
        -------
        Union[:class:`User`, :class:`Member`]
            The subscribed user or member.
        """

        return GuildEventUserIterator(event=self, limit=limit, with_member=with_member, before=before, after=after)
