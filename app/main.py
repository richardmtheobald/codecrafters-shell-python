import sys
import os
import subprocess

def tokenize(token_string):
    tokens = []
    current_token = ""
    mid_token = False
    i = 0
    mode = "normal"
    while i < len(token_string):
        character = token_string[i]
        if mode == "single":
            if character == "'":
                mode = "normal"
            else:
                current_token += character
        elif mode == "double":
            if character == "\\" and i + 1 < len(token_string) and token_string[i + 1] in ['"', "\\", "$", "`", "\n"]:
                i += 1
                current_token += token_string[i]
            elif character == '"':
                mode = "normal"
            else:
                current_token += character
        elif mode == "normal":
            if character == "'":
                mode = "single"
                mid_token = True
            elif character == '"':
                mode = "double"
                mid_token = True
            elif character.isspace():
                if mid_token:
                    tokens.append(current_token)
                    current_token = ""
                    mid_token = False
            elif character == "\\":
                i += 1
                if i < len(token_string):
                    current_token += token_string[i]
                    mid_token = True
            else:
                current_token += character
                mid_token = True
        i += 1
    if mid_token:
        tokens.append(current_token)
    return tokens


def find_executable(exe_name):
    for path in os.environ.get("PATH","").split(os.pathsep):
        full_path = os.path.join(path,exe_name)
        if os.path.isfile(full_path) and os.access(full_path,os.X_OK):
            return full_path
    return None

def main():
    valid_command_names = ["exit","echo","type", "pwd", "cd"]
    while True:
        sys.stdout.write("$ ")

        command = input()

        match tokenize(command):
            case ["exit"]:
                break

            case ["pwd"]:
                print(os.getcwd())

            case ["cd", directory]:
                if directory.startswith('~'):
                    directory = os.environ["HOME"] + directory[1:]
                if os.path.isdir(directory):
                    os.chdir(directory)
                else:
                    print(f"cd: {directory}: No such file or directory")

            case ["echo", *the_rest]:
                print(f"{' '.join(the_rest)}")

            case ["type", command_name]:
                if command_name in valid_command_names:
                    print(f"{command_name} is a shell builtin")
                else:
                    full_path = find_executable(command_name)
                    if full_path:
                        print(f"{command_name} is {full_path}")
                    else:
                        print(f"{command_name}: not found")

            case [exe_name, *args]:
                full_path = find_executable(exe_name)
                if full_path:
                    subprocess.run([exe_name,*args],executable=full_path)
                else:
                    print(f"{exe_name}: command not found")

            case []:
                pass


if __name__ == "__main__":
    main()
