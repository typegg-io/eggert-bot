import asyncio
import os
from dataclasses import dataclass, field
from typing import Callable

from discord import Embed, ButtonStyle, File
from discord.ext import commands
from discord.ui import View, Button as DiscordButton

from config import BOT_PREFIX
from config import TYPEGG_GUILD_ID, STATS_CHANNEL_ID
from utils import files
from utils.colors import SUCCESS, WARNING
from utils.urls import profile_url

welcome_message = (
    f"### Hi there, I'm Eggert!\n"
    f"Run `{BOT_PREFIX}link` and follow the steps to start using commands.\n"
)


@dataclass
class Field:
    """
    Represents a single field in a Discord embed.

    Attributes:
        title (str): The title of the field.
        content (str): The text content of the field.
        inline (bool): Whether the field should display inline.
    """
    title: str
    content: str
    inline: bool = False


@dataclass
class Page:
    """
    Represents a single page in a Message object.

    Attributes:
        title (str): The title of the page.
        description (str): The description of the page.
        fields (list[Field]): A list of Field objects to display in the embed.
        footer (str): Optional footer text.
        color (int): Optional color for the embed.
        button_name (str): Name used for the page-switching button.
        render (Callable): Function to render an image/file for the page.
        default (bool): Whether this is the default page to show initially.
    """
    title: str = None
    description: str = ""
    fields: list = field(default_factory=list)
    footer: str = None
    color: int = None
    button_name: str = None
    render: Callable = None
    default: bool = False


