"""재입대 줴줴이야 실행 파일. `python main.py`로 실행한다."""

import tkinter as tk

from ui import App


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
