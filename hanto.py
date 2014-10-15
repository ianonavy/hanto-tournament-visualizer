from __future__ import division

import argparse
import itertools
import sys
import threading
from math import pi, cos, sin, sqrt

import Tkinter as tk
from PIL import Image, ImageTk
from Queue import Queue


LINE_THICKNESS = 3
SCALE_DOWN_FACTOR = .75
COLORS = {
    'RED_WINS': 'red',
    'BLUE_WINS': 'blue',
    'DRAW': 'green'
}
END_MESSAGES = {
    'RED_WINS': "Red wins!",
    'BLUE_WINS': "Blue wins!",
    'DRAW': "It's a draw!"
}
IMAGE_PATH = "img/{}.gif"


def get_offsets(width, height, r, x, y):
    x_offset = width / 2 + (r * 1.5 * x)
    y_offset = height / 2 - (r * sqrt(3) * y) - (r * sqrt(3) / 2 * x)
    return x_offset, y_offset


def make_hex(width, height, r, x, y):
    coords = []
    n = 6

    x_offset, y_offset = get_offsets(width, height, r, x, y)
    angle = 2 * pi / n
    for i in range(n):
        dx = (r * cos(i * angle)) + x_offset
        dy = (r * sin(i * angle)) + y_offset
        coords.append((dx, dy))
    return coords


class ImageLoader(object):

    def __init__(self, hex_radius):
        self.hex_radius = int(hex_radius)
        self.animal_imgs = {}

    def set_hex_radius(self, new_r):
        self.hex_radius = int(new_r)

    def get_animal(self, animal):
        hex_radius = self.hex_radius
        if animal in self.animal_imgs:
            return self.animal_imgs[animal]
        im = Image.open(IMAGE_PATH.format(animal))
        im = im.resize((hex_radius * 2, hex_radius * 2), Image.ANTIALIAS)
        self.animal_imgs[animal] = ImageTk.PhotoImage(im)
        return self.animal_imgs[animal]

    def clear(self):
        for key in self.animal_imgs.keys():
            del self.animal_imgs[key]


class Piece(object):
    def __init__(self, app, x, y, animal, color):
        self.app = app
        self.canvas = app.canvas
        self.x = x
        self.y = y
        self.animal = animal
        self.color = color
        self.hex_id = None
        self.animal_id = None

    def draw(self):
        app = self.app
        width, height, r = app.width, app.height, app.hex_radius
        dx, dy = get_offsets(width, height, r, self.x, self.y)
        hex_coords = make_hex(width, height, r, self.x, self.y)
        if any(map(app.out_of_bounds, hex_coords)):
            app.scale_down()
            return
        self.hex_id = self.canvas.create_polygon(
            *itertools.chain(hex_coords),
            outline="black",
            fill=self.color,
            width=LINE_THICKNESS)
        self.animal_id = self.canvas.create_image(
            dx, dy, image=app.image_loader.get_animal(self.animal))

    def move(self, new_x, new_y):
        assert self.hex_id and self.animal_id
        self.canvas.delete(self.hex_id)
        self.canvas.delete(self.animal_id)
        self.x = new_x
        self.y = new_y
        self.draw()
        self.app.re_render()

    def __repr__(self):
        return "({}, {}): {} {}".format(
            self.x, self.y, self.color, self.animal)


class App(object):

    def __init__(self, master, width, height, hex_radius, delay,
                 close_timer, continuous, **kwargs):
        self.master = master
        self.width = width
        self.height = height
        self.hex_radius = hex_radius
        self.delay = delay
        self.close_timer = close_timer
        self.continuous = continuous
        self.canvas = tk.Canvas(self.master, width=width, height=height)
        self.canvas.pack()
        self.master.after(0, self.draw_grid)
        self.master.after(0, self.animation)
        self.queue = Queue()
        self.image_loader = ImageLoader(hex_radius)
        self.pieces = {}
        ReadThread(self.queue, continuous).start()

    def draw_grid(self):
        width, height, r = self.width, self.height, self.hex_radius
        dx = int(width / r) + 2
        dy = int(height / r) + 2
        for i in range(-dx, dx):
            for j in range(-dy, dy):
                hexes = make_hex(width, height, r, i, j)
                self.canvas.create_polygon(
                    *hexes,
                    outline="black",
                    fill="white",
                    width=LINE_THICKNESS)

    def out_of_bounds(self, coord):
        x, y = coord
        return x < 0 or y < 0 or x > self.width or y > self.height

    def scale_down(self):
        self.hex_radius *= SCALE_DOWN_FACTOR
        self.image_loader.set_hex_radius(self.hex_radius)
        self.re_render()

    def re_render(self):
        self.canvas.delete("all")
        self.draw_grid()
        self.image_loader.clear()
        for piece in self.pieces.values():
            piece.draw()

    def finish(self):
        if self.continuous:
            self.pieces = {}
            self.re_render()
            self.master.after(0, self.animation)
        else:
            sys.exit()

    def animation(self):
        if not self.queue.empty():
            item = self.queue.get()
            if item[0] == 'result':
                # arbitrary placement of win text: in the middle,
                # 8th from the top
                outline = self.canvas.create_text(
                    (self.width / 2, self.height / 8),
                    text=END_MESSAGES[item[1]],
                    justify=tk.CENTER,
                    fill="#222",
                    font=("Arial", int(self.height / 10)))
                self.canvas.scale(
                    outline, self.width / 2 - 3, self.height / 8 - 3, 2, 2)

                self.canvas.create_text(
                    (self.width / 2, self.height / 8),
                    text=END_MESSAGES[item[1]],
                    justify=tk.CENTER,
                    fill=COLORS.get(item[1]),
                    font=("Arial", int(self.height / 10)))
                if self.close_timer:
                    self.master.after(self.close_timer, self.finish)
                    return
            else:
                x1, y1, x2, y2, animal, color = item
                if not x1 and not y1:
                    piece = Piece(self, x2, y2, animal, color)
                    self.pieces[x2, y2] = piece
                    piece.draw()
                else:
                    piece = self.pieces[x1, y1]
                    piece.move(x2, y2)
                    del self.pieces[x1, y1]
                    self.pieces[x2, y2] = piece

        self.master.after(self.delay, self.animation)


class ReadThread(threading.Thread):

    def __init__(self, queue, continuous, *args, **kwargs):
        self.queue = queue
        self.continuous = continuous
        super(ReadThread, self).__init__(*args, **kwargs)

    def run(self):
        line = 'wheeee'
        while not self.is_done(line):
            try:
                line = raw_input()
            except EOFError:
                break
            print(line)
            val = self.parse(line)
            if val:
                self.queue.put(val)

    def is_done(self, line):
        return ("DRAW" in line or "WINS" in line) and not self.continuous

    def parse(self, line):
        words = line.split()
        if not len(words) >= 6 and 'Exception' not in line:
            return ('result', line)
        color = words[0].lower()
        if color == 'blue':
            color = 'lightblue'
        animal = words[2].lower()
        x1 = None
        y1 = None
        x2 = None
        y2 = None
        if 'places' in line:
            x2 = int(words[4][1:-1])
            y2 = int(words[5][:-1])
        elif 'moves' in line:
            x1 = int(words[4][1:-1])
            y1 = int(words[5][:-1])
            x2 = int(words[7][1:-1])
            y2 = int(words[8][:-1])
        return (x1, y1, x2, y2, animal, color)


def main():
    WIDTH = 800
    HEIGHT = 600
    HEX_RADIUS = 600
    DELAY = int(1000 / 60)  # 60 fps
    CLOSE_TIMER = 3000
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--geometry", help="<width>x<height>",
        default="%sx%s" % (WIDTH, HEIGHT))
    parser.add_argument(
        "--delay", help="delay in ms", type=int, default=DELAY)
    parser.add_argument(
        "--close-timer",
        help="time in ms before it closes. 0 for infinite",
        type=int,
        default=CLOSE_TIMER)
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="overrides geometry")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="continuously runs for multiple games")
    args = parser.parse_args()

    try:
        width, height = args.geometry.split('x')
        width = int(width)
        height = int(height)
    except:
        print("--geometry flag must be in the format <width>x<height>")
        sys.exit()

    delay = max(DELAY, args.delay)

    root = tk.Tk()
    root.config(bg="white")
    root.wm_title("Hanto Tournament")
    if args.fullscreen:
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        root.overrideredirect(1)
        root.geometry("%dx%d+0+0" % (width, height))
    app = App(
        root, width, height, HEX_RADIUS, args.delay, args.close_timer,
        args.continuous)
    root.mainloop()


if __name__ == '__main__':
    main()
