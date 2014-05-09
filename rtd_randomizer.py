import re
import random
import libtcodpy as libtcod


INDENTSIZE = 4
indent_check = re.compile("\\A\\s+")
category_check = re.compile("\\[[^\\]]+\\]")
catarg_check = re.compile("[^\\[\\]:]+")
flagarg_check = re.compile("([^\\(\\)]+)\\(([^\\)]*)\\)")
note_check = re.compile("\"([^\"]*)\"$")
remove_comment = re.compile("(?<!\\\\)#.*")
category_list = []

RESULT_W, RESULT_H = 35, 35
result_display = libtcod.console_new(RESULT_W, RESULT_H)


def is_num(string_in):
    try:
        int(string_in)
        return True
    except ValueError:
        dice = re.match("(\\d*)d(\\d+)", string_in)
        if dice is None:
            return False
        return True


def make_num(string_in):
    try:
        return int(string_in)
    except ValueError:
        dice = re.match("(\\d*)d(\\d+)(?:([\\+\\-\\*/])(\\d+))?", string_in)
        if dice is not None:
            numret = 0
            for d in range(int(dice.group(1))):
                numret += random.randint(1, int(dice.group(2)))
            if dice.group(3) is not None:
                if dice.group(3) == '+':
                    numret += make_num(dice.group(4))
                elif dice.group(3) == '-':
                    numret -= make_num(dice.group(4))
                elif dice.group(3) == '*':
                    numret *= make_num(dice.group(4))
                elif dice.group(3) == '/':
                    numret /= make_num(dice.group(4))
            return numret
        return 0


class Category:
    name = None
    sub = None
    genlist = None
    parent = None
    note = None
    all = False
    number = False
    hidden = False
    item_chance_min = 1
    item_chance_max = 1
    initial_value = 0
    run_for = 1

    def __init__(self):
        self.name = ""
        self.sub = []
        self.genlist = []
        self.note = ""

    def get(self):
        r = make_num(self.run_for)
        if self.all:
            if self.item_chance_max < self.item_chance_min:
                self.item_chance_max = self.item_chance_min
            retlist = []
            for l in self.genlist:
                if random.randint(1, self.item_chance_max) <= self.item_chance_min:
                    retlist.append(l)
        else:
            retlist = random.sample(self.genlist, min(r, len(self.genlist)))
        if self.number:
            numret = make_num(self.initial_value)
            for r in retlist:
                r = re.match("\\A([\\+\\-\\*/])?(.+)", r)
                if r is not None:
                    if r.group(1) is None:
                        numret = make_num(r.group(2))
                    elif r.group(1) == '+':
                        numret += make_num(r.group(2))
                    elif r.group(1) == '-':
                        numret -= make_num(r.group(2))
                    elif r.group(1) == '*':
                        numret *= make_num(r.group(2))
                    elif r.group(1) == '/':
                        numret /= make_num(r.group(2))
            return [str(numret)]
        else:
            return retlist

    pc = [0, 0]

    def print_rec(self, layer):
        libtcod.console_set_color_control(libtcod.COLCTRL_2, libtcod.turquoise, libtcod.black)
        libtcod.console_set_color_control(libtcod.COLCTRL_3, libtcod.gray, libtcod.black)
        libtcod.console_print_rect(result_display, Category.pc[0] + layer, Category.pc[1], 30 - Category.pc[0], 30, "{:c}{}:{:c}".format(libtcod.COLCTRL_2, self.name, libtcod.COLCTRL_STOP))
        libtcod.console_print(result_display, Category.pc[0], Category.pc[1], "{:c}{}{:c}".format(libtcod.COLCTRL_3, '|' * layer, libtcod.COLCTRL_STOP))
        Category.pc[1] += libtcod.console_get_height_rect(result_display, Category.pc[0] + layer, Category.pc[1], 30 - Category.pc[0], 30, "{:c}{}:{:c}".format(libtcod.COLCTRL_2, self.name, libtcod.COLCTRL_STOP))
        for g in self.get():
            libtcod.console_print_rect(result_display, Category.pc[0] + layer, Category.pc[1], 30 - Category.pc[0], 30, "{}".format(g))
            libtcod.console_print(result_display, Category.pc[0], Category.pc[1], "{:c}{}{:c}".format(libtcod.COLCTRL_3, '|' * layer, libtcod.COLCTRL_STOP))
            Category.pc[1] += libtcod.console_print_rect(result_display, Category.pc[0] + layer, Category.pc[1], 30 - Category.pc[0], 30, "{}".format(g))
        for s in self.sub:
            s.print_rec(layer + 1)


def get_indent(line_in):
    substr = indent_check.match(line_in)
    if substr is None or len(substr.group()) == 0:
        return 0
    count = int(substr.group().count(' ') / 4)
    count += substr.group().count('\t')
    return count