class Message(View):
    """
    Constructs and sends an interactive, embed-based message with optional pagination.

    Attributes:
        ctx (commands.Context): The command context from which the message is sent.
        page (Page): A Page object for a single-page message. Optional if `pages` is provided.
        pages (list[Page]): A list of Page objects to paginate through.
        content (str): Text content above the embed.
        title (str): Default title for all pages.
        url (str): Optional URL linked to the embed title.
        header (str): Header text placed above the description.
        footer (str): Default footer for all pages.
        footer_icon (str): Default footer icon for all pages (URL), `footer` must also be passed to load the icon.
        color (int): Default color for all pages.
        profile (dict): Optional user profile for author section, pulled from API.
        show_avatar (bool): Whether to show the avatar in the embed.
        thumbnail (str): Optional thumbnail to display in the embed (URL).

    Methods:
        send(): Sends the constructed message with buttons and embeds.
    """

    def __init__(
        self,
        ctx: commands.Context,
        page: Page = None,
        pages: list = None,
        content: str = "",
        title: str = None,
        url: str = None,
        header: str = "",
        footer: str = "",
        footer_icon: str = None,
        color: int = None,
        profile: dict = None,
        show_avatar: bool = True,
        thumbnail: str = None,
    ):
        self.ctx = ctx
        self.pages = pages or []
        if page:
            self.pages.insert(0, page)
        self.page_count = len(self.pages)
        self.page_index = 0

        super().__init__(timeout=60 if self.page_count > 1 else 0.01)
        self.message = None

        self.content = content
        self.title = title
        self.url = url
        self.header = header
        self.footer = footer
        self.footer_icon = footer_icon
        self.color = self.ctx.user["theme"]["embed"] if hasattr(ctx, "user") and color is None else color
        self.profile = profile
        self.show_avatar = show_avatar
        self.thumbnail = thumbnail

        self.embeds = []
        self.cache = {}
        self.paginated = any(not page.button_name for page in self.pages)

        # self.build_embeds()

    def build_embeds(self):
        """Assembles the embed(s) for the message."""
        for i, page in enumerate(self.pages):
            title = page.title if page.title else self.title
            description = self.header + "\n" + page.description
            footer = page.footer if page.footer else self.footer
            if page.default:
                self.page_index = i
            embed = Embed(
                title=title,
                description=description,
                url=self.url,
                color=page.color if page.color else self.color,
            )
            if page.fields:
                for field in page.fields:
                    embed.add_field(name=field.title, value=field.content, inline=field.inline)
            if footer:
                self.update_footer(embed, footer)
            if self.footer_icon:
                embed.set_footer(text=embed.footer.text, icon_url=self.footer_icon)
            if self.profile:
                self.add_profile(embed)
            if self.paginated and self.page_count > 1:
                self.update_footer(embed, f"Page {i + 1} of {self.page_count}")
            if self.thumbnail:
                embed.set_thumbnail(url=self.thumbnail)
            self.embeds.append(embed)

        if self.pages[self.page_index].render:
            self.update_image()
        if self.page_count > 1:
            if self.paginated:
                self.add_navigation_buttons()
                self.update_navigation_buttons()
            else:
                self.add_buttons()

    def add_profile(self, embed):
        """Adds profile avatar and author section to the embed."""
        username = self.profile["username"]
        display_name = self.profile.get("displayName", None) or username
        author_icon = (
            f"https://flagsapi.com/{self.profile["country"].upper()}/flat/64.png"
            if self.profile["country"]
            else ""
        )

        if self.show_avatar:
            embed.set_thumbnail(url=self.profile["avatarUrl"])

        embed.set_author(
            name=display_name,
            url=profile_url(username),
            icon_url=author_icon,
        )

    def update_footer(self, embed, text):
        """Appends footer text to the embed."""
        footer_text = f"{embed.footer.text}\n" if embed.footer.text else ""
        embed.set_footer(text=footer_text + text)

    def update_navigation_buttons(self):
        self.children[0].disabled = self.page_index == 0
        self.children[1].disabled = self.page_index == 0
        self.children[2].disabled = self.page_index == self.page_count - 1
        self.children[3].disabled = self.page_index == self.page_count - 1

    def add_navigation_buttons(self):
        """Adds pagination buttons to the embed."""
        self.first_button = DiscordButton(label="\u25c0\u25c0", style=ButtonStyle.secondary)
        self.previous_button = DiscordButton(label="\u25c0", style=ButtonStyle.primary)
        self.next_button = DiscordButton(label="\u25b6", style=ButtonStyle.primary)
        self.last_button = DiscordButton(label="\u25b6\u25b6", style=ButtonStyle.secondary)

        self.first_button.callback = self.first
        self.previous_button.callback = self.previous
        self.next_button.callback = self.next
        self.last_button.callback = self.last

        self.add_item(self.first_button)
        self.add_item(self.previous_button)
        self.add_item(self.next_button)
        self.add_item(self.last_button)

    async def first(self, interaction):
        if self.page_index > 0:
            self.page_index = 0
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def previous(self, interaction):
        if self.page_index > 0:
            self.page_index -= 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def next(self, interaction):
        if self.page_index < self.page_count - 1:
            self.page_index += 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def last(self, interaction):
        if self.page_index < self.page_count - 1:
            self.page_index = self.page_count - 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    def add_buttons(self):
        """Adds buttons with custom names (non-paginated layout)."""
        for i, page in enumerate(self.pages):
            style = ButtonStyle.primary if i == self.page_index else ButtonStyle.secondary
            button = DiscordButton(label=page.button_name, style=style)
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, index):
        async def callback(interaction):
            if index == self.page_index:
                return await interaction.response.defer()

            self.page_index = index
            if self.pages[self.page_index].render:
                self.update_image()
            self.clear_items()
            self.add_buttons()

            await self.update_embed(interaction)

        return callback

    def update_image(self):
        """Sets an image for the current page if a render() function is present."""
        index = self.page_index
        if index not in self.cache:
            page = self.pages[index]
            file_name = page.render()
            self.cache[index] = file_name

        self.embeds[index].set_image(url=f"attachment://{self.cache[index]}")

    async def update_embed(self, interaction):
        """Updates the embed and buttons for a given page."""
        if self.ctx.author.id != interaction.user.id:
            return await interaction.response.defer()

        kwargs = {
            "embed": self.embeds[self.page_index],
            "view": self,
        }
        if self.pages[self.page_index].render:
            file_name = self.cache[self.page_index]
            file = File(file_name, filename=os.path.basename(file_name))
            kwargs["attachments"] = [file]
        else:
            kwargs["attachments"] = []
        await interaction.response.edit_message(**kwargs)

    async def send(self):
        """Sends the constructed message with buttons and embeds."""
        self.build_embeds()

        kwargs = {
            "embed": self.embeds[self.page_index],
            "view": self,
            "content": self.content,
        }
        if self.pages[self.page_index].render:
            file_name = self.cache[self.page_index]
            file = File(file_name, filename=os.path.basename(file_name))
            kwargs["files"] = [file]
        self.message = await self.ctx.send(**kwargs)

    async def edit(self, page_index: int = None):
        """Edits the current message with updated page data."""
        if page_index is not None:
            self.page_index = page_index

        self.embeds = []
        self.build_embeds()

        kwargs = {
            "embed": self.embeds[self.page_index],
            "view": self,
        }
        if self.pages[self.page_index].render:
            file_name = self.cache[self.page_index]
            file = File(file_name, filename=os.path.basename(file_name))
            kwargs["attachments"] = [file]
        else:
            kwargs["attachments"] = []

        await self.message.edit(**kwargs)

    def start(self):
        """Returns a fire-and-forget message, used for skeleton commands."""

        async def runner():
            await self.send()
            # await self.edit()

        return asyncio.create_task(runner())

    async def on_timeout(self):
        await super().on_timeout()
        if len(self.pages) > 1:
            await self.message.edit(view=None)
        for file in self.cache.values():
            files.remove_file(file)


