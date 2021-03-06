# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from PIL import Image
from rgbmatrix import graphics
from rgbmatrix.core import FrameCanvas

from dm_drawstuff import drawppm_bottomleft
from dm_depdata import Meldung


class MultisymbolScrollline:
    @dataclass
    class __Element:
        text: str
        symbol: Image.Image
        initial_pretext: int
        initial_posttext: int
        letters_passed: int = field(init=False, default=0)
        curr_textxoffset: int = field(init=False, default=0)
        pretext: int = field(init=False)
        posttext: int = field(init=False)

        def __post_init__(self):
            self.pretext = self.initial_pretext
            self.posttext = self.initial_posttext

        def reset(self):
            self.pretext = self.initial_pretext
            self.posttext = self.initial_posttext
            self.letters_passed = 0
            self.curr_textxoffset = 0

    def __init__(self, lx, rx, symoffset, font, textcolor, symdict, bgcolor_t=None, initial_pretext=2, initial_posttext=5, pretext_zero_if_no_symbol=True, add_end_spacer=True):
        # attributes
        self.lx = lx
        self.rx = rx
        self.symoffset = symoffset
        self.font = font
        self.textcolor = textcolor
        self.symdict = symdict
        self.bgcolor = graphics.Color(*bgcolor_t) if bgcolor_t else graphics.Color()
        self.initial_posttext = initial_posttext
        self.initial_pretext = initial_pretext
        self.pretext_zero_if_no_symbol = pretext_zero_if_no_symbol
        self.add_end_spacer = add_end_spacer
        # self.staticleftsymtextspacing = staticleftsymtextspacing
        # self.forcescroll = forcescroll
        # self.noscroll = noscroll

        # state
        self.meldungs: List[Meldung] = []
        self.elements: List[MultisymbolScrollline.__Element] = []
        self.currfirstelemi = None
        self.currlastelemi = None
        self.shownelems = 0
        self.startpos = rx

    def update(self, meldungs: List[Meldung]) -> None:
        if meldungs == self.meldungs:
            return
        ...  # todo: schlaue anpassung je nach davor angezeigter meldung; dabei alle anderen zeilen hier anpassen
        self.meldungs = meldungs
        self.elements = []
        self.currfirstelemi = None
        self.currlastelemi = None
        self.shownelems = 0
        self.startpos = self.rx
        for meldung in meldungs:
            _symbol = self.symdict and self.symdict.get(meldung.symbol) or None
            self.elements.append(self.__class__.__Element(text=''.join(_char for _char in meldung.text if characterwidth(self.font, ord(_char))),
                                                          symbol=_symbol,
                                                          initial_pretext=self.initial_pretext if (_symbol is not None or not self.pretext_zero_if_no_symbol) else 0,
                                                          initial_posttext=self.initial_posttext))
        if self.elements:
            if self.elements[0].symbol is not None:
                self.startpos -= (self.elements[0].symbol.size[0] - 1)
            if self.add_end_spacer:
                self.elements[-1].initial_posttext = 0
                self.elements[-1].posttext = 0
                self.elements.append(self.__class__.__Element(text='', symbol=None, initial_pretext=0, initial_posttext=self.startpos-self.lx))

    def render(self, canvas: FrameCanvas, texty: int) -> None:
        if not self.elements:
            return
        currx = self.startpos
        if self.currfirstelemi is None:
            self.currfirstelemi = 0
        elemi = self.currfirstelemi
        self.shownelems = 0
        while currx <= self.rx:
            elem = self.elements[elemi]
            isleftelem = currx == self.lx
            if currx + (elem.symbol is not None and (elem.symbol.size[0] - 1)) <= self.rx:
                self.shownelems += 1
                self.currlastelemi = elemi
                if elem.symbol is not None: currx = drawppm_bottomleft(canvas, elem.symbol, currx, texty+self.symoffset, transp=True)
                if isleftelem:
                    currx += elem.pretext
                    text_max = propscroll(self.font, elem.text[elem.letters_passed:], currx+elem.curr_textxoffset, self.rx)
                else:
                    currx += elem.initial_pretext
                    text_max = propscroll(self.font, elem.text, currx, self.rx)
                if text_max or (not elem.text) or (isleftelem and elem.letters_passed == len(elem.text)):
                    if isleftelem:
                        currx += elem.curr_textxoffset
                    if text_max:
                        if isleftelem:
                            currx += graphics.DrawText(canvas, self.font, currx, texty, self.textcolor, elem.text[elem.letters_passed:elem.letters_passed+text_max]) - 1
                            if not elem.pretext:
                                elem.curr_textxoffset -= 1
                            if elem.curr_textxoffset < 0:
                                elem.curr_textxoffset = characterwidth(self.font, ord(elem.text[elem.letters_passed])) - 1
                                elem.letters_passed += 1
                        else:
                            currx += graphics.DrawText(canvas, self.font, currx, texty, self.textcolor, elem.text[:text_max]) - 1
                    else:  # if ((not elem.text) or (isleftelem and elem.letters_passed = len(elem.text))):
                        if isleftelem and elem.posttext < 0 and elem.symbol is not None:
                            _thissize = elem.symbol.size[0]
                            for _y in range(texty+self.symoffset-elem.symbol.size[1], texty+self.symoffset+1):
                                graphics.DrawLine(canvas, self.lx+_thissize+elem.posttext, _y, self.lx+_thissize-1, _y, self.bgcolor)
                    if isleftelem:
                        currx += elem.posttext
                        if elem.letters_passed == len(elem.text):
                            if elem.curr_textxoffset:
                                elem.curr_textxoffset -= 1
                            elif not elem.pretext:
                                elem.posttext -= 1
                        if elem.pretext: elem.pretext -= 1
                        if elem.posttext <= ((elem.symbol is not None and -elem.symbol.size[0]) or 0):
                            elem.reset()
                            self.currfirstelemi = (self.currfirstelemi + 1) % len(self.elements)
                            self.shownelems -= 1
                    else:
                        currx += elem.initial_posttext
                    elemi = (elemi + 1) % len(self.elements)
                else: break
            else: break
        if self.startpos > self.lx: self.startpos -= 1


