# pr files = off
import pygame, math, random, sys
from array import array

pygame.init()
W, H = 224, 288
SC = 2
FPS = 60
TILE, COLS, ROWS, TOP = 8, 28, 31, 24
STEP = 1.0 / 120.0

UP, LEFT, DOWN, RIGHT = (0, -1), (-1, 0), (0, 1), (1, 0)
DIRS = (UP, LEFT, DOWN, RIGHT)

_NES = (
    (0x66,0x66,0x66),(0x00,0x2A,0x88),(0x14,0x12,0xA7),(0x3B,0x00,0xA4),
    (0x5C,0x00,0x7E),(0x6E,0x00,0x40),(0x6C,0x06,0x00),(0x56,0x1D,0x00),
    (0x33,0x35,0x00),(0x0B,0x48,0x00),(0x00,0x52,0x00),(0x00,0x4F,0x08),
    (0x00,0x40,0x4D),(0,0,0),(0,0,0),(0,0,0),
    (0xAD,0xAD,0xAD),(0x15,0x5F,0xD9),(0x42,0x40,0xFF),(0x75,0x27,0xFE),
    (0xA0,0x1A,0xCC),(0xB7,0x1E,0x7B),(0xB5,0x31,0x20),(0x99,0x4E,0x00),
    (0x6B,0x6D,0x00),(0x38,0x87,0x00),(0x0C,0x93,0x00),(0x00,0x8F,0x32),
    (0x00,0x7C,0x8D),(0,0,0),(0,0,0),(0,0,0),
    (0xFF,0xFE,0xFF),(0x64,0xB0,0xFF),(0x92,0x90,0xFF),(0xC6,0x76,0xFF),
    (0xF3,0x6A,0xFF),(0xFE,0x6E,0xCC),(0xFE,0x81,0x70),(0xEA,0x9E,0x22),
    (0xBC,0xBE,0x00),(0x88,0xD8,0x00),(0x5C,0xE4,0x30),(0x45,0xE0,0x82),
    (0x48,0xCD,0xDE),(0x4F,0x4F,0x4F),(0,0,0),(0,0,0),
    (0xFF,0xFE,0xFF),(0xC0,0xDF,0xFF),(0xD3,0xD2,0xFF),(0xE8,0xC8,0xFF),
    (0xFB,0xC2,0xFF),(0xFE,0xC4,0xEA),(0xFE,0xCC,0xC5),(0xF7,0xD8,0xA5),
    (0xE4,0xE5,0x94),(0xCF,0xEF,0x96),(0xBD,0xF4,0xAB),(0xB3,0xF3,0xCC),
    (0xB5,0xEB,0xF2),(0xB8,0xB8,0xB8),(0,0,0),(0,0,0),
)
def _tint(c):
    r, g, b = c
    return (int(r * 0.55), int(g * 0.75), min(255, int(b * 1.10) + 35))
PAL = tuple(_tint(c) for c in _NES)

BLACK   = (0, 0, 0)
WALL    = PAL[0x12]
DOT     = PAL[0x27]
PELLET  = PAL[0x27]
PAC     = PAL[0x28]
GHOSTS  = (PAL[0x26], PAL[0x25], PAL[0x24], PAL[0x21])
FRIGHT  = PAL[0x11]
GOLD    = PAL[0x28]
MENU_HI = PAL[0x21]
WHITE   = (255, 255, 255)
RED     = (255, 60, 60)

GHOST_NAMES  = ("SHADOW", "SPEEDY", "BASHFUL", "POKEY")
GHOST_ALIAS  = ("BLINKY", "PINKY", "INKY", "CLYDE")

# fruit table — 8 entries, indexed by (level - 1) // 2, capped
FRUITS = (
    ("cherry", 100),
    ("straw", 300),
    ("orange", 500),
    ("apple", 700),
    ("melon", 1000),
    ("galaxian", 2000),
    ("bell", 3000),
    ("key", 5000),
)

LAYOUT = (
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......  .......##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
)