class Button(View):
    def __init__(self, label: str, callback: Callable, message: str):
        """
        A view with a single button.

        Args:
            label (str): Button text.
            callback (Callable): Function or coroutine to call when pressed.
            message (str): Message to display when the button is pressed.
        """
        super().__init__(timeout=60)
        self.label = label
        self.callback_func = callback
        self.message_text = message
        self.message = None
        self.add_item(self.make_button())

    def make_button(self):
        button = DiscordButton(label=self.label, style=ButtonStyle.primary)

        async def callback(interaction):
            result = self.callback_func(interaction)
            if asyncio.iscoroutine(result):
                result = await result

            if result:
                await interaction.response.send_message(self.message_text, ephemeral=True)

        button.callback = callback
        return button

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                pass


def paginate_data(data: list, formatter: Callable[..., str], page_count: int = 10, per_page: int = 10):
    """
    Splits a list of data into multiple Page objects.

    Args:
        data (list): The data to be formatted into pages.
        formatter (Callable): Function that formats each data item into a string.
        page_count (int): Maximum number of pages.
        per_page (int): Number of items per page.

    Returns:
        list[Page]: A list of Page objects for use in a Message.
    """
    page_count = min(page_count, ((len(data) - 1) // per_page) + 1)
    pages = []
    for i in range(page_count):
        description = ""
        for item in data[i * per_page:(i + 1) * per_page]:
            description += formatter(item)
        pages.append(Page(description=description))

    return pages


def command_milestone(author, milestone):
    return Embed(
        title="Command Milestone! :tada:",
        description=f"<@{author}> just ran the {milestone:,}th command!",
        color=SUCCESS
    )


def privacy_warning():
    return Embed(
        title=":warning: Privacy Warning :warning:",
        description=(
            "Certain commands expose race data that is not normally\n"
            "available to the public (like non-quote best races).\n"
            "Use at your own discretion!"
        ),
        color=WARNING,
    )


def usable_in(*channel_ids):
    """
    Decorator to mark commands as usable in specific channels.

    Usage:
        @usable_in(CHANNEL_ID_1, CHANNEL_ID_2)
        async def mycommand(self, ctx):
            ...
    """

    def decorator(func):
        if not hasattr(func, 'allowed_channels'):
            func.allowed_channels = set()
        func.allowed_channels.update(channel_ids)
        return func

    return decorator


def check_channel_permissions(ctx: commands.Context) -> bool:
    """
    Check if a command can be used in the current channel.

    Rules:
    1. DMs: always allowed
    2. Non-TypeGG servers: always allowed
    3. TypeGG server stats channel: all commands allowed
    4. TypeGG server other channels: only commands decorated with @usable_in for that channel

    Returns:
        bool: True if command is allowed, False otherwise
    """
    # Rule 1: DMs are always allowed
    if ctx.guild is None:
        return True

    # Rule 2: Non-TypeGG servers are always allowed
    if ctx.guild.id != TYPEGG_GUILD_ID:
        return True

    # Rule 3: Stats channel allows all commands
    if ctx.channel.id == STATS_CHANNEL_ID:
        return True

    # Rule 4: Other channels in TypeGG server - check if command is decorated
    command = ctx.command
    if command is None:
        return False

    # Check if the command callback has allowed_channels attribute
    callback = command.callback
    if hasattr(callback, 'allowed_channels'):
        return ctx.channel.id in callback.allowed_channels

    # If not decorated, command is not allowed in this channel
    return False
