"""뱀 게임 (tkinter 사용 - 별도 설치 불필요)

조작법:
  방향키 / WASD : 이동
  Space         : 일시정지 / 재개
  R             : 게임 오버 후 재시작
"""

import random
import tkinter as tk

CELL = 20          # 칸 크기(픽셀)
COLS = 30          # 가로 칸 수
ROWS = 25          # 세로 칸 수
START_SPEED = 120  # 시작 속도(ms, 작을수록 빠름)
MIN_SPEED = 50     # 최고 속도

BG_COLOR = "#1e1e1e"
SNAKE_COLOR = "#4caf50"
HEAD_COLOR = "#8bc34a"
FOOD_COLOR = "#f44336"
TEXT_COLOR = "#ffffff"

DIRECTIONS = {
    "Up": (0, -1), "w": (0, -1),
    "Down": (0, 1), "s": (0, 1),
    "Left": (-1, 0), "a": (-1, 0),
    "Right": (1, 0), "d": (1, 0),
}


class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("뱀 게임")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root, width=COLS * CELL, height=ROWS * CELL,
            bg=BG_COLOR, highlightthickness=0,
        )
        self.canvas.pack()

        self.root.bind("<Key>", self.on_key)
        self.high_score = 0
        self.after_id = None
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.speed = START_SPEED
        self.paused = False
        self.game_over = False
        self.food = self.place_food()
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.tick()

    def place_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def on_key(self, event):
        key = event.keysym
        if key.lower() in ("w", "a", "s", "d"):
            key = key.lower()

        if key in DIRECTIONS and not self.game_over:
            dx, dy = DIRECTIONS[key]
            # 반대 방향으로는 바로 꺾을 수 없음
            if (dx, dy) != (-self.direction[0], -self.direction[1]):
                self.next_direction = (dx, dy)
        elif key == "space" and not self.game_over:
            self.paused = not self.paused
            self.draw()
        elif key.lower() == "r" and self.game_over:
            self.reset()

    def tick(self):
        if not self.paused and not self.game_over:
            self.step()
        self.draw()
        if not self.game_over:
            self.after_id = self.root.after(self.speed, self.tick)

    def step(self):
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])

        # 벽 충돌
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.end_game()
            return

        ate = new_head == self.food
        body = self.snake if ate else self.snake[:-1]
        # 자기 몸 충돌
        if new_head in body:
            self.end_game()
            return

        self.snake.insert(0, new_head)
        if ate:
            self.score += 10
            self.speed = max(MIN_SPEED, self.speed - 3)
            self.food = self.place_food()
            if self.food is None:  # 화면을 꽉 채우면 승리
                self.end_game()
        else:
            self.snake.pop()

    def end_game(self):
        self.game_over = True
        self.high_score = max(self.high_score, self.score)

    def draw(self):
        c = self.canvas
        c.delete("all")

        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 3, fy * CELL + 3,
                          (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
                          fill=FOOD_COLOR, outline="")

        for i, (x, y) in enumerate(self.snake):
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill=HEAD_COLOR if i == 0 else SNAKE_COLOR,
                               outline="")

        c.create_text(8, 8, anchor="nw", fill=TEXT_COLOR,
                      font=("Malgun Gothic", 12, "bold"),
                      text=f"점수: {self.score}   최고: {self.high_score}")

        w, h = COLS * CELL, ROWS * CELL
        if self.game_over:
            msg = "승리!" if self.food is None else "게임 오버"
            c.create_text(w / 2, h / 2 - 20, fill=TEXT_COLOR,
                          font=("Malgun Gothic", 28, "bold"), text=msg)
            c.create_text(w / 2, h / 2 + 20, fill=TEXT_COLOR,
                          font=("Malgun Gothic", 14),
                          text=f"점수: {self.score}  |  R 키로 재시작")
        elif self.paused:
            c.create_text(w / 2, h / 2, fill=TEXT_COLOR,
                          font=("Malgun Gothic", 24, "bold"),
                          text="일시정지")


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