# ── synth ────────────────────────────────────────────────────────────────
class Synth:
    RATE = 22050
    def __init__(self):
        self.ok = False
        self.muted = False
        self.s = {}
        try:
            pygame.mixer.pre_init(self.RATE, -16, 1, 256)
            pygame.mixer.init(self.RATE, -16, 1, 256)
            pygame.mixer.set_num_channels(4)
            self.ch = [pygame.mixer.Channel(i) for i in range(4)]
            self.ok = True
            self._build()
        except Exception:
            self.ok = False

    def _synth(self, dur, f, vol=0.18, sq=True):
        n = max(1, int(self.RATE * dur))
        buf = array("h")
        ph = 0.0
        for i in range(n):
            t = i / self.RATE
            fr = f(t) if callable(f) else f
            ph = (ph + max(0.0, fr) / self.RATE) % 1.0
            wv = 1.0 if ph < 0.5 else -1.0 if sq else 1.0 - 4.0 * abs(ph - 0.5)
            env = min(1.0, i / 60, (n - 1 - i) / 120)
            v = int(wv * env * vol * 32767)
            buf.append(max(-32768, min(32767, v)))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        self.s["waka"]   = self._synth(0.07, lambda t: 240 + 520 * t)
        self.s["waka2"]  = self._synth(0.07, lambda t: 760 - 520 * t)
        self.s["pellet"] = self._synth(0.30, lambda t: 180 + 1400 * t)
        self.s["ghost"]  = self._synth(0.35, lambda t: 350 + 2200 * t + 65 * math.sin(t * 90))
        self.s["death"]  = self._synth(1.40, lambda t: max(50, 780 * (1 - t / 1.5) + 90 * math.sin(t * 60)), 0.20)
        self.s["fruit"]  = self._synth(0.25, lambda t: 880 if t < 0.12 else 1320, 0.16)
        self.s["menu"]   = self._synth(0.08, lambda t: 660, 0.14)
        self.s["sel"]    = self._synth(0.14, lambda t: 880 + 200 * t, 0.18)
        self.s["intro"]  = self._synth(0.45, lambda t: 520 + 700 * t, 0.16)
        self.s["extra"]  = self._synth(0.55, lambda t: 520 + 1200 * t, 0.22)

    def play(self, name, ch=2):
        if self.ok and not self.muted and name in self.s:
            self.ch[ch].play(self.s[name])

    def toggle(self):
        self.muted = not self.muted
        if self.ok:
            for c in self.ch:
                c.stop()

# ── actors ───────────────────────────────────────────────────────────────
class Actor:
    __slots__ = ("tile", "direction", "target", "progress")
    def __init__(self, tile, direction=LEFT):
        self.tile = tile
        self.direction = direction
        self.target = None
        self.progress = 0.0

    @property
    def pos(self):
        if self.target is None:
            return self.tile
        return (self.tile[0] + self.direction[0] * self.progress,
                self.tile[1] + self.direction[1] * self.progress)

    def reverse(self):
        self.direction = (-self.direction[0], -self.direction[1])
        if self.target is not None:
            self.tile, self.target = self.target, self.tile
            self.progress = 1.0 - self.progress

    def move(self, dist, graph, choose, arrive=None):
        while dist > 1e-9:
            if self.target is None:
                d = choose(self)
                if d not in graph.get(self.tile, {}):
                    return
                self.direction = d
                self.target = graph[self.tile][d]
                self.progress = 0.0
            amt = min(dist, 1.0 - self.progress)
            self.progress += amt
            dist -= amt
            if self.progress >= 1.0 - 1e-9:
                self.tile = self.target
                self.target = None
                self.progress = 0.0
                if arrive and arrive(self) is False:
                    return

