"""The keyboard layouts the keystroke heatmap can draw."""

from dataclasses import dataclass


@dataclass
class K:
    """One key on a rendered keyboard."""

    matches: str
    width: float = 1
    text: str | None = None
    fontsize: int = 12

    def __post_init__(self) -> None:
        """Derive the key's label from the characters it matches."""
        if self.text is None:
            if len(self.matches) >= 2 and self.matches.isalpha() and self.matches[0].upper() == self.matches[1]:
                self.text = self.matches[1]
            else:
                self.text = " ".join(self.matches)


keymaps = {
    "qwerty": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("qQ"), K("wW"), K("eE"), K("rR"), K("tT"), K("yY"), K("uU"), K("iI"), K("oO"), K("pP"), K("[{"), K("]}"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("sS"), K("dD"), K("fF"), K("gG"), K("hH"), K("jJ"), K("kK"), K("lL"), K(";:"), K("'\""), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("zZ"), K("xX"), K("cC"), K("vV"), K("bB"), K("nN"), K("mM"), K(",<"), K(".>"), K("/?"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "dvorak": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("[{"), K("]}"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("'\""), K(",<"), K(".>"), K("pP"), K("yY"), K("fF"), K("gG"), K("cC"), K("rR"), K("lL"), K("?/"), K("=+"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("oO"), K("eE"), K("uU"), K("iI"), K("dD"), K("hH"), K("tT"), K("nN"), K("sS"), K("-_"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K(";:"), K("qQ"), K("jJ"), K("kK"), K("xX"), K("bB"), K("mM"), K("wW"), K("vV"), K("zZ"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "colemak": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("qQ"), K("wW"), K("fF"), K("pP"), K("gG"), K("jJ"), K("lL"), K("uU"), K("yY"), K(";:"), K("[{"), K("]}"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("rR"), K("sS"), K("tT"), K("dD"), K("hH"), K("nN"), K("eE"), K("iI"), K("oO"), K("'\""), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("zZ"), K("xX"), K("cC"), K("vV"), K("bB"), K("kK"), K("mM"), K(",<"), K(".>"), K("/?"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "gallium": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("bB"), K("lL"), K("dD"), K("cC"), K("vV"), K("jJ"), K("fF"), K("oO"), K("uU"), K(",<"), K("[{"), K("]}"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("nN"), K("rR"), K("tT"), K("sS"), K("gG"), K("yY"), K("hH"), K("aA"), K("eE"), K("iI"), K("/?"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("xX"), K("qQ"), K("mM"), K("wW"), K("zZ"), K("kK"), K("pP"), K("'\""), K(";:"), K(".>"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "semimak": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("fF"), K("lL"), K("hH"), K("vV"), K("zZ"), K("'\""), K("wW"), K("uU"), K("oO"), K("yY"), K("[{"), K("]}"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("sS"), K("rR"), K("nN"), K("tT"), K("kK"), K("cC"), K("dD"), K("eE"), K("aA"), K("iI"), K(";:"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("xX"), K("jJ"), K("bB"), K("mM"), K("qQ"), K("pP"), K("gG"), K(",<"), K(".>"), K("/?"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "canary": [
        [K("`~"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("wW"), K("lL"), K("yY"), K("pP"), K("bB"), K("zZ"), K("fF"), K("oO"), K("uU"), K("'\""), K("[{"), K("]}"), K("\\|", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("cC"), K("rR"), K("sS"), K("tT"), K("gG"), K("mM"), K("nN"), K("eE"), K("iI"), K("aA"), K(";:"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("qQ"), K("jJ"), K("vV"), K("dD"), K("kK"), K("xX"), K("hH"), K("/?"), K(",<"), K(".>"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "azerty": [
        [K("²"), K("&1"), K("é2"), K("\"3"), K("'4"), K("(5"), K("-6"), K("è7"), K("_8"), K("ç9"), K("à0"), K(")°"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("aA"), K("zZ"), K("eE"), K("rR"), K("tT"), K("yY"), K("uU"), K("iI"), K("oO"), K("pP"), K("^¨"), K("$£"), K("*µ", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("qQ"), K("sS"), K("dD"), K("fF"), K("gG"), K("hH"), K("jJ"), K("kK"), K("lL"), K("mM"), K("ù%"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("wW"), K("xX"), K("cC"), K("vV"), K("bB"), K("nN"), K(",?"), K(";."), K(":/"), K("!§"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],

    "qwertz": [
        [K("^°"), K("1!"), K("2\""), K("3§"), K("4$"), K("5%"), K("6&"), K("7/"), K("8("), K("9)"), K("0="), K("ß?"), K("´`"), K("", text="Backspace", width=2, fontsize=10)],
        [K("", width=1.5, text="Tab"), K("qQ"), K("wW"), K("eE"), K("rR"), K("tT"), K("zZ"), K("uU"), K("iI"), K("oO"), K("pP"), K("üÜ"), K("+*"), K("#'", width=1.5)],
        [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("sS"), K("dD"), K("fF"), K("gG"), K("hH"), K("jJ"), K("kK"), K("lL"), K("öÖ"), K("äÄ"), K("\n", width=2.25, text="Enter")],
        [K("", width=2, text="Shift"), K("yY"), K("xX"), K("cC"), K("vV"), K("bB"), K("nN"), K("mM"), K(",;"), K(".:"), K("-_"), K("", width=3, text="Shift")],
        [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
    ],
}


def get_keymap(keymap: str | None = None) -> tuple[list[list[K]], str]:
    """Return a layout and its name, falling back to qwerty."""
    if keymap is None:
        return keymaps["qwerty"], "qwerty"

    keymap = keymap.lower()
    if keymap in keymaps:
        return keymaps[keymap], keymap

    # A profile layout carries a free-text variant, so "Colemak-DH" has to find Colemak.
    for name in keymaps:
        if keymap.startswith(name):
            return keymaps[name], name

    return keymaps["qwerty"], "qwerty"
