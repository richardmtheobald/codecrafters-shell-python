import sys
import os
import subprocess
import readline

valid_command_names = ["exit","echo","type", "pwd", "cd"]
parser_commands = {
    ">": ("stdout", "w"),
    "1>": ("stdout", "w"),
    "2>": ("stderr", "w"),
    ">>": ("stdout", "a"),
    "1>>": ("stdout", "a"),
    "2>>": ("stderr", "a")
}

def builtin_auto_completer(text, state):
    matches = [name + " " for name in valid_command_names if name.startswith(text)]
    if state < len(matches):
        return matches[state]
    return None

def parse(tokens):
    args = []
    redirects = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in parser_commands and i+1 < len(tokens):
            channel, mode = parser_commands[token]
            redirects[channel] = {
                "filename":tokens[i+1],
                "mode":mode
            }
            i += 2
        else:
            args.append(token)
            i+=1
    return args, redirects

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
    readline.set_completer(builtin_auto_completer)
    readline.parse_and_bind("tab: complete")
    while True:
        command = input("$ ")

        args, redirects = parse(tokenize(command))

        streams = {}
        for out_type in ["stdout", "stderr"]:
            if out_type in redirects:
                streams[out_type] = open(redirects[out_type]["filename"], redirects[out_type]["mode"])
            else:
                streams[out_type] = getattr(sys, out_type)

        match args:
            case ["exit"]:
                break

            case ["pwd"]:
                print(os.getcwd(), file=streams["stdout"])

            case ["cd", directory]:
                if directory.startswith('~'):
                    directory = os.environ["HOME"] + directory[1:]
                if os.path.isdir(directory):
                    os.chdir(directory)
                else:
                    print(f"cd: {directory}: No such file or directory", file=streams["stderr"])

            case ["echo", *the_rest]:
                print(f"{' '.join(the_rest)}", file=streams["stdout"])

            case ["type", command_name]:
                if command_name in valid_command_names:
                    print(f"{command_name} is a shell builtin", file=streams["stdout"])
                else:
                    full_path = find_executable(command_name)
                    if full_path:
                        print(f"{command_name} is {full_path}", file=streams["stdout"])
                    else:
                        print(f"{command_name}: not found", file=streams["stdout"])

            case [exe_name, *args]:
                full_path = find_executable(exe_name)
                if full_path:
                    subprocess.run([exe_name,*args],executable=full_path,
                                   stdout=streams["stdout"], stderr=streams["stderr"])
                else:
                    print(f"{exe_name}: command not found", file=streams["stderr"])

            case []:
                pass

        for out_type, stream in streams.items():
            if stream is not getattr(sys, out_type):
                stream.close()


if __name__ == "__main__":
    main()
