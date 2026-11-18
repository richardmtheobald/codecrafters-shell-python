import sys


def main():
    while True:
        sys.stdout.write("$ ")

        command = input()

        match command.split():
            case ["exit"]:
                break
            case ["echo", *the_rest]:
                print(f"{" ".join(items)}")
            case [first_word, *_]:
                print(f"{command}: command not found")
            case []:
                print("$ ")


if __name__ == "__main__":
    main()
