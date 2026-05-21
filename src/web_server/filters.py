import re

from markupsafe import Markup, escape

_GG_PLUS_EMOJI = "<:GG1:1445664315871985807><:GG2:1445664341742452798>"
_GG_PLUS_LINKED = re.compile(r'\[' + re.escape(_GG_PLUS_EMOJI) + r'\]\(([^)]+)\)')
_GG_PLUS_PLACEHOLDER = "\x00GG:{}\x00"


def _gg_badge(url: str) -> str:
    return f'<a href="{url}" class="plus-badge" target="_blank">GG+</a>'


def discord_md(text: str) -> Markup:
    text = _GG_PLUS_LINKED.sub(lambda m: _GG_PLUS_PLACEHOLDER.format(m.group(1)), text)
    text = text.replace(_GG_PLUS_EMOJI, _GG_PLUS_PLACEHOLDER.format("https://typegg.io/plus"))
    text = re.sub(r'\\(.)', r'\1', text)
    text = str(escape(text))
    text = re.sub(r'\x00GG:([^\x00]+)\x00', lambda m: _gg_badge(m.group(1)), text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return Markup(text)


FILTERS = {
    "discord_md": discord_md,
}