class SimpleScrollline:
    def __init__(self, lx, rx, symoffset, font, textcolor, symtextspacing=1, forcescroll=False, noscroll=False):
        self.lx = lx
        self.rx = rx
        self.symoffset = symoffset
        self.font = font
        self.textcolor = textcolor
        self.symtextspacing = symtextspacing
        self.forcescroll = forcescroll
        self.noscroll = noscroll

        self.currx = rx
        self.letters_passed = 0
        self.symbol = None
        self.text = ""
        self.textlen = 0
        self.base_start = lx
        self.base_start_static = lx
        self.text_max_theoretical = 0
        self.willscroll = forcescroll

    def update(self, symbol: Optional[Image.Image], text: str) -> None:
        if symbol == self.symbol and text == self.text:
            return
        self.symbol = symbol
        self.text = ''.join(_char for _char in text if characterwidth(self.font, ord(_char)))
        self.textlen = len(self.text)
        self.base_start = self.lx + (self.symbol is not None and self.symbol.size[0])
        self.base_start_static = self.base_start + (self.symbol is not None and self.symtextspacing)
        self.text_max_theoretical = propscroll(self.font, self.text, self.base_start_static, self.rx)
        self.willscroll = (not self.noscroll) and (self.forcescroll or self.textlen > self.text_max_theoretical)

    def render(self, canvas: FrameCanvas, texty: int) -> None:
        if self.symbol: drawppm_bottomleft(canvas, self.symbol, self.lx, texty+self.symoffset, transp=True)
        if not self.text: return
        if self.willscroll:
            if self.letters_passed >= self.textlen:
                self.letters_passed = 0
                self.currx = self.rx
            text_max = propscroll(self.font, self.text[self.letters_passed:], self.currx, self.rx)
            scrolllen = graphics.DrawText(canvas, self.font, self.currx, texty, self.textcolor, self.text[self.letters_passed:self.letters_passed+text_max])
            self.currx -= 1
            if self.currx < self.base_start:
                self.currx = self.base_start + characterwidth(self.font, ord(self.text[self.letters_passed])) - 1
                self.letters_passed += 1
        else: graphics.DrawText(canvas, self.font, self.base_start_static, texty, self.textcolor, self.text[:self.text_max_theoretical])


# beides ohne extra_spacing
@lru_cache(maxsize=4096)
def propscroll(font: graphics.Font, text: str, start: int, end: int) -> int:
    c = 0
    cpx = 0
    pixel = end - start + 1 + 1  # + 1 wegen space am ende jedes zeichens, was am ende egal ist
    while c < len(text):
        _cpx = cpx + characterwidth(font, ord(text[c]))
        if _cpx > pixel:
            break
        c += 1
        cpx = _cpx
    return c


@lru_cache(maxsize=64)
def textpx(font: graphics.Font, text: str) -> int:
    return sum(characterwidth(font, ord(c)) for c in text) - 1


@lru_cache(maxsize=None)
def characterwidth(font: graphics.Font, cp: int) -> int:
    _cw = font.CharacterWidth(cp)
    if _cw == -1:
        _cw = font.CharacterWidth(65533)
        if _cw == -1:
            _cw = 0
    return _cw