# ── maze ─────────────────────────────────────────────────────────────────
class Maze:
    def __init__(self):
        self.dots = {(x, y) for y, r in enumerate(LAYOUT) for x, c in enumerate(r) if c == "."}
        self.pellets = {(x, y) for y, r in enumerate(LAYOUT) for x, c in enumerate(r) if c == "o"}
        floor = {(x, y) for y, r in enumerate(LAYOUT) for x, c in enumerate(r) if c != "#"}
        doors = {(13, 12), (14, 12)}
        def flood(allowed):
            seen = {(13, 23)}
            q = [(13, 23)]
            while q:
                t = q.pop()
                for d in DIRS:
                    n = ((t[0] + d[0]) % COLS, t[1] + d[1])
                    if n in allowed and n not in seen:
                        seen.add(n)
                        q.append(n)
            return seen
        self.inside = flood(floor)
        self.outside = flood(floor - doors)
        self.total = len(self.dots) + len(self.pellets)
        self.graph = self._graph(self.outside)
        self.house = self._graph(self.inside)
        self.home_field = self._dist((13, 14), self.house)
        self.exit_field = self._dist((13, 11), self.house)
        self.walls = self._render()

    @staticmethod
    def _graph(tiles):
        g = {}
        for t in tiles:
            g[t] = {}
            for d in DIRS:
                n = ((t[0] + d[0]) % COLS, t[1] + d[1])
                if n in tiles:
                    g[t][d] = n
        return g

    @staticmethod
    def _dist(target, graph):
        out = {target: 0}
        q = [target]
        while q:
            t = q.pop()
            for n in graph.get(t, {}).values():
                if n not in out:
                    out[n] = out[t] + 1
                    q.append(n)
        return out

    def _render(self):
        s = pygame.Surface((W, H))
        s.fill(BLACK)
        for y, row in enumerate(LAYOUT):
            for x, c in enumerate(row):
                if c != "#":
                    continue
                px, py = x * TILE, TOP + y * TILE
                u = (x, y - 1) in self.inside
                d = (x, y + 1) in self.inside
                l = (x - 1, y) in self.inside
                r = (x + 1, y) in self.inside
                x0, x1 = px + (2 if l else 0), px + (5 if r else 7)
                y0, y1 = py + (2 if u else 0), py + (5 if d else 7)
                if u:
                    pygame.draw.line(s, WALL, (x0, py + 2), (x1, py + 2))
                if d:
                    pygame.draw.line(s, WALL, (x0, py + 5), (x1, py + 5))
                if l:
                    pygame.draw.line(s, WALL, (px + 2, y0), (px + 2, y1))
                if r:
                    pygame.draw.line(s, WALL, (px + 5, y0), (px + 5, y1))
        return s

# ── ghosts ───────────────────────────────────────────────────────────────
class Ghost(Actor):
    def __init__(self, i):
        super().__init__(((13, 11), (13, 14), (11, 14), (15, 14))[i])
        self.i = i
        self.state = "normal" if i == 0 else "house"
        self.fright = False
        self.wait = 0.6 + i * 0.25
        self.reborn = False

