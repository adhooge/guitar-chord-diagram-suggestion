from typing import List
import matplotlib.pyplot as plt
import matplotlib as mpl
from math import floor

class Diagram():

    def __init__(self, num_strings: int = 6, num_frets: int = 4,
            root_fret: int = 1, diagram: str = '', ax: plt.Axes | None = None,
            fig: mpl.figure.Figure | None = None, fig_width: int = 4,
            nut_linewidth: int = 2, linewidth: int = 1, linecolor: str = 'k',
            marker_size: int = 80, interactive: bool = False, show_title: bool = False,
            textbox: mpl.widgets.TextBox | None = None) -> None:
        self.num_strings = num_strings
        self.num_frets = num_frets
        self.root_fret = root_fret
        self.diagram: List[str]
        self.textbox = textbox
        if diagram == '':
            self._init_diagram()
        elif textbox is not None:
            self.diagram = self.textbox.text.split('.')
        else:
            self.diagram = diagram.split('.')
            self.root_fret = self._get_root_fret()
        self.fig_width = fig_width
        self.nut_linewidth = nut_linewidth
        self.linewidth = linewidth
        self.linecolor = linecolor
        self.marker_size = marker_size
        self.show_title = show_title
        if ax is None or fig is None:
            self._init_fig_ax()
        else:
            self.ax = ax
            self.fig = fig
        self._prepare_axes()
        self.interactive = interactive
        if self.interactive:
            self.click_connection = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
            self.scroll_connection = self.fig.canvas.mpl_connect('scroll_event', self.onscroll)

    def _get_root_fret(self) -> int:
        size_threshold = self.num_frets
        min_fret = 999
        max_fret = 0
        for f in self.diagram:
            if f == 'x':
                continue
            v = int(f)
            if v > max_fret:
                max_fret = v
            if v < min_fret and v != 0:
                min_fret = v
        if max_fret < self.num_frets and (max_fret - min_fret) < size_threshold:
            return 1
        else:
            return min_fret

    def onclick(self, event: mpl.backend_bases.MouseEvent) -> None:
        if event.inaxes != self.ax:
            return
        string = round(event.xdata)
        if event.ydata > self.num_frets:
            self.__change_open_mute(string)
        else:
            fret = floor(self.num_frets - event.ydata)
            self.__update_dot(string, fret)
        self.update()

    def onscroll(self, event: mpl.backend_bases.MouseEvent) -> None:
        if event.button == 'down':
            # increase root fret
            step = 1
        else:
            step = -1
            if self.root_fret == 1:
                # the diagram cannot go further up!
                return
        self.root_fret += step
        self._shift_diagram(step)
        self._check_root_fret()
        self.update()

    def _check_root_fret(self) -> None:
        self.root_fret_txt.set_text(str(self.root_fret))
        if self.root_fret == 1:
            self.root_fret_txt.set_alpha(0)
        else:
            self.root_fret_txt.set_alpha(1)

    def _shift_diagram(self, step: int) -> None:
        for s, f in enumerate(self.diagram):
            if f not in ['x', '0']:
                tmp = int(f)
                val = str(tmp + step)
                self.diagram[s] = val

    def __change_open_mute(self, string: int) -> None:
        if self.diagram[string] == 'x':
            # switch from x to 0
            self.muted_strings[string].set_alpha(0)
            self.open_strings[string].set_alpha(1)
            self.diagram[string] = '0'
        elif self.diagram[string] == '0':
            # switch from 0 to x
            self.muted_strings[string].set_alpha(1)
            self.open_strings[string].set_alpha(0)
            self.diagram[string] = 'x'
        else:
            # start with mute and remove all dots on string
            self.muted_strings[string].set_alpha(1)
            for dot in self.dots[string]:
                dot.set_alpha(0)
            self.diagram[string] = 'x'

    def update(self) -> None:
        if self.textbox is not None:
            self.textbox.set_val(self.diagram_str)
        if self.show_title:
            self.ax.set_title(self.diagram_str)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _init_diagram(self) -> None:
        diag = ''
        for s in range(self.num_strings):
            diag += 'x.'
        diag = diag[:-1]
        self.diagram = diag.split('.')

    def _init_fig_ax(self) -> None:
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_width*1.5))
        self.fig = fig
        self.ax = ax

    def _prepare_axes(self) -> None:
        self.ax.clear()
        self.ax.axis('off')
        # nut
        self.nut = self.ax.hlines(self.num_frets, 0, self.num_strings-1, linewidth=self.nut_linewidth,
                color=self.linecolor)
        # root fret
        self.root_fret_txt = self.ax.text(-0.5, self.num_frets - 0.5, str(self.root_fret))
        if self.root_fret == 1:
            self.root_fret_txt.set_alpha(0)
        # frets
        self.frets = self.ax.hlines(range(self.num_frets), 0, self.num_strings-1,
                color=self.linecolor)
        # strings
        self.strings = self.ax.vlines(range(self.num_strings), 0, self.num_frets,
                color=self.linecolor)
        # Prepare dots
        ## Muted strings
        self.muted_strings = []
        for s in range(self.num_strings):
            x = self.ax.scatter(s, self.num_frets+.5, s=self.marker_size,
                    marker='x', color=self.linecolor, alpha=0)
            self.muted_strings.append(x)
        ## Open strings
        self.open_strings = []
        for s in range(self.num_strings):
            x = self.ax.scatter(s, self.num_frets+.5, s=self.marker_size,
                    marker='o', color=self.linecolor, facecolors='none', alpha=0)
            self.open_strings.append(x)
        ## Dots
        self.dots = []
        for s in range(self.num_strings):
            self.dots.append([])
            for f in range(self.num_frets):
                plot_fret = self.num_frets + 0.5 - f - 1
                d = self.ax.scatter(s, plot_fret, s=self.marker_size,
                                    color=self.linecolor, alpha=0)
                self.dots[s].append(d)
        # title
        if self.show_title:
            self.ax.set_title(self.diagram_str)

    @property
    def diagram_str(self):
        return '.'.join(self.diagram)

    def show_diagram(self) -> None:
        for string, fret in enumerate(self.diagram):
            match fret:
                case 'x':
                    self.__mute(string)
                case '0':
                    self.__open(string)
                case _:
                    self.__update_dot(string, int(fret) - self.root_fret)

    def __mute(self, string: int) -> None:
        # turn off all dots on string
        for dot in self.dots[string]:
            dot.set_alpha(0)
        self.muted_strings[string].set_alpha(1)
        self.open_strings[string].set_alpha(0)

    def __open(self, string: int) -> None:
        # turn off all dots on string
        for dot in self.dots[string]:
            dot.set_alpha(0)
        self.muted_strings[string].set_alpha(0)
        self.open_strings[string].set_alpha(1)

    def __update_dot(self, string: int, fret: int) -> None:
        # turn off muted and open strings
        self.muted_strings[string].set_alpha(0)
        self.open_strings[string].set_alpha(0)
        # turn off all dots on string
        for dot in self.dots[string]:
            dot.set_alpha(0)
        # turn on the correct dot
        self.dots[string][fret].set_alpha(1)
        #update diagram
        self.diagram[string] = str(self.root_fret + fret)

    def set_diagram(self, diagram: str) -> None:
        self.diagram = diagram.split('.')
        self.root_fret = self._get_root_fret()
        self._check_root_fret()
        self.show_diagram()
        self.update()
