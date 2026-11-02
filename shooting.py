"""Sky Lancer - pygame 종스크롤 슈팅 게임.

조작법
  방향키 / WASD : 이동
  Z / Space     : 공중 기관포 (누르고 있으면 연사)
  X / Shift     : 지상 폭탄 (조준점 위치에 떨어짐)
  P             : 일시정지
  M             : 소리 켜기 / 끄기
  Enter         : 시작 / 재시작
  Esc           : 종료

공중 적은 기관포로, 지상 목표(포대·벙커·요새)는 폭탄으로만 파괴할 수 있습니다.
P 아이템을 먹으면 한 번에 쏘는 총알이 2 → 4 → 8 → 16발로 늘어납니다.
"""
import math
import random
import sys
from array import array

import pygame

WIDTH, HEIGHT = 480, 720
FPS = 60
SCROLL_SPEED = 1.2
CHUNK_H = 240
BOMB_RANGE = 170

# 지형 색상
GRASS = (62, 110, 58)
FIELD_COLORS = [(84, 128, 64), (110, 140, 70), (96, 118, 56), (128, 120, 72)]
FOREST = (38, 92, 44)
FOREST_DARK = (26, 64, 32)
WATER = (52, 104, 160)
SAND = (180, 168, 120)
ROAD = (92, 88, 84)
ROAD_LINE = (200, 196, 160)

WHITE = (255, 255, 255)
YELLOW = (255, 230, 90)
RED = (240, 70, 70)
ORANGE = (255, 150, 50)
PURPLE = (170, 90, 230)
GREY = (120, 124, 132)
DARK_GREY = (70, 72, 80)
FIRE_COLORS = [(255, 240, 160), (255, 190, 60), (255, 120, 40), (200, 60, 30)]

POWER_LEVELS = (2, 4, 8, 16)  # 파워 단계별 한 번에 쏘는 총알 수


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------- 사운드
class SoundFX:
    """효과음 파일 없이 파형을 직접 합성해서 만든다. 오디오 장치가 없으면 조용히 꺼진다."""

    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(16)
            self.build()
            self.enabled = True
        except (pygame.error, TypeError):
            self.sounds = {}

    def synth(self, f0, f1, dur, vol, wave="square", smooth=0.0):
        """f0 → f1 Hz로 미끄러지는 소리를 감쇠 포락선과 함께 만든다."""
        n = int(self.rate * dur)
        out = array("h")
        phase = prev = 0.0
        for i in range(n):
            t = i / n
            phase += (f0 + (f1 - f0) * t) / self.rate
            if wave == "noise":
                s = random.uniform(-1, 1)
                prev = s = prev * smooth + s * (1 - smooth)  # 간단한 저역 통과 → 낮은 굉음
                s *= 1 + smooth * 2
            elif wave == "square":
                s = 1.0 if phase % 1 < 0.5 else -1.0
            elif wave == "triangle":
                s = 4 * abs(phase % 1 - 0.5) - 1
            else:
                s = math.sin(phase * math.tau)
            env = min(1.0, i / 40) * (1 - t) ** 2
            v = max(-32767, min(32767, int(s * env * vol * 32767)))
            out.extend([v] * self.channels)
        return out

    def make(self, *parts):
        buf = array("h")
        for part in parts:
            buf.extend(part)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def build(self):
        s = self.synth
        self.sounds = {
            "shot": self.make(s(900, 420, 0.06, 0.10)),
            "eshot": self.make(s(760, 520, 0.05, 0.06, "sine")),
            "bomb": self.make(s(1300, 350, 0.35, 0.18, "triangle")),
            "hit": self.make(s(320, 200, 0.04, 0.12)),
            "explode": self.make(s(0, 0, 0.35, 0.45, "noise", 0.55)),
            "big_explode": self.make(s(0, 0, 1.2, 0.7, "noise", 0.85)),
            "die": self.make(s(0, 0, 0.5, 0.6, "noise", 0.75), s(500, 60, 0.6, 0.3)),
            "powerup": self.make(*(s(f, f, 0.07, 0.25) for f in (523, 659, 784, 1047, 1319))),
            "gameover": self.make(*(s(f, f * 0.98, 0.22, 0.25, "triangle") for f in (392, 330, 262, 196))),
        }

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        if self.sounds:
            self.enabled = not self.enabled


