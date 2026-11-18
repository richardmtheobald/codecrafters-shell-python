import sys
import os

def main():
    while True:
        sys.stdout.write("$ ")

        command = input()

        valid_command_names = ["exit","echo","type"]

        match command.split():
            case ["exit"]:
                break
            case ["echo", *the_rest]:
                print(f"{' '.join(the_rest)}")
            case ["type", command_name]:
                paths = os.environ.get("PATH","").split(os.pathsep)
                if command_name in valid_command_names:
                    print(f"{command_name} is a shell builtin")
                else:
                    for path in paths:
                        full_path = os.path.join(path,command_name)
                        if os.path.isfile(full_path) and os.access(full_path,os.X_OK):
                            print(f"{command_name} is {full_path}")
                            break
                    else:
                        print(f"{command_name}: not found")
            case [first_word, *_]:
                print(f"{command}: command not found")
            case []:
                pass


if __name__ == "__main__":
    main()
