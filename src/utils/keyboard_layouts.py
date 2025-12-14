from dataclasses import dataclass
from typing import List


@dataclass
class K:
    matches: str
    width: float = 1
    text: str | None = None
    fontsize: int = 12

    def __post_init__(self):
        if self.text is None:
            if len(self.matches) >= 2 and self.matches.isalpha() and self.matches[0].upper() == self.matches[1]:
                self.text = self.matches[1]
            else:
                self.text = " ".join(self.matches)


def get_keymap(keymap: str = None) -> (List[List[K]], str):
    if keymap is None:
        keymap = "qwerty"

    keymaps = {
        "qwerty": [
            [K("~`"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("-_"), K("=+"), K("", text="Backspace", width=2, fontsize=10)],
            [K("", width=1.5, text="Tab"), K("qQ"), K("wW"), K("eE"), K("rR"), K("tT"), K("yY"), K("uU"), K("iI"), K("oO"), K("pP"), K("[{"), K("]}"), K("\\|", width=1.5)],
            [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("sS"), K("dD"), K("fF"), K("gG"), K("hH"), K("jJ"), K("kK"), K("lL"), K(";:"), K("'\""), K("\n", width=2.25, text="Enter")],
            [K("", width=2, text="Shift"), K("zZ"), K("xX"), K("cC"), K("vV"), K("bB"), K("nN"), K("mM"), K(",<"), K(".>"), K("/?"), K("", width=3, text="Shift")],
            [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
        ],

        "dvorak": [
            [K("~`"), K("1!"), K("2@"), K("3#"), K("4$"), K("5%"), K("6^"), K("7&"), K("8*"), K("9("), K("0)"), K("[{"), K("]}"), K("", text="Backspace", width=2, fontsize=10)],
            [K("", width=1.5, text="Tab"), K("'\""), K(",<"), K(".>"), K("pP"), K("yY"), K("fF"), K("gG"), K("cC"), K("rR"), K("lL"), K("?/"), K("=+"), K("\\|", width=1.5)],
            [K("", width=1.75, text="Caps Lock", fontsize=10), K("aA"), K("oO"), K("eE"), K("uU"), K("iI"), K("dD"), K("hH"), K("tT"), K("nN"), K("sS"), K("-_"), K("\n", width=2.25, text="Enter")],
            [K("", width=2, text="Shift"), K(";:"), K("qQ"), K("jJ"), K("kK"), K("xX"), K("bB"), K("mM"), K("wW"), K("vV"), K("zZ"), K("", width=3, text="Shift")],
            [K("", width=1.25, text="Ctrl"), K("", width=1.25, text="Super"), K("", width=1.25, text="Alt"), K(" ", width=6.25, text="Space"), K("", width=1.25, text="Alt"), K("", width=1.25, text="Super"), K("", width=1.25, text="Menu"), K("", width=1.25, text="Ctrl")]
        ]
    }

    if keymap in keymaps:
        return keymaps[keymap], keymap

    return keymaps["qwerty"], "qwerty"