def scan_file(filename):
    with open(filename, "r") as file:
        current = None
        linenum = 0
        current_indent = 0
        for line in file:
            if line[0] == '#' or line[0] == '\n':
                continue
            if line[-1] == '\n':
                line = line[:-1]
            line = re.sub(remove_comment, "", line)
            indent = get_indent(line)
            category_info = re.search(category_check, line)
            if category_info is None:
                if current is None:
                    print("Syntax Error (line " + str(linenum) + "): list item defined outside generator")
                    return False
                note = re.match(note_check, line)
                if note is None:
                    line = re.sub("\\A\\s+", "", line)
                    line = re.sub("\\Z\\s+", "", line)
                    if len(line):
                        current.genlist.append(line)
                else:
                    current.note = note.group(1)
            else:
                category_info = re.findall(catarg_check, category_info.group())
                if indent > current_indent + 1:
                    print("Syntax Error (line " + str(linenum) + "): too many indents!")
                    return False
                # Use indent to determine where to place this category object
                add_this = Category()
                add_to = current
                for x in range(-1, current_indent - indent):
                    if add_to is None:
                        break
                    add_to = add_to.parent
                if add_to is None:
                    category_list.append(add_this)
                else:
                    add_to.sub.append(add_this)
                    add_this.parent = add_to
                for arg in category_info:
                    flag = re.match(flagarg_check, arg)
                    if flag is None:
                        if is_num(arg):
                            add_this.run_for = arg
                        else:
                            add_this.name = arg
                    else:
                        if flag.group(2):
                            flagarg = re.findall("[^,]+", flag.group(2))
                        else:
                            flagarg = []
                        if flag.group(1) == "ALL":
                            add_this.all = True
                            if len(flagarg) >= 2:
                                try:
                                    add_this.item_chance_max = max(1, int(flagarg[1]))
                                except ValueError:
                                    add_this.item_chance_max = 1
                                try:
                                    add_this.item_chance_min = max(1, int(flagarg[0]))
                                except ValueError:
                                    add_this.item_chance_min = 1
                            elif len(flagarg):
                                try:
                                    add_this.item_chance_max = max(1, int(flagarg[0]))
                                except ValueError:
                                    add_this.item_chance_max = 1
                        elif flag.group(1) == "NUMBER":
                            add_this.number = True
                            if len(flagarg):
                                add_this.initial_value = make_num(flagarg[0])
                        elif flag.group(1) == "HIDDEN":
                            add_this.hidden = True
                current = add_this
                current_indent = indent
            linenum += 1
    return True

select = 0
list_cam = 0
list_size = 30


def do_input(event, key, mouse):
    global select, list_cam
    if event == libtcod.EVENT_KEY_PRESS:
        if key.vk == libtcod.KEY_KP8 or key.vk == libtcod.KEY_UP:
            select -= 1
            if select < 0:
                select += len(category_list)
            list_cam = max(0, min(len(category_list) - list_size, int(select - list_size / 2)))
        elif key.vk == libtcod.KEY_KP2 or key.vk == libtcod.KEY_DOWN:
            select += 1
            if select >= len(category_list):
                select -= len(category_list)
            list_cam = max(0, min(len(category_list) - list_size, int(select - list_size / 2)))
        elif key.vk == libtcod.KEY_KP8 or key.vk == libtcod.KEY_ENTER:
            libtcod.console_clear(result_display)
            Category.pc = [0, 0]
            category_list[select].print_rec(0)


def do_update():
    pass


def do_render():
    y = 1
    for c in range(list_cam, min(list_size + list_cam, len(category_list))):
        if c == select:
            libtcod.console_set_color_control(libtcod.COLCTRL_1, libtcod.cyan, libtcod.blue)
        else:
            libtcod.console_set_color_control(libtcod.COLCTRL_1, libtcod.white, libtcod.black)
        libtcod.console_print(0, 1, y, "{:c}{}{:c}".format(libtcod.COLCTRL_1, category_list[c].name, libtcod.COLCTRL_STOP))
        y += 1
    libtcod.console_blit(result_display, 0, 0, RESULT_W, RESULT_H, 0, 18, 1)


libtcod.console_set_custom_font(b'terminal.png', libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(50, 50, b'RTD Randomizer')
libtcod.sys_set_fps(30)
scan_file("gen.txt")

key = libtcod.Key()
mouse = libtcod.Mouse()
while not libtcod.console_is_window_closed():
    while True:
        event = libtcod.sys_check_for_event(libtcod.EVENT_ANY, key, mouse)
        if event == 0:
            break
        do_input(event, key, mouse)
    do_update()
    libtcod.console_clear(0)
    do_render()
    libtcod.console_flush()