# https://github.com/jquast/blessed
# https://blessed.readthedocs.io/en/latest/
from blessed import Terminal


class UiTools(Terminal):

    def __init__(self, width, height):
        super().__init__()
        self.THEME_COLOR = self.skyblue
        self.THEME_BGROUND_COLOR = self.black
        self.THEME_CHOSEN_COLOR = self.black_on_skyblue
        self.THEME_UNCHOSEN_COLOR = self.white

        self._width = width
        self._height = height

        if (self.width <  self._width) or (self.height < self._height):
            print("Terminal window is too small, please enlarge the window.")
            print(f"Terminal size: {self.width}x{self.height}")
            print(f"Required size: { self._width}x{self._height}")
            exit()

    def split_str_by_len(self, text, length):
        return [text[i:i+length] for i in range(0, len(text), length)]

    def draw_title(self, title):
        sapce = " "*int(self._width/2-len(title)/2)
        title = sapce + title + sapce
        print(self.home() + self.THEME_CHOSEN_COLOR(f'{title}'))

    def draw(self, content, color=None, location=None, align='left', box_width=None, margin=1):
        #
        if color is None:
            color = self.THEME_COLOR
        #
        if location is None:
            _x, _y = self.get_location()
        else:
            _x, _y = location
        #
        if not isinstance(content, list):
            content = [content]
        #
        if box_width is None:
            box_width = 0
            for _line in content:
                if len(_line) > box_width:
                    box_width = len(_line)
            box_width += margin*2
            if box_width > self._width:
                box_width = self._width

        max_len = box_width - margin*2

        new_content = []
        for line in content:
            if len(line) > max_len:
                _strs = self.split_str_by_len(line, max_len)
                new_content.extend(_strs)
            else:
                new_content.append(line)

        for i, line in enumerate(new_content):
            print(self.move_xy(_x, _y+i), end='')
            if align == 'left':
                space = " "*(box_width-len(line))
                print(color(f'{line}{space}'), end='', flush=True)
            elif align == 'right':
                space = " "*(box_width-len(line))
                print(color(f'{space}{line}'), end='', flush=True)
            elif align == 'center':
                space = " "*int((box_width-len(line))/2)
                print(color(f'{space}{line}{space}'), end='', flush=True)

    def draw_options(self, 
                    content,
                    selected_index,
                    location = None,
                    selected_color=None,
                    unselected_color=None,
                    align='left',
                    box_width=None):
        #
        if selected_color is None:
            selected_color = self.THEME_CHOSEN_COLOR
        if unselected_color is None:
            unselected_color = self.THEME_UNCHOSEN_COLOR
        #
        _x, _y = location
        #
        for i, line in enumerate(content):
            # location
            print(self.move_xy(_x, _y+i), end='')
            # color
            if i == selected_index:
                color = selected_color
            else:
                color = unselected_color

            # no fixed width
            if box_width is None or len(line) >= box_width:
                print(color(f'{line}'))
            # fixed width, align
            else:
                if align == 'left':
                    space = " "*(box_width-len(line))
                    print(color(f'{line}{space}'))
                elif align == 'right':
                    space = " "*(box_width-len(line))
                    print(color(f'{space}{line}'))
                elif align == 'center':
                    space = " "*int((box_width-len(line))/2)
                    print(color(f'{space}{line}{space}'))

    def draw_ask(self,
                question,
                color=None,
                location=None,
                align='left',
                box_width=None):

        if color is None:
            color = self.THEME_COLOR
        if location is None:
            location=(0, self.height-1)

        with self.location():
            self.draw(question, color, location, align, box_width)
            while True:
                key = self.inkey()
                if key.lower() == 'y':
                    return True
                elif key.lower() == 'n':
                    return False
                elif key.name == 'KEY_ESCAPE':
                    return False
                else:
                    continue

    def draw_progress_bar(self, percentage, color=None, bg_color=None, location=None, box_width=10):
        if color is None:
            color = self.THEME_CHOSEN_COLOR
        if bg_color is None:
            bg_color = self.THEME_COLOR
        if location is None:
            _x, _y = self.get_location()
        else:
            _x, _y = location

        if percentage > 100:
            percentage = 100
        elif percentage < 0:
            percentage = 0

        bar = int(percentage/100*box_width)

        with self.location():
            print(self.move_xy(_x, _y), end='')
            print(bg_color(f'{percentage:3d}%'), end='')
            print(bg_color(f'|'), end='')
            print(color(f' '*bar), end='')
            print(bg_color(f' '*(box_width-bar)), end='')
            print(bg_color(f'|'), end='')

    def clear_xline(self, line):
        with self.location():
            print(self.move_xy(0, line) + self.clear_line, end='')