# ---------------------------------------------------------------- 배경
class Background:
    """랜덤 지형 조각을 이어 붙여 아래로 흐르는 배경."""

    def __init__(self):
        self.chunks = []
        y = HEIGHT - CHUNK_H
        while y > -CHUNK_H:
            self.chunks.append([self.make_chunk(), y])
            y -= CHUNK_H

    def make_chunk(self):
        s = pygame.Surface((WIDTH, CHUNK_H))
        s.fill(GRASS)
        for _ in range(random.randint(2, 4)):
            w, h = random.randint(60, 160), random.randint(40, 100)
            x, y = random.randint(-20, WIDTH - 40), random.randint(0, CHUNK_H - h)
            pygame.draw.rect(s, random.choice(FIELD_COLORS), (x, y, w, h))
        if random.random() < 0.35:
            w, h = random.randint(80, 180), random.randint(50, 110)
            x, y = random.randint(0, WIDTH - w), random.randint(10, CHUNK_H - h - 10)
            pygame.draw.ellipse(s, SAND, (x - 6, y - 6, w + 12, h + 12))
            pygame.draw.ellipse(s, WATER, (x, y, w, h))
        if random.random() < 0.4:
            y = random.randint(20, CHUNK_H - 20)
            pygame.draw.rect(s, ROAD, (0, y - 8, WIDTH, 16))
            for x in range(0, WIDTH, 40):
                pygame.draw.rect(s, ROAD_LINE, (x, y - 1, 20, 2))
        for _ in range(random.randint(10, 25)):
            x, y = random.randint(0, WIDTH), random.randint(12, CHUNK_H - 12)
            r = random.randint(6, 12)
            pygame.draw.circle(s, FOREST_DARK, (x, y), r)
            pygame.draw.circle(s, FOREST, (x - 2, y - 2), r - 3)
        return s

    def update(self):
        for chunk in self.chunks:
            chunk[1] += SCROLL_SPEED
        self.chunks = [c for c in self.chunks if c[1] < HEIGHT]
        top = min(c[1] for c in self.chunks)
        while top > 0:
            top -= CHUNK_H
            self.chunks.append([self.make_chunk(), top])

    def draw(self, surf):
        for image, y in self.chunks:
            surf.blit(image, (0, round(y)))


# ---------------------------------------------------------------- 이펙트
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, drift=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.drift = drift

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        self.x += self.vx
        self.y += self.vy + self.drift
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= 1

    def draw(self, surf):
        r = max(1, int(self.size * self.life / self.max_life))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


class Popup:
    def __init__(self, x, y, text, font):
        self.x, self.y = x, y
        self.image = font.render(text, True, WHITE)
        self.life = 45

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        self.y -= 0.8
        self.life -= 1

    def draw(self, surf):
        surf.blit(self.image, self.image.get_rect(center=(int(self.x), int(self.y))))