# ── game ─────────────────────────────────────────────────────────────────
class Game:
    KILL = 256
    FRUIT_DOTS = (70, 170)
    EXTRA_LIFE = (10000, 50000, 100000)

    def __init__(self):
        self.maze = Maze()
        self.synth = Synth()
        self.rng = random.Random()
        self.state = "intro"
        self.intro_t = 0.0
        self.timer = 0.0
        self.score = 0
        self.high = 0
        self.lives = 3
        self.level = 1
        self.fruit_cleared = 0
        self.fruit_used = 0
        self.next_extra = 0
        self.fruit_history = []
        self.reset()

    def reset(self):
        self.pac = Actor((13, 23), LEFT)
        self.queued = LEFT
        self.ghosts = [Ghost(i) for i in range(4)]
        self.dots = set(self.maze.dots)
        self.pellets = set(self.maze.pellets)
        self.fright = 0.0
        self.mode_time = 0.0
        self.wave = 0
        self.mode = "scatter"
        self.chain = 0
        self.death = 0.0
        self.fruit_cleared = 0
        self.fruit_used = 0
        self.fruit_score = 0
        self.fruit_pos = (13.5, 17)
        self.fruit_timer = 0.0
        if self.level >= self.KILL:
            self._kill_screen()

    def _kill_screen(self):
        rng = random.Random(0x100)
        for y in range(ROWS):
            for x in range(COLS // 2, COLS):
                if LAYOUT[y][x] != "#" and rng.random() < 0.40:
                    self.dots.add((x, y))
        for (x, y) in list(self.dots):
            if rng.random() < 0.30:
                self.dots.add((x, y))

    def remaining(self):
        return len(self.dots) + len(self.pellets)

    def add_score(self, pts):
        self.score += pts
        while self.next_extra < len(self.EXTRA_LIFE) and self.score >= self.EXTRA_LIFE[self.next_extra]:
            self.lives += 1
            self.next_extra += 1
            self.synth.play("extra")
        self.high = max(self.high, self.score)

    def choose_pac(self, a):
        ch = self.maze.graph.get(a.tile, {})
        if self.queued in ch:
            return self.queued
        return a.direction if a.direction in ch else None

    def target(self, g):
        corners = ((30, -3), (-3, -3), (30, 34), (-3, 34))
        if self.mode == "scatter":
            return corners[g.i]
        px, py = self.pac.tile
        dx, dy = self.pac.direction
        if g.i == 0:
            return (px, py)
        if g.i == 1:
            return (px + dx * 4 - (4 if dy == -1 else 0), py + dy * 4)
        if g.i == 2:
            ax, ay = px + dx * 2 - (2 if dy == -1 else 0), py + dy * 2
            bx, by = self.ghosts[0].tile
            return (2 * ax - bx, 2 * ay - by)
        if (g.tile[0] - px) ** 2 + (g.tile[1] - py) ** 2 >= 64:
            return (px, py)
        return corners[3]

    def choose_ghost(self, g):
        if g.state in ("eyes", "exit"):
            gr = self.maze.house.get(g.tile, {})
            field = self.maze.home_field if g.state == "eyes" else self.maze.exit_field
            if not gr:
                return None
            return min(gr, key=lambda d: field.get(gr[d], 9999))
        ch = self.maze.graph.get(g.tile, {})
        avail = [d for d in DIRS if d in ch and d != (-g.direction[0], -g.direction[1])]
        if not avail:
            back = (-g.direction[0], -g.direction[1])
            return back if back in ch else None
        if g.fright:
            return self.rng.choice(avail)
        if g.tile in ((12, 11), (15, 11), (12, 23), (15, 23)):
            f = [d for d in avail if d != UP]
            if f:
                avail = f
        t = self.target(g)
        return min(avail, key=lambda d: (ch[d][0] - t[0]) ** 2 + (ch[d][1] - t[1]) ** 2)

    def arrive_ghost(self, g):
        if g.state == "eyes" and g.tile == (13, 14):
            g.state = "house"
            g.fright = False
            g.wait = 0.5
            g.reborn = True
            return False
        if g.state == "exit" and g.tile == (13, 11):
            g.state = "normal"
            g.direction = LEFT
            return False
        return True

    def update_ghost(self, g, dt):
        if g.state == "house":
            g.wait -= dt
            if g.wait <= 0:
                g.state = "exit"
            else:
                return
        sp = 7.6 if self.level == 1 else 8.55 if self.level < 5 else 9.5
        if g.state == "eyes":
            sp = 15.0
        elif g.state == "exit":
            sp = 4.0
        elif g.fright:
            sp *= 0.62
        graph = self.maze.house if g.state in ("eyes", "exit") else self.maze.graph
        g.move(sp * dt, graph, self.choose_ghost, self.arrive_ghost)

    def update(self, dt):
        self.timer += dt
        if self.state == "intro":
            self.intro_t += dt
            if self.intro_t >= 4.0:
                self.state = "ready"
                self.timer = 0.0
            return
        if self.state == "ready":
            if self.timer >= 2.0:
                self.state = "play"
                self.timer = 0.0
            return
        if self.state == "dying":
            self.death += dt
            if self.death > 1.5:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "over"
                    self.timer = 0.0
                else:
                    self.reset()
                    self.state = "intro"
                    self.intro_t = 0.0
            return
        if self.state == "over":
            return
        # fruit timer
        if self.fruit_timer > 0:
            self.fruit_timer = max(0.0, self.fruit_timer - dt)
        # fright timer
        if self.fright > 0:
            self.fright = max(0.0, self.fright - dt)
            if self.fright == 0:
                for g in self.ghosts:
                    g.fright = False
        else:
            periods = (7, 20, 7, 20, 5, 20, 5, float("inf"))
            self.mode_time += dt
            if self.mode_time >= periods[self.wave]:
                self.mode_time = 0.0
                self.wave = min(self.wave + 1, 7)
                self.mode = "scatter" if self.wave % 2 == 0 else "chase"
                for g in self.ghosts:
                    if g.state == "normal":
                        g.reverse()
        if self.queued == (-self.pac.direction[0], -self.pac.direction[1]):
            self.pac.reverse()
        sp = 7.6 if self.level == 1 else 8.55 if self.level < 5 else 9.5
        if self.fright > 0:
            sp *= 1.07
        self.pac.move(sp * dt, self.maze.graph, self.choose_pac, self.eat)
        for g in self.ghosts:
            self.update_ghost(g, dt)
        self.collide()
        # fruit pickup
        if self.fruit_timer > 0:
            fx, fy = self.fruit_pos
            px, py = self.pac.pos
            if abs(px - fx) < 0.9 and abs(py - fy) < 0.7:
                idx = min(len(FRUITS) - 1, (self.level - 1) // 2)
                self.add_score(FRUITS[idx][1])
                self.fruit_score = FRUITS[idx][1]
                self.fruit_timer = 0.0
                self.synth.play("fruit")

    def eat(self, a):
        t = a.tile
        if t in self.dots:
            self.dots.discard(t)
            self.add_score(10)
            self.synth.play("waka" if self.score % 20 == 0 else "waka2", 1)
        elif t in self.pellets:
            self.pellets.discard(t)
            self.add_score(50)
            self.fright = 6.0
            self.chain = 0
            for g in self.ghosts:
                if g.state != "eyes":
                    g.fright = True
                    if g.state == "normal":
                        g.reverse()
            self.synth.play("pellet")
        else:
            return True
        self.fruit_cleared += 1
        if self.level < self.KILL:
            # fruit spawn — arcade thresholds 70 and 170
            if self.fruit_cleared in self.FRUIT_DOTS and self.fruit_used < 2:
                self.fruit_used += 1
                self.fruit_timer = 9.0
                idx = min(len(FRUITS) - 1, (self.level - 1) // 2)
                self.fruit_history.append(FRUITS[idx][0])
                if len(self.fruit_history) > 7:
                    self.fruit_history.pop(0)
                self.synth.play("fruit")
        if self.remaining() == 0 and self.level < self.KILL:
            self.level += 1
            self.reset()
            self.state = "intro"
            self.intro_t = 0.0
            self.synth.play("intro")
        return False

    def collide(self):
        px, py = self.pac.pos
        for g in self.ghosts:
            if g.state != "normal":
                continue
            gx, gy = g.pos
            dx = abs(px - gx)
            dx = min(dx, COLS - dx)
            if dx * dx + (py - gy) ** 2 >= 0.64 ** 2:
                continue
            if g.fright:
                self.chain += 1
                pts = 200 * 2 ** min(3, self.chain - 1)
                self.add_score(pts)
                g.state = "eyes"
                g.fright = False
                self.synth.play("ghost")
            else:
                self.state = "dying"
                self.death = 0.0
                self.synth.play("death")
                return

    def key(self, k):
        m = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
             pygame.K_DOWN: DOWN, pygame.K_s: DOWN, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}
        if k in m:
            self.queued = m[k]

# ── draw helpers ─────────────────────────────────────────────────────────
def draw_pac(s, x, y, d, t, death=None, r=6, color=None):
    col = color if color else PAC
    ang = math.atan2(d[1], d[0])
    m = 0.08 + 0.65 * abs(math.sin(t * 15))
    if death is not None:
        if death >= 1:
            return
        ang = -math.pi / 2
        m = min(math.pi - 0.01, death * math.pi)
    pts = [(round(x), round(y))]
    for i in range(33):
        a = ang + m + (math.tau - 2 * m) * i / 32
        pts.append((round(x + math.cos(a) * r), round(y + math.sin(a) * r)))
    pygame.draw.polygon(s, col, pts)

def draw_ghost(s, x, y, i, d, t, fear=False, flash=False, eyes=False, r=6):
    x, y, r = round(x), round(y), r
    col = (255, 255, 255) if flash else (FRIGHT if fear else GHOSTS[i])
    if not eyes:
        pygame.draw.circle(s, col, (x, y - 1), r)
        pygame.draw.rect(s, col, (x - r, y - 1, r * 2 + 1, r + 1))
        off = int(t * 10) % 2
        feet = [(x - r, y + 1), (x + r, y + 1)]
        feet += [(x + r - k * r / 3, y + r - (2 if (k + off) % 2 else 0)) for k in range(7)]
        pygame.draw.polygon(s, col, feet)
    if fear and not eyes:
        ink = (255, 65, 65) if flash else (255, 255, 255)
        for dx in (-2, 2):
            pygame.draw.rect(s, ink, (x + dx - 1, y - 2, 2, 2))
        pygame.draw.lines(s, ink, False, [(x - 4 + k, y + 3 + k % 2) for k in range(9)])
    else:
        for dx in (-3, 3):
            pygame.draw.ellipse(s, (255, 255, 255), (x + dx - 2, y - 4, 5, 6))
            pygame.draw.rect(s, (25, 60, 230), (x + dx - 1 + d[0], y - 2 + d[1], 2, 3))

def draw_fruit(s, x, y, kind, r=5):
    """Draw a small arcade-style fruit in the given colour."""
    # pick colour per kind
    colours = {
        "cherry": (220, 40, 60),
        "straw": (240, 60, 70),
        "orange": (250, 150, 40),
        "apple": (230, 50, 60),
        "melon": (90, 200, 90),
        "galaxian": (240, 220, 80),
        "bell": (250, 220, 80),
        "key": (200, 200, 240),
    }
    col = colours.get(kind, (255, 200, 60))
    pygame.draw.circle(s, col, (x, y), r)
    pygame.draw.circle(s, (255, 255, 255), (x - r // 2, y - r // 2), max(1, r // 3))

# ── fonts ────────────────────────────────────────────────────────────────
BIG = None
MED = None
SML = None

def init_fonts():
    global BIG, MED, SML
    BIG = pygame.font.Font(None, 48)
    MED = pygame.font.Font(None, 20)
    SML = pygame.font.Font(None, 12)

def text_center(s, msg, font, color, y):
    img = font.render(msg, True, color)
    s.blit(img, (W // 2 - img.get_width() // 2, y))

def text_left(s, msg, font, color, x, y):
    img = font.render(msg, True, color)
    s.blit(img, (x, y))

def text_right(s, msg, font, color, x, y):
    img = font.render(msg, True, color)
    s.blit(img, (x - img.get_width(), y))

# ── HUD ──────────────────────────────────────────────────────────────────
def draw_hud(s, g):
    # top row: 1UP score on left, HIGH score in the middle
    text_left(s, "1UP", SML, (255, 255, 255), 4, 2)
    text_left(s, f"{g.score:06d}", SML, (255, 255, 255), 4, 12)
    text_center(s, "HIGH SCORE", SML, (255, 255, 255), 2)
    text_center(s, f"{g.high:06d}", SML, (255, 255, 255), 12)
    # level on the right
    text_right(s, f"LV {g.level:03d}", SML, GOLD, W - 4, 2)
    text_right(s, f"{g.remaining():03d}", SML, GOLD, W - 4, 12)

    # bottom left: lives as Pac-Man sprites
    lx = 6
    ly = H - 10
    for i in range(min(5, g.lives)):
        draw_pac(s, lx + i * 14, ly, LEFT, 0.07, r=5)

    # bottom right: fruit history (last 7 levels)
    fx = W - 6
    for i, kind in enumerate(reversed(g.fruit_history[-7:])):
        draw_fruit(s, fx - i * 14 - 6, ly, kind, r=5)

    # active fruit on the maze
    if g.fruit_timer > 0:
        idx = min(len(FRUITS) - 1, (g.level - 1) // 2)
        kind = FRUITS[idx][0]
        cx, cy = g.fruit_pos
        draw_fruit(s, cx * TILE, TOP + cy * TILE, kind, r=5)

# ── ghost intro screen ───────────────────────────────────────────────────
def draw_ghost_intro(s, game, t):
    s.fill(BLACK)
    pulse = 0.6 + 0.4 * abs(math.sin(t * 3))
    title_col = (
        min(255, int(GOLD[0] * pulse + 60)),
        min(255, int(GOLD[1] * pulse + 60)),
        min(255, int(GOLD[2] * pulse + 60)),
    )
    text_center(s, "CHARACTER / NICKNAME", MED, title_col, 24)

    reveal = min(4, int(t / 0.85))
    for i in range(4):
        y = 60 + i * 34
        if i < reveal:
            draw_ghost(s, 46, y + 6, i, LEFT, t, r=9)
            text_left(s, f'"{GHOST_NAMES[i]}"', SML, WHITE, 76, y)
            text_left(s, GHOST_ALIAS[i], MED, GHOSTS[i], 76, y + 12)
        elif i == reveal:
            if int(t * 8) % 2 == 0:
                draw_ghost(s, 46, y + 6, i, LEFT, t, r=9)
                text_left(s, f'"{GHOST_NAMES[i]}"', SML, WHITE, 76, y)
                text_left(s, GHOST_ALIAS[i], MED, GHOSTS[i], 76, y + 12)

    text_center(s, "ENTER to skip", SML, PAL[0x10], H - 20)
    text_center(s, f"LEVEL {game.level:03d}", SML, (180, 180, 180), H - 36)

# ── menus ────────────────────────────────────────────────────────────────
MENU_ITEMS = ("Play Game", "Help", "About", "Exit Game")

TITLE_Y1 = 24
TITLE_Y2 = 56
SUBTITLE1_Y = 88
SUBTITLE2_Y = 100
MENU_START_Y = 140
MENU_STEP_Y = 22

class Menu:
    def __init__(self):
        self.idx = 0
        self.t = 0.0
        self.state = "main"

    def key(self, k, synth):
        if self.state != "main":
            if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_BACKSPACE):
                self.state = "main"
                synth.play("menu")
            return None
        if k in (pygame.K_UP, pygame.K_w):
            self.idx = (self.idx - 1) % len(MENU_ITEMS)
            synth.play("menu")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.idx = (self.idx + 1) % len(MENU_ITEMS)
            synth.play("menu")
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            synth.play("sel")
            item = MENU_ITEMS[self.idx]
            if item == "Play Game":
                return "play"
            if item == "Help":
                self.state = "help"
            if item == "About":
                self.state = "about"
            if item == "Exit Game":
                return "quit"
        return None

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        s.fill(BLACK)
        bob = int(math.sin(self.t * 2.5) * 2)
        text_center(s, "AC's", BIG, GOLD, TITLE_Y1 + bob)
        text_center(s, "PACMAN", BIG, GOLD, TITLE_Y2 + bob)
        text_center(s, "ultra pacmane 0.1  [c] ac 1999-2026", SML, PAL[0x10], SUBTITLE1_Y)
        text_center(s, "files = off  ·  sfx = nes  ·  60 fps", SML, PAL[0x10], SUBTITLE2_Y)

        if self.state == "main":
            for i, label in enumerate(MENU_ITEMS):
                y = MENU_START_Y + i * MENU_STEP_Y
                if i == self.idx:
                    txt = MED.render("> " + label + " <", True, MENU_HI)
                else:
                    txt = MED.render(label, True, (200, 200, 200))
                s.blit(txt, (W // 2 - txt.get_width() // 2, y))
            draw_pac(s, W // 2, H - 42, RIGHT, self.t, r=8)
            text_center(s, "arrows / WASD  ·  enter select  ·  M mute", SML, PAL[0x10], H - 18)
        elif self.state == "help":
            text_center(s, "HELP", BIG, GOLD, 20)
            lines = (
                "CONTROLS",
                "Arrows or WASD ....... move",
                "M .................... mute",
                "ESC .................. back",
                "",
                "OBJECTIVE",
                "Eat all dots. Power pellets",
                "make ghosts vulnerable.",
                "200/400/800/1600 points.",
                "",
                "Reach level 256 for the",
                "famous kill screen.",
                "",
                "ENTER / ESC to return",
            )
            for i, line in enumerate(lines):
                col = WHITE if line and line[0].isupper() else (180, 180, 180)
                text_center(s, line, SML, col, 62 + i * 14)
        elif self.state == "about":
            text_center(s, "ABOUT", BIG, GOLD, 20)
            lines = (
                "AC's PACMAN",
                "ultra pacmane 0.1",
                "",
                "files = off  ·  no assets",
                "sfx   = nes  ·  2A03 beeps",
                "60 fps  ·  Famicom 2C02",
                "",
                "custom pygame engine",
                "actor graph movement",
                "arcade ghost AI",
                "kill screen at 256",
                "",
                "ac  ·  acholding",
                "",
                "ENTER / ESC to return",
            )
            for i, line in enumerate(lines):
                col = WHITE if i < 2 else (180, 180, 180)
                text_center(s, line, SML, col, 62 + i * 14)

# ── in-game render ───────────────────────────────────────────────────────
def draw_game(canvas, g):
    canvas.fill(BLACK)
    canvas.blit(g.maze.walls, (0, 0))
    for (x, y) in g.dots:
        pygame.draw.rect(canvas, DOT, (x * TILE + 3, TOP + y * TILE + 3, 2, 2))
    if int(g.timer * 4) % 2 == 0:
        for (x, y) in g.pellets:
            pygame.draw.circle(canvas, PELLET, (x * TILE + 4, TOP + y * TILE + 4), 4)
    for gh in g.ghosts:
        gx, gy = gh.pos
        flash = gh.fright and g.fright < 2 and int(g.timer * 8) % 2 == 0
        for off in (-W, 0, W):
            draw_ghost(canvas, gx * TILE + 4 + off, TOP + gy * TILE + 4, gh.i, gh.direction, g.timer,
                       fear=gh.fright, flash=flash, eyes=(gh.state == "eyes"))
    px, py = g.pac.pos
    dth = max(0.0, (g.death - 0.4) / 1.0) if g.state == "dying" else None
    for off in (-W, 0, W):
        draw_pac(canvas, px * TILE + 4 + off, TOP + py * TILE + 4, g.pac.direction, g.timer, death=dth)
    # HUD overlays the top and bottom of the maze
    draw_hud(canvas, g)
    if g.level >= Game.KILL:
        warn = SML.render("KILL SCREEN — LEVEL 256", True, RED)
        canvas.blit(warn, (W // 2 - warn.get_width() // 2, TOP + 6))
    if g.state == "ready":
        txt = SML.render("READY!", True, (255, 255, 0))
        canvas.blit(txt, (W // 2 - txt.get_width() // 2, TOP + 17 * TILE))
    elif g.state == "over":
        txt = SML.render("GAME OVER — ESC for menu", True, RED)
        canvas.blit(txt, (W // 2 - txt.get_width() // 2, TOP + 17 * TILE))

# ── main ─────────────────────────────────────────────────────────────────
def main():
    pygame.display.set_caption("AC's Pacman")
    screen = pygame.display.set_mode((W * SC, H * SC), pygame.RESIZABLE)
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    init_fonts()
    menu = Menu()
    synth = Synth()
    game = None
    mode = "menu"
    acc = 0.0
    run = True
    while run:
        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                run = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_m:
                    synth.toggle()
                    continue
                if mode == "menu":
                    action = menu.key(e.key, synth)
                    if action == "play":
                        game = Game()
                        game.synth = synth
                        synth.play("intro")
                        mode = "game"
                    elif action == "quit":
                        run = False
                else:
                    if e.key == pygame.K_ESCAPE:
                        mode = "menu"
                        menu.state = "main"
                        menu.idx = 0
                    elif game.state == "intro" and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.state = "ready"
                        game.timer = 0.0
                    else:
                        game.key(e.key)
        acc += dt
        while acc >= STEP:
            if mode == "menu":
                menu.update(STEP)
            elif mode == "game":
                game.update(STEP)
            acc -= STEP
        if mode == "menu":
            menu.draw(canvas)
        elif game.state == "intro":
            draw_ghost_intro(canvas, game, game.intro_t)
        else:
            draw_game(canvas, game)
        sw, sh = screen.get_size()
        f = max(1, min(sw // W, sh // H))
        size = (W * f, H * f)
        screen.fill(BLACK)
        screen.blit(pygame.transform.scale(canvas, size), ((sw - size[0]) // 2, (sh - size[1]) // 2))
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()