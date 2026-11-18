import sys


def main():
    while True:
        sys.stdout.write("$ ")

        command = input()

        match command.split():
            case ["exit"]:
                break
            case ["echo", *the_rest]:
                print(f"{' '.join(the_rest)}")
            case ["type", command_name]:
                valid_command_names = ["exit","echo","type"]
                if command_name in valid_command_names:
                    print(f"{command_name} is a shell builtin")
                else:
                    print(f"{command_name}: not found")
            case [first_word, *_]:
                print(f"{command}: command not found")
            case []:
                print("$ ")


if __name__ == "__main__":
    main()
