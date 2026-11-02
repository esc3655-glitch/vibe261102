import tkinter as tk


class BreakoutGame:
    WIDTH = 800
    HEIGHT = 600
    BALL_RADIUS = 9
    PADDLE_WIDTH = 110
    PADDLE_HEIGHT = 14
    BRICK_ROWS = 5
    BRICK_COLUMNS = 10
    BRICK_WIDTH = 68
    BRICK_HEIGHT = 22
    BRICK_GAP = 7

    def __init__(self, root):
        self.root = root
        self.root.title("블록깨기")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(
            root,
            width=self.WIDTH,
            height=self.HEIGHT,
            background="#111827",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.keys = set()
        self.score = 0
        self.lives = 3
        self.paused = False
        self.waiting_to_serve = False
        self.game_over = False
        self.won = False
        self.paddle_x = self.WIDTH / 2
        self.ball_x = self.WIDTH / 2
        self.ball_y = self.HEIGHT - 90
        self.ball_dx = 4.0
        self.ball_dy = -4.5
        self.bricks = {}

        self._create_scene()
        self._create_bricks()
        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.canvas.bind("<Motion>", self._move_paddle_with_mouse)
        self._draw_hud()
        self._draw_paddle()
        self._draw_ball()
        self._tick()

    def _create_scene(self):
        self.canvas.create_text(
            18,
            18,
            anchor="nw",
            text="BLOCK BREAKER",
            fill="#9ca3af",
            font=("Segoe UI", 11, "bold"),
        )
        self.canvas.create_line(
            18,
            50,
            self.WIDTH - 18,
            50,
            fill="#374151",
            width=1,
        )

    def _create_bricks(self):
        colors = ["#fb7185", "#fb923c", "#facc15", "#4ade80", "#38bdf8"]
        total_width = (
            self.BRICK_COLUMNS * self.BRICK_WIDTH
            + (self.BRICK_COLUMNS - 1) * self.BRICK_GAP
        )
        left = (self.WIDTH - total_width) / 2
        top = 88

        for row in range(self.BRICK_ROWS):
            for column in range(self.BRICK_COLUMNS):
                x1 = left + column * (self.BRICK_WIDTH + self.BRICK_GAP)
                y1 = top + row * (self.BRICK_HEIGHT + self.BRICK_GAP)
                brick_id = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x1 + self.BRICK_WIDTH,
                    y1 + self.BRICK_HEIGHT,
                    fill=colors[row],
                    outline="",
                )
                self.bricks[brick_id] = (row, column)

    def _draw_hud(self):
        self.canvas.delete("hud")
        self.canvas.create_text(
            self.WIDTH - 180,
            20,
            anchor="nw",
            text=f"점수  {self.score:04d}     목숨  {self.lives}",
            fill="#f9fafb",
            font=("Segoe UI", 12, "bold"),
            tags="hud",
        )

    def _draw_paddle(self):
        self.canvas.delete("paddle")
        half = self.PADDLE_WIDTH / 2
        self.canvas.create_rectangle(
            self.paddle_x - half,
            self.HEIGHT - 48,
            self.paddle_x + half,
            self.HEIGHT - 48 + self.PADDLE_HEIGHT,
            fill="#e5e7eb",
            outline="",
            tags="paddle",
        )

    def _draw_ball(self):
        self.canvas.delete("ball")
        radius = self.BALL_RADIUS
        self.canvas.create_oval(
            self.ball_x - radius,
            self.ball_y - radius,
            self.ball_x + radius,
            self.ball_y + radius,
            fill="#ffffff",
            outline="",
            tags="ball",
        )

    def _show_message(self, title, subtitle):
        self.canvas.delete("message")
        self.canvas.create_text(
            self.WIDTH / 2,
            self.HEIGHT / 2 - 18,
            text=title,
            fill="#ffffff",
            font=("Segoe UI", 30, "bold"),
            tags="message",
        )
        self.canvas.create_text(
            self.WIDTH / 2,
            self.HEIGHT / 2 + 25,
            text=subtitle,
            fill="#d1d5db",
            font=("Segoe UI", 13),
            tags="message",
        )

    def _key_down(self, event):
        key = event.keysym.lower()
        if key in self.keys:
            return
        self.keys.add(key)

        if key == "space":
            if self.game_over:
                self._restart()
            elif self.waiting_to_serve:
                self.waiting_to_serve = False
                self.canvas.delete("message")
            else:
                self.paused = not self.paused
                if self.paused:
                    self._show_message("일시정지", "스페이스바를 눌러 계속")
                else:
                    self.canvas.delete("message")
        elif key == "r":
            self._restart()

    def _key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def _move_paddle_with_mouse(self, event):
        self.paddle_x = self._clamp_paddle_x(event.x)

    def _clamp_paddle_x(self, x):
        half = self.PADDLE_WIDTH / 2
        return max(half + 8, min(self.WIDTH - half - 8, x))

    def _tick(self):
        if not self.paused and not self.game_over:
            self._update_paddle()
            if not self.waiting_to_serve:
                self._update_ball()
            self._draw_paddle()
            self._draw_ball()
        self.root.after(16, self._tick)

    def _update_paddle(self):
        if "left" in self.keys or "a" in self.keys:
            self.paddle_x -= 8
        if "right" in self.keys or "d" in self.keys:
            self.paddle_x += 8
        self.paddle_x = self._clamp_paddle_x(self.paddle_x)

    def _update_ball(self):
        previous_x = self.ball_x
        previous_y = self.ball_y
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        if self.ball_x - self.BALL_RADIUS <= 0:
            self.ball_x = self.BALL_RADIUS
            self.ball_dx = abs(self.ball_dx)
        elif self.ball_x + self.BALL_RADIUS >= self.WIDTH:
            self.ball_x = self.WIDTH - self.BALL_RADIUS
            self.ball_dx = -abs(self.ball_dx)

        if self.ball_y - self.BALL_RADIUS <= 58:
            self.ball_y = 58 + self.BALL_RADIUS
            self.ball_dy = abs(self.ball_dy)

        self._check_paddle_collision(previous_y)
        self._check_brick_collision(previous_x, previous_y)

        if self.ball_y - self.BALL_RADIUS > self.HEIGHT:
            self._lose_life()

    def _check_paddle_collision(self, previous_y):
        paddle_top = self.HEIGHT - 48
        paddle_half = self.PADDLE_WIDTH / 2
        ball_bottom = self.ball_y + self.BALL_RADIUS
        overlaps_paddle = (
            self.ball_x + self.BALL_RADIUS >= self.paddle_x - paddle_half
            and self.ball_x - self.BALL_RADIUS <= self.paddle_x + paddle_half
        )
        if (
            self.ball_dy > 0
            and previous_y + self.BALL_RADIUS <= paddle_top
            and ball_bottom >= paddle_top
            and overlaps_paddle
        ):
            self.ball_y = paddle_top - self.BALL_RADIUS
            self.ball_dy = -abs(self.ball_dy)
            offset = (self.ball_x - self.paddle_x) / paddle_half
            self.ball_dx = max(-6.5, min(6.5, offset * 6.5))

    def _check_brick_collision(self, previous_x, previous_y):
        ball_box = (
            self.ball_x - self.BALL_RADIUS,
            self.ball_y - self.BALL_RADIUS,
            self.ball_x + self.BALL_RADIUS,
            self.ball_y + self.BALL_RADIUS,
        )
        for brick_id in tuple(self.bricks):
            brick_box = self.canvas.coords(brick_id)
            if not brick_box:
                continue
            left, top, right, bottom = brick_box
            if not (
                ball_box[2] >= left
                and ball_box[0] <= right
                and ball_box[3] >= top
                and ball_box[1] <= bottom
            ):
                continue

            self.canvas.delete(brick_id)
            del self.bricks[brick_id]
            self.score += 10
            self._draw_hud()

            came_from_side = (
                previous_x + self.BALL_RADIUS <= left
                or previous_x - self.BALL_RADIUS >= right
            )
            if came_from_side:
                self.ball_dx *= -1
            else:
                self.ball_dy *= -1

            if not self.bricks:
                self.won = True
                self.game_over = True
                self._show_message("모든 블록을 깼어요!", "스페이스바 또는 R 키로 다시 시작")
            return

    def _lose_life(self):
        self.lives -= 1
        self._draw_hud()
        if self.lives <= 0:
            self.game_over = True
            self._show_message("게임 오버", "스페이스바 또는 R 키로 다시 시작")
            return

        self.ball_x = self.paddle_x
        self.ball_y = self.HEIGHT - 75
        self.ball_dx = 4.0
        self.ball_dy = -4.5
        self.waiting_to_serve = True
        self._show_message("공을 놓쳤어요", "스페이스바를 눌러 다시 시작")

    def _restart(self):
        for brick_id in self.bricks:
            self.canvas.delete(brick_id)
        self.bricks.clear()
        self.score = 0
        self.lives = 3
        self.paused = False
        self.waiting_to_serve = False
        self.game_over = False
        self.won = False
        self.paddle_x = self.WIDTH / 2
        self.ball_x = self.WIDTH / 2
        self.ball_y = self.HEIGHT - 90
        self.ball_dx = 4.0
        self.ball_dy = -4.5
        self.canvas.delete("message")
        self._create_bricks()
        self._draw_hud()
        self._draw_paddle()
        self._draw_ball()


def main():
    root = tk.Tk()
    BreakoutGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()