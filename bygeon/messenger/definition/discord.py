from typing import Union, List, Optional, TypedDict
from typing_extensions import NotRequired


class Endpoints:
    GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"
    SEND_MESSAGE = "https://discordapp.com/api/channels/{}/messages"
    DELETE_MESSAGE = "https://discordapp.com/api/channels/{}/messages/{}"
    EDIT_MESSAGE = "https://discordapp.com/api/channels/{}/messages/{}"
    GET_EMOJI = "https://cdn.discordapp.com/emojis/{}"
    GET_CHANNEL = "https://discordapp.com/api/channels/{}"
    LIST_GUILD_MEMBERS = "https://discordapp.com/api/guilds/{}/members"


class ReferencedMessage(TypedDict):
    type: int
    id: str


class Author(TypedDict):
    id: str
    username: str
    avatar: str
    bot: bool


class EmbedAuthor(TypedDict):
    name: str
    url: str
    icon_url: str
    proxy_icon_url: str


class GatewayEvent(TypedDict):
    type: int
    referenced_message: ReferencedMessage
    channel_id: str
    content: str
    author: Author
    heartbeat_interval: int


class UnavailableGuild(TypedDict):
    id: str
    unavailable: bool


class User(TypedDict):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str]
    bot: NotRequired[bool]
    system: NotRequired[bool]
    mfa_enabled: NotRequired[bool]
    banner: NotRequired[Optional[str]]
    accent_color: NotRequired[Optional[int]]
    locale: NotRequired[str]
    verified: NotRequired[bool]
    email: NotRequired[Optional[str]]
    flags: NotRequired[int]
    premium_type: NotRequired[int]
    public_flags: NotRequired[int]


class Role(TypedDict):
    pass


class GuildMember(TypedDict):
    user: User
    nick: NotRequired[Optional[str]]
    avatar: Optional[str]
    roles: List[str]
    joined_at: str
    premium_since: str
    deaf: bool
    mute: bool
    pending: NotRequired[bool]
    permissions: NotRequired[str]
    communication_disabled_until: str

    pass


class Attachment(TypedDict):
    id: str
    filename: str
    description: NotRequired[str]
    content_type: NotRequired[str]
    # size	integer	size of file in bytes
    size: int
    url: str
    proxy_url: str
    height: NotRequired[Optional[int]]
    width: NotRequired[Optional[int]]
    ephemeral: NotRequired[bool]


class Embed(TypedDict):
    pass


class Reaction(TypedDict):
    pass


class MessageReference(TypedDict):
    pass


class Channel(TypedDict):
    pass


class StickerItem(TypedDict):
    id: str
    name: str
    # 1: png, 2: apng, 3: lottie
    format_type: int


class DiscordMessage(TypedDict):
    id: str
    channel_id: str
    author: User
    content: str
    timestamp: str
    edited_timestamp: Optional[str]
    tts: bool
    mention_everyone: bool
    mentions: List[User]
    mention_roles: List[Role]
    # mention_channels?**	array of channel mention objects	channels specifically mentioned in this message
    attachments: List[Attachment]
    embeds: List[Embed]
    reactions: Optional[List[Reaction]]
    nonce: NotRequired[Union[int, str]]
    pinned: bool
    webhook_id: NotRequired[str]
    type: int
    # activity?	message activity object	sent with Rich Presence-related chat embeds
    # application?	partial application object	sent with Rich Presence-related chat embeds
    # application_id?	snowflake	if the message is an Interaction or application-owned webhook, this is the id of the application
    message_reference: NotRequired[MessageReference]
    flags: NotRequired[int]

    # recursive TypedDict not supported yet
    referenced_message: NotRequired[Optional[dict]]
    thread: NotRequired[Channel]

    # components?	Array of message components	sent if the message contains components like buttons, action rows, or other interactive components
    sticker_items: Optional[List[StickerItem]]


class MessageCreateEvent(DiscordMessage):
    guild_id: NotRequired[str]
    # mentions: List[User]


class MessageDeleteEvent(TypedDict):
    id: str
    channel_id: str
    guild_id: NotRequired[str]


class MessageUpdateEvent(MessageCreateEvent):
    ...


class Hello(TypedDict):
    heartbeat_interval: int


class Application(TypedDict):
    id: str
    flags: NotRequired[int]


class ReadyEvent(TypedDict):
    v: int
    user: User
    guilds: List[UnavailableGuild]
    session_id: str
    shard: Optional[List[int]]
    application: Application


class WebsocketMessage(TypedDict):
    op: int
    t: str
    s: int
    d: Union[MessageCreateEvent, ReadyEvent, Hello, MessageDeleteEvent]


class Opcode:
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE_UPDATE = 3
    RESUME = 6
    RECONNECT = 7
    HELLO = 10
    HEARTBEAT_ACK = 11


class EventName:
    MESSAGE_CREATE = "MESSAGE_CREATE"
    MESSAGE_UPDATE = "MESSAGE_UPDATE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    READY = "READY"