# ---------------------------------------------------------------- 플레이어 & 무기
class Player:
    radius = 5  # 실제 피격 판정은 기체보다 작게
    speed = 4.5

    def __init__(self):
        self.dead_timer = 0
        self.power = 0  # POWER_LEVELS 인덱스
        self.reset()

    def reset(self):
        self.x, self.y = WIDTH / 2, HEIGHT - 110
        self.invuln = 150
        self.shot_cd = 0
        self.tick = 0

    @property
    def active(self):
        return self.dead_timer == 0

    @property
    def target(self):
        return self.x, self.y - BOMB_RANGE

    def update(self, keys):
        self.tick += 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.shot_cd > 0:
            self.shot_cd -= 1
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx, dy = dx * 0.7071, dy * 0.7071
        self.x = max(16, min(WIDTH - 16, self.x + dx * self.speed))
        self.y = max(BOMB_RANGE + 40, min(HEIGHT - 30, self.y + dy * self.speed))

    def draw(self, surf):
        if self.invuln and (self.invuln // 4) % 2:
            return
        x, y = int(self.x), int(self.y)
        flame = 6 + (self.tick % 6)
        pygame.draw.polygon(surf, ORANGE, [(x - 3, y + 13), (x + 3, y + 13), (x, y + 13 + flame)])
        body = [(x, y - 18), (x + 6, y - 4), (x + 17, y + 9), (x + 6, y + 8), (x + 4, y + 14),
                (x - 4, y + 14), (x - 6, y + 8), (x - 17, y + 9), (x - 6, y - 4)]
        pygame.draw.polygon(surf, (215, 225, 245), body)
        pygame.draw.polygon(surf, (90, 110, 160), body, 2)
        pygame.draw.circle(surf, (80, 200, 255), (x, y - 3), 3)


class Shot:
    def __init__(self, x, y, vx=0.0, vy=-11.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -20 or not -20 < self.x < WIDTH + 20:
            self.alive = False

    def draw(self, surf):
        pygame.draw.rect(surf, YELLOW, (int(self.x) - 1, int(self.y) - 6, 3, 12))


class Bomb:
    """플레이어 위치에서 조준점까지 포물선처럼 떨어지는 폭탄."""
    FLIGHT = 32

    def __init__(self, x, y):
        self.sx, self.sy = x, y
        self.tx, self.ty = x, y - BOMB_RANGE
        self.t = 0
        self.alive = True
        self.landed = False

    @property
    def pos(self):
        p = self.t / self.FLIGHT
        return self.sx + (self.tx - self.sx) * p, self.sy + (self.ty - self.sy) * p

    def update(self):
        self.t += 1
        self.ty += SCROLL_SPEED  # 목표 지점은 지면과 함께 흐른다
        if self.t >= self.FLIGHT:
            self.alive = False
            self.landed = True

    def draw(self, surf):
        x, y = self.pos
        r = max(2, int(6 - 4 * self.t / self.FLIGHT))
        pygame.draw.circle(surf, (40, 40, 40), (int(x), int(y)), r + 1)
        pygame.draw.circle(surf, (230, 230, 230), (int(x), int(y)), r)


class Item:
    """파괴된 적이 떨어뜨리는 파워업 캡슐."""
    radius = 12
    label = None  # Game에서 글꼴이 준비되면 채운다

    def __init__(self, x, y):
        self.x, self.base_x, self.y = x, x, y
        self.t = 0
        self.alive = True

    def update(self):
        self.t += 1
        self.y += 1.6
        self.x = self.base_x + math.sin(self.t * 0.08) * 18
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        glow = 160 + int(95 * abs(math.sin(self.t * 0.15)))
        pygame.draw.circle(surf, (40, glow // 2, glow), (x, y), self.radius + 2)
        pygame.draw.circle(surf, (200, 240, 255), (x, y), self.radius - 2)
        if self.label:
            surf.blit(self.label, self.label.get_rect(center=(x, y + 1)))


class EnemyBullet:
    radius = 4

    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 90, 160), (int(self.x), int(self.y)), self.radius + 1)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 2)


# ---------------------------------------------------------------- 적
class Enemy:
    radius = 10
    max_hp = 1
    score = 100

    def __init__(self, x, y, game):
        self.x, self.y = x, y
        self.game = game
        self.hp = self.max_hp
        self.alive = True
        self.flash = 0

    def hit(self, dmg):
        """피해를 입히고, 파괴되었으면 True를 돌려준다."""
        self.hp -= dmg
        self.flash = 4
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def color(self, base):
        return WHITE if self.flash else base

    def check_offscreen(self, margin=60):
        if self.y > HEIGHT + margin or self.y < -260 or self.x < -margin or self.x > WIDTH + margin:
            self.alive = False


# --- 공중 적 (기관포로 격추)
class Dart(Enemy):
    """빠르게 내려오며 플레이어 쪽으로 방향을 트는 돌격기."""
    radius = 11
    score = 150

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.vx = 0.0
        self.vy = 3.6 + 0.2 * min(game.level, 6)

    def update(self):
        p = self.game.player
        if self.y < p.y - 140:
            self.vx += 0.1 if p.x > self.x else -0.1
            self.vx = max(-2.2, min(2.2, self.vx))
        self.x += self.vx
        self.y += self.vy
        self.check_offscreen()

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(surf, self.color(RED), [(x, y + 13), (x + 11, y - 9), (x, y - 3), (x - 11, y - 9)])
        pygame.draw.circle(surf, (255, 210, 210), (x, y), 3)


class Weaver(Enemy):
    """좌우로 흔들리며 내려오면서 가끔 사격하는 적."""
    radius = 12
    max_hp = 2
    score = 200

    def __init__(self, x, y, game, phase):
        super().__init__(x, y, game)
        self.base_x = x
        self.t = phase

    def update(self):
        self.t += 0.05
        self.y += 2.2
        self.x = self.base_x + math.sin(self.t) * 70
        if 0 < self.y < HEIGHT * 0.6 and random.random() < 0.006 * self.game.level:
            self.game.fire_at(self.x, self.y)
        self.check_offscreen(120)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(surf, self.color(ORANGE), [(x, y - 12), (x + 13, y), (x, y + 12), (x - 13, y)])
        pygame.draw.polygon(surf, self.color((140, 70, 20)), [(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)])


class Saucer(Enemy):
    """내려와 잠시 머물며 확산탄을 쏘고 떠나는 중형기."""
    radius = 18
    max_hp = 8
    score = 600

    def __init__(self, x, game):
        super().__init__(x, -30, game)
        self.stop_y = random.randint(100, 220)
        self.state = "enter"
        self.timer = 0

    def update(self):
        if self.state == "enter":
            self.y += (self.stop_y - self.y) * 0.04 + 0.5
            if self.y >= self.stop_y:
                self.state = "hover"
        elif self.state == "hover":
            self.timer += 1
            self.x += math.sin(self.timer * 0.03) * 1.2
            if self.timer % 50 == 25:
                self.game.fire_at(self.x, self.y, spread=(-0.25, 0, 0.25))
            if self.timer > 200:
                self.state = "leave"
        else:
            self.y -= 2.5
        self.check_offscreen()

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.ellipse(surf, self.color(PURPLE), (x - 20, y - 8, 40, 16))
        pygame.draw.ellipse(surf, self.color((220, 180, 255)), (x - 9, y - 13, 18, 14))
        for i in range(4):
            a = self.timer * 0.1 + i * math.pi / 2
            pygame.draw.circle(surf, YELLOW, (x + int(math.cos(a) * 14), y + int(math.sin(a) * 4)), 2)


# --- 지상 목표 (폭탄으로 파괴, 지면과 함께 스크롤)
class Turret(Enemy):
    radius = 14
    score = 300

    def __init__(self, x, y, game, parent=None, ox=0, oy=0):
        super().__init__(x, y, game)
        self.parent, self.ox, self.oy = parent, ox, oy
        self.cooldown = random.randint(60, 120)
        self.angle = math.pi / 2

    def update(self):
        if self.parent:
            if not self.parent.alive:
                self.alive = False
                return
            self.x, self.y = self.parent.x + self.ox, self.parent.y + self.oy
        else:
            self.y += SCROLL_SPEED
        p = self.game.player
        self.angle = math.atan2(p.y - self.y, p.x - self.x)
        self.cooldown -= 1
        if self.cooldown <= 0 and 0 < self.y < p.y - 80 and p.active:
            self.game.fire_at(self.x, self.y)
            self.cooldown = random.randint(max(40, 110 - self.game.level * 8), 160)
        if not self.parent:
            self.check_offscreen()

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surf, self.color(DARK_GREY), (x, y), 14)
        pygame.draw.circle(surf, self.color(GREY), (x, y), 9)
        ex = x + int(math.cos(self.angle) * 15)
        ey = y + int(math.sin(self.angle) * 15)
        pygame.draw.line(surf, (40, 40, 44), (x, y), (ex, ey), 4)


