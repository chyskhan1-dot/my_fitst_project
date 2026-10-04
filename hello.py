"""Первая тестовая программа: приветствие и маленькая игра «Угадай число»."""

import random
from datetime import datetime


def greet(name: str) -> str:
    hour = datetime.now().hour
    if hour < 12:
        part = "Доброе утро"
    elif hour < 18:
        part = "Добрый день"
    else:
        part = "Добрый вечер"
    return f"{part}, {name}!"


def guess_game(low: int = 1, high: int = 10) -> None:
    secret = random.randint(low, high)
    print(f"Я загадал число от {low} до {high}. Попробуй угадать!")
    attempts = 0
    while True:
        try:
            guess = int(input("Твой вариант: "))
        except ValueError:
            print("Нужно ввести целое число.")
            continue
        attempts += 1
        if guess < secret:
            print("Больше!")
        elif guess > secret:
            print("Меньше!")
        else:
            print(f"Угадал за {attempts} попыт(ки/ок)!")
            break


if __name__ == "__main__":
    name = input("Как тебя зовут? ").strip() or "друг"
    print(greet(name))
    guess_game()