class Bunker(Enemy):
    radius = 14
    score = 200

    def update(self):
        self.y += SCROLL_SPEED
        self.check_offscreen()

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, self.color((120, 96, 70)), (x - 14, y - 14, 28, 28))
        pygame.draw.rect(surf, self.color((80, 62, 44)), (x - 8, y - 8, 16, 16))
        pygame.draw.rect(surf, (40, 30, 20), (x - 14, y - 14, 28, 28), 2)


class Fortress(Enemy):
    """주기적으로 등장하는 거대 지상 요새. 중앙 코어를 폭탄으로 파괴해야 한다."""
    radius = 30
    max_hp = 10
    score = 3000

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self.pulse = 0

    def update(self):
        self.y += SCROLL_SPEED
        self.pulse += 1
        if 40 < self.y < HEIGHT * 0.6 and self.pulse % 110 == 0:
            self.game.fire_ring(self.x, self.y, 10, 2.6)
        self.check_offscreen(120)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pts = [(x + math.cos(math.pi / 8 + i * math.pi / 4) * 78,
                y + math.sin(math.pi / 8 + i * math.pi / 4) * 78) for i in range(8)]
        pygame.draw.polygon(surf, (60, 62, 70), pts)
        pygame.draw.polygon(surf, (30, 30, 36), pts, 4)
        pygame.draw.circle(surf, (90, 92, 100), (x, y), 44)
        pygame.draw.circle(surf, (40, 40, 46), (x, y), 44, 3)
        glow = 150 + int(80 * math.sin(self.pulse * 0.12))
        pygame.draw.circle(surf, self.color((glow, 40, 40)), (x, y), 22)
        pygame.draw.circle(surf, self.color((255, 200, 160)), (x, y), 8)
        # 남은 체력 표시
        w = int(60 * self.hp / self.max_hp)
        pygame.draw.rect(surf, (30, 30, 30), (x - 30, y + 52, 60, 5))
        pygame.draw.rect(surf, RED, (x - 30, y + 52, w, 5))


# ---------------------------------------------------------------- 게임
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sky Lancer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)
        self.big_font = pygame.font.Font(None, 72)
        Item.label = pygame.font.Font(None, 24).render("P", True, (20, 30, 90))
        self.sfx = SoundFX()
        self.hiscore = 0
        self.state = "title"
        self.paused = False
        self.reset()

    def reset(self):
        self.bg = Background()
        self.player = Player()
        self.shots, self.bombs, self.ebullets, self.items = [], [], [], []
        self.air, self.ground = [], []
        self.particles, self.popups, self.craters = [], [], []
        self.score = 0
        self.lives = 3
        self.frame = 0
        self.next_fortress = 2700
        self.paused = False

    @property
    def level(self):
        return 1 + self.frame // 1800

    # --- 적 탄환
    def bullet_speed(self):
        return 3 + 0.3 * min(self.level, 8)

    def fire_at(self, x, y, spread=(0,)):
        p = self.player
        if not p.active:
            return
        sp = self.bullet_speed()
        base = math.atan2(p.y - y, p.x - x)
        for s in spread:
            a = base + s
            self.ebullets.append(EnemyBullet(x, y, math.cos(a) * sp, math.sin(a) * sp))
        self.sfx.play("eshot")

    def fire_ring(self, x, y, n, sp):
        self.sfx.play("eshot")
        offset = random.random() * math.tau
        for i in range(n):
            a = offset + math.tau * i / n
            self.ebullets.append(EnemyBullet(x, y, math.cos(a) * sp, math.sin(a) * sp))

    # --- 이펙트
    def explosion(self, x, y, big=False, ground=False):
        n = 40 if big else 14
        power = 6 if big else 3.5
        drift = SCROLL_SPEED if ground else 0
        for _ in range(n):
            a = random.random() * math.tau
            s = random.random() * power
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s,
                                           random.randint(20, 45), random.choice(FIRE_COLORS),
                                           random.randint(3, 8 if big else 5), drift))

    def add_score(self, points, x, y):
        self.score += points
        self.popups.append(Popup(x, y, str(points), self.small_font))

    # --- 플레이어 사격 & 파워업
    def fire_volley(self):
        p = self.player
        n = POWER_LEVELS[p.power]
        if n <= 4:
            # 2발 / 4발: 나란히 직진
            for i in range(n):
                self.shots.append(Shot(p.x + (i - (n - 1) / 2) * 8, p.y - 10))
        else:
            # 8발 / 16발: 부채꼴로 퍼짐
            spread = 0.55 if n == 8 else 1.0
            for i in range(n):
                a = -spread / 2 + spread * i / (n - 1)
                self.shots.append(Shot(p.x + math.sin(a) * 14, p.y - 10, math.sin(a) * 11, -math.cos(a) * 11))
        p.shot_cd = 7
        self.sfx.play("shot")

    def maybe_drop_item(self, e):
        chance = {Saucer: 1.0, Fortress: 1.0, Bunker: 0.15, Weaver: 0.08, Dart: 0.04}.get(type(e), 0)
        if random.random() < chance:
            self.items.append(Item(e.x, e.y))

    def collect_item(self, item):
        item.alive = False
        p = self.player
        if p.power < len(POWER_LEVELS) - 1:
            p.power += 1
            self.popups.append(Popup(p.x, p.y - 30, f"SHOT x{POWER_LEVELS[p.power]}", self.font))
        else:
            self.add_score(1000, p.x, p.y - 30)  # 최대 단계에서는 보너스 점수
        self.sfx.play("powerup")

    # --- 생성
    def spawn(self):
        lvl = self.level
        fortress_active = any(isinstance(g, Fortress) for g in self.ground)
        if self.frame >= self.next_fortress and not fortress_active:
            self.spawn_fortress()
            self.next_fortress = self.frame + 3600
            fortress_active = True

        air_interval = max(30, 90 - lvl * 8) * (2 if fortress_active else 1)
        if self.frame % air_interval == 0:
            self.spawn_air_wave()

        ground_interval = max(50, 120 - lvl * 8)
        if not fortress_active and self.frame % ground_interval == 0:
            x = random.randint(30, WIDTH - 30)
            if random.random() < 0.6:
                self.ground.append(Turret(x, -30, self))
            else:
                for i in range(random.randint(1, 3)):
                    bx = x + i * 36
                    if bx < WIDTH - 20:
                        self.ground.append(Bunker(bx, -30, self))

    def spawn_air_wave(self):
        kind = random.choices(["dart", "weaver", "saucer"], weights=[5, 4, 1 + self.level // 2])[0]
        if kind == "dart":
            x = random.randint(40, WIDTH - 40)
            for i in range(3):
                self.air.append(Dart(x, -20 - i * 50, self))
        elif kind == "weaver":
            x = random.randint(90, WIDTH - 90)
            for i in range(4):
                self.air.append(Weaver(x, -20 - i * 45, self, i * 0.6))
        else:
            for _ in range(1 if self.level < 3 else 2):
                self.air.append(Saucer(random.randint(60, WIDTH - 60), self))

    def spawn_fortress(self):
        fort = Fortress(WIDTH / 2, -100, self)
        self.ground.append(fort)  # 포대보다 먼저 갱신되도록 먼저 추가
        for ox, oy in [(-50, -50), (50, -50), (-50, 50), (50, 50)]:
            t = Turret(fort.x + ox, fort.y + oy, self, fort, ox, oy)
            t.hp = 2
            self.ground.append(t)

    # --- 충돌 처리
    def bomb_explode(self, x, y):
        self.explosion(x, y, ground=True)
        self.sfx.play("explode")
        self.craters.append([x, y, 10])
        for g in self.ground:
            if g.alive and dist(g.x, g.y, x, y) < g.radius + 20 and g.hit(1):
                self.destroy_ground(g)

    def destroy_ground(self, g):
        is_fort = isinstance(g, Fortress)
        self.add_score(g.score, g.x, g.y)
        self.explosion(g.x, g.y, big=is_fort, ground=True)
        self.craters.append([g.x, g.y, 34 if is_fort else 14])
        self.maybe_drop_item(g)
        if is_fort:
            self.sfx.play("big_explode")
            for t in self.ground:
                if getattr(t, "parent", None) is g and t.alive:
                    t.alive = False
                    self.add_score(t.score, t.x, t.y)
                    self.explosion(t.x, t.y, ground=True)
            self.ebullets.clear()

    def player_hit(self):
        p = self.player
        self.explosion(p.x, p.y, big=True)
        self.lives -= 1
        p.dead_timer = 90
        p.power = max(0, p.power - 1)  # 격추되면 파워 한 단계 하락
        self.ebullets.clear()
        self.bombs.clear()
        self.sfx.play("die")

    def handle_collisions(self):
        for s in self.shots:
            for e in self.air:
                if e.alive and s.alive and dist(s.x, s.y, e.x, e.y) < e.radius + 4:
                    s.alive = False
                    if e.hit(1):
                        big = isinstance(e, Saucer)
                        self.add_score(e.score, e.x, e.y)
                        self.explosion(e.x, e.y, big=big)
                        self.sfx.play("big_explode" if big else "explode")
                        self.maybe_drop_item(e)
                    else:
                        self.sfx.play("hit")

        p = self.player
        if not p.active:
            return
        for item in self.items:
            if item.alive and dist(item.x, item.y, p.x, p.y) < item.radius + 14:
                self.collect_item(item)
        if p.invuln:
            return
        for b in self.ebullets:
            if dist(b.x, b.y, p.x, p.y) < b.radius + p.radius:
                self.player_hit()
                return
        for e in self.air:
            if e.alive and dist(e.x, e.y, p.x, p.y) < e.radius + p.radius:
                e.alive = False
                self.explosion(e.x, e.y)
                self.player_hit()
                return

    # --- 갱신
    def update(self):
        self.frame += 1
        keys = pygame.key.get_pressed()
        p = self.player

        self.bg.update()
        for c in self.craters:
            c[1] += SCROLL_SPEED
        self.craters = [c for c in self.craters if c[1] < HEIGHT + 40]

        if p.active:
            p.update(keys)
            if (keys[pygame.K_z] or keys[pygame.K_SPACE]) and p.shot_cd == 0:
                self.fire_volley()
            if (keys[pygame.K_x] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and not self.bombs:
                self.bombs.append(Bomb(p.x, p.y))
                self.sfx.play("bomb")
        else:
            p.dead_timer -= 1
            if p.dead_timer == 0:
                if self.lives > 0:
                    p.reset()
                else:
                    self.hiscore = max(self.hiscore, self.score)
                    self.state = "gameover"
                    self.sfx.play("gameover")

        self.spawn()

        for b in self.bombs:
            b.update()
            if b.landed:
                self.bomb_explode(b.tx, b.ty)
        for group in (self.shots, self.ebullets, self.ground, self.air, self.items, self.particles, self.popups):
            for obj in group:
                obj.update()
        for e in self.air + self.ground:
            if e.flash:
                e.flash -= 1

        self.handle_collisions()

        self.shots = [o for o in self.shots if o.alive]
        self.bombs = [o for o in self.bombs if o.alive]
        self.ebullets = [o for o in self.ebullets if o.alive]
        self.air = [o for o in self.air if o.alive]
        self.ground = [o for o in self.ground if o.alive]
        self.items = [o for o in self.items if o.alive]
        self.particles = [o for o in self.particles if o.alive]
        self.popups = [o for o in self.popups if o.alive]

    # --- 그리기
    def draw_crosshair(self, surf):
        tx, ty = self.player.target
        locked = any(dist(g.x, g.y, tx, ty) < g.radius + 20 for g in self.ground)
        color = RED if locked else (230, 230, 230)
        x, y = int(tx), int(ty)
        pygame.draw.circle(surf, color, (x, y), 12, 2)
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            pygame.draw.line(surf, color, (x + dx * 6, y + dy * 6), (x + dx * 17, y + dy * 17), 2)

    def draw_hud(self, surf):
        surf.blit(self.font.render(f"SCORE {self.score}", True, WHITE), (10, 10))
        hi = self.font.render(f"HI {max(self.hiscore, self.score)}", True, YELLOW)
        surf.blit(hi, hi.get_rect(midtop=(WIDTH // 2 + 40, 10)))
        surf.blit(self.small_font.render(f"LEVEL {self.level}", True, WHITE), (10, 36))
        power = self.small_font.render(f"SHOT x{POWER_LEVELS[self.player.power]}", True, (120, 210, 255))
        surf.blit(power, (10, 56))
        if not self.sfx.enabled:
            surf.blit(self.small_font.render("MUTE", True, GREY), (WIDTH - 50, 40))
        for i in range(self.lives):
            x, y = WIDTH - 20 - i * 22, 22
            pygame.draw.polygon(surf, (215, 225, 245), [(x, y - 9), (x + 8, y + 6), (x - 8, y + 6)])

    def draw_center_text(self, surf, lines):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 20, 140))
        surf.blit(shade, (0, 0))
        y = HEIGHT // 2 - 30 * len(lines)
        for text, font, color in lines:
            img = font.render(text, True, color)
            surf.blit(img, img.get_rect(center=(WIDTH // 2, y)))
            y += font.get_height() + 12

    def draw(self):
        surf = self.screen
        self.bg.draw(surf)
        for x, y, r in self.craters:
            pygame.draw.circle(surf, (50, 44, 36), (int(x), int(y)), r)
            pygame.draw.circle(surf, (34, 30, 26), (int(x), int(y)), max(2, r - 5))
        for g in self.ground:
            g.draw(surf)

        if self.state == "play":
            if self.player.active:
                self.draw_crosshair(surf)
            for group in (self.bombs, self.items, self.shots, self.air):
                for obj in group:
                    obj.draw(surf)
            if self.player.active:
                self.player.draw(surf)
            for group in (self.ebullets, self.particles, self.popups):
                for obj in group:
                    obj.draw(surf)
            self.draw_hud(surf)
            if self.paused:
                self.draw_center_text(surf, [("PAUSED", self.big_font, WHITE),
                                             ("Press P to resume", self.font, WHITE)])
        elif self.state == "title":
            self.draw_center_text(surf, [
                ("SKY LANCER", self.big_font, YELLOW),
                ("Arrows / WASD : Move", self.font, WHITE),
                ("Z / Space : Air cannon", self.font, WHITE),
                ("X / Shift : Ground bomb", self.font, WHITE),
                ("Grab P items: 2 > 4 > 8 > 16 shots", self.font, (120, 210, 255)),
                ("P : Pause   M : Sound   Esc : Quit", self.font, WHITE),
                ("Press ENTER to start", self.font, ORANGE),
            ])
        else:
            self.draw_hud(surf)
            self.draw_center_text(surf, [
                ("GAME OVER", self.big_font, RED),
                (f"SCORE {self.score}", self.font, WHITE),
                (f"HI SCORE {self.hiscore}", self.font, YELLOW),
                ("Press ENTER to restart", self.font, ORANGE),
            ])
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if self.state in ("title", "gameover") and event.key == pygame.K_RETURN:
                        self.reset()
                        self.state = "play"
                    elif self.state == "play" and event.key == pygame.K_p:
                        self.paused = not self.paused
                    if event.key == pygame.K_m:
                        self.sfx.toggle()

            if self.state == "play":
                if not self.paused:
                    self.update()
            else:
                self.bg.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
