import sys
import os
import subprocess
import readline

valid_command_names = ["exit","echo","type", "pwd", "cd", "complete", "jobs", "history", "declare"]
parser_commands = {
    ">": ("stdout", "w"),
    "1>": ("stdout", "w"),
    "2>": ("stderr", "w"),
    ">>": ("stdout", "a"),
    "1>>": ("stdout", "a"),
    "2>>": ("stderr", "a")
}
completion_scripts = {}
jobs = []
history = []
history_appended_count = 0
shell_variables = {}

def is_valid_name(name):
    if name == "" or name[0].isdigit():
        return False
    return all(c.isascii() and (c.isalnum() or c == "_") for c in name)

def lookup_variable(name):
    if name in shell_variables:
        return shell_variables[name]
    return os.environ.get(name,"")

def read_variable(token_string, i):
    if i+1 < len(token_string) and token_string[i+1] == "{":
        end = token_string.find("}", i+2)
        if end == -1:
            return None
        return lookup_variable(token_string[i + 2:end]), end

    j = i+1
    while j < len(token_string) and token_string[j].isascii() and (token_string[j].isalnum() or token_string[j] == "_"):
        j += 1
    name = token_string[i + 1:j]
    if not is_valid_name(name):
        return None
    return lookup_variable(name), j-1

def add_to_history(line):
    history.append(line)
    readline.add_history(line)

def load_history(path):
    if not os.path.isfile(path):
        return
    with open(path) as file:
        for line in file:
            line = line.rstrip("\n")
            if line:
                add_to_history(line)

def save_history(path, lines, mode):
    with open(path, mode) as file:
        for line in lines:
            file.write(line + "\n")

def auto_completer(text, state):
    line = readline.get_line_buffer()

    if line[:readline.get_begidx()].strip() == "":
        matches = [name for name in valid_command_names if name.startswith(text)]
        for name in find_executables_starting_with(text):
            if name not in matches:
                matches.append(name)
        matches = [name + " " for name in matches]
    else:
        words = line[:readline.get_begidx()].split()
        command_name = words[0]
        if command_name in completion_scripts:
            result = subprocess.run(
                [completion_scripts[command_name], command_name, text, words[-1]],
                capture_output=True,
                text=True,
                env={**os.environ, "COMP_LINE": line, "COMP_POINT": str(readline.get_endidx())}
            )
            matches = [option + " " for option in result.stdout.splitlines() if option]
        else:
            matches = find_files_starting_with(text)

    matches.sort()

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
            elif character == "$":
                result = read_variable(token_string, i)
                if result is None:
                    current_token += character
                else:
                    value, i = result
                    current_token += value
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
            elif character == "$":
                result = read_variable(token_string, i)
                if result is None:
                    current_token += character
                    mid_token = True
                else:
                    value, i = result
                    current_token += value
                    if value:
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

def find_executables_starting_with(text):
    found = []
    for path in os.environ.get("PATH","").split(os.pathsep):
        if not os.path.isdir(path):
            continue
        for exe_name in os.listdir(path):
            full_path = os.path.join(path,exe_name)
            if exe_name.startswith(text) and os.path.isfile(full_path) and os.access(full_path,os.X_OK):
                found.append(exe_name)
    return found

def find_files_starting_with(text):
    slash_location = text.rfind("/")
    folder_path = text[:slash_location + 1]
    file_name = text[slash_location+1:]
    search_dir = folder_path or "."
    if search_dir.startswith('~'):
        search_dir = os.environ["HOME"] + search_dir[1:]

    if not os.path.isdir(search_dir):
        return []

    matches = []
    for name in os.listdir(search_dir):
        if not name.startswith(file_name):
            continue
        if name.startswith(".") and not file_name.startswith("."):
            continue
        if os.path.isdir(os.path.join(search_dir, name)):
            matches.append(folder_path + name + "/")
        else:
            matches.append(folder_path + name + " ")
    return matches

def report_jobs(jobs, include_running, out):
    still_running = []
    for index, job in enumerate(jobs):
        if index == len(jobs) - 1:
            marker = "+"
        elif index == len(jobs) - 2:
            marker = "-"
        else:
            marker = " "

        if job["process"].poll() is None:
            still_running.append(job)
            if include_running:
                print(f"[{job['number']}]{marker}  {'Running':<24}{job['command']} &", file=out)
        else:
            print(f"[{job['number']}]{marker}  {'Done':<24}{job['command']}", file=out)
    jobs[:] = still_running

def run_pipeline(segments):
    processes = []
    previous_output_stream = None

    for index, segment in enumerate(segments):
        args, _ = parse(segment)
        is_last_segment = index == len(segments) - 1

        if args[0] in valid_command_names:
            if is_last_segment:
                run_builtin(args, sys.stdout, sys.stderr)
                next_output = None
            else:
                read_end, write_end = os.pipe()
                with os.fdopen(write_end, "w") as pipe_writer:
                    run_builtin(args, pipe_writer, sys.stderr)
                next_output = os.fdopen(read_end)
        else:
            process = subprocess.Popen(
                args,
                stdin=previous_output_stream,
                stdout=None if is_last_segment else subprocess.PIPE
            )
            processes.append(process)
            next_output = process.stdout

        if previous_output_stream is not None:
            previous_output_stream.close()

        previous_output_stream = next_output

    for process in processes:
        process.wait()

def run_builtin(args, out, err):
    global history_appended_count
    match args:
        case ["pwd"]:
            print(os.getcwd(), file=out)

        case ["cd", directory]:
            if directory.startswith('~'):
                directory = os.environ["HOME"] + directory[1:]
            if os.path.isdir(directory):
                os.chdir(directory)
            else:
                print(f"cd: {directory}: No such file or directory", file=err)

        case ["echo", *the_rest]:
            print(' '.join(the_rest), file=out)

        case ["type", command_name]:
            if command_name in valid_command_names:
                print(f"{command_name} is a shell builtin", file=out)
            else:
                full_path = find_executable(command_name)
                if full_path:
                    print(f"{command_name} is {full_path}", file=out)
                else:
                    print(f"{command_name}: not found", file=out)

        case ["complete", "-C", script, command_name]:
            completion_scripts[command_name] = script

        case ["complete", "-p", command_name]:
            if command_name in completion_scripts:
                print(f"complete -C '{completion_scripts[command_name]}' {command_name}", file=out)
            else:
                print(f"complete: {command_name}: no completion specification", file=err)

        case ["complete", "-r", command_name]:
            completion_scripts.pop(command_name, None)

        case ["complete", *_]:
            pass

        case ["jobs"]:
            report_jobs(jobs, True, out)

        case ["history"]:
            for number, line in enumerate(history, start=1):
                print(f"{number:>5} {line}", file=out)

        case ["history", "-r", path]:
            load_history(path)

        case ["history", "-w", path]:
            save_history(path, history, "w")

        case ["history", "-a", path]:
            save_history(path, history[history_appended_count:], "a")
            history_appended_count = len(history)

        case ["history", count]:
            start = max(len(history) - int(count), 0)
            for index in range(start, len(history)):
                print(f"{index + 1:>5} {history[index]}", file=out)

        case ["declare", "-p", name]:
            if name in shell_variables:
                print(f'declare -- {name}="{shell_variables[name]}"', file=out)
            else:
                print(f"declare: {name}: not found", file=err)

        case ["declare", *assignments]:
            for assignment in assignments:
                name, _, value = assignment.partition("=")
                if not is_valid_name(name):
                    print(f"declare: `{assignment}': not a valid identifier", file=err)
                    continue
                shell_variables[name] = value

def split_pipeline(tokens):
    segments = [[]]
    for token in tokens:
        if token == "|":
            segments.append([])
        else:
            segments[-1].append(token)
    return segments

def main():
    readline.set_completer(auto_completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")
    if hasattr(readline, "set_auto_history"):
        readline.set_auto_history(False)

    global history_appended_count
    histfile = os.environ.get("HISTFILE")
    if histfile:
        load_history(histfile)
    history_appended_count = len(history)

    while True:
        report_jobs(jobs, False, sys.stdout)
        command = input("$ ")

        if command.strip():
            add_to_history(command)

        tokens = tokenize(command)
        pipe_segments = split_pipeline(tokens)
        if len(pipe_segments) > 1:
            run_pipeline(pipe_segments)
            continue

        args, redirects = parse(tokens)

        #for processes that are run in the background, we need to strip out the & but let the executor know it's a background process
        background = False
        if args and args[-1] == "&":
            background = True
            args = args[:-1]

        streams = {}
        for out_type in ["stdout", "stderr"]:
            if out_type in redirects:
                streams[out_type] = open(redirects[out_type]["filename"], redirects[out_type]["mode"])
            else:
                streams[out_type] = getattr(sys, out_type)

        match args:
            case ["exit"]:
                break

            case [builtin_name, *_] if builtin_name in valid_command_names:
                run_builtin(args, streams["stdout"], streams["stderr"])

            case [exe_name, *args]:
                full_path = find_executable(exe_name)
                if full_path:
                    if background:
                        process = subprocess.Popen([exe_name, *args],
                            executable=full_path,
                            stdout=streams["stdout"],
                            stderr=streams["stderr"]
                        )
                        number = max([job["number"] for job in jobs], default=0)+1
                        jobs.append({
                            "number": number,
                            "process": process,
                            "command": " ".join([exe_name, *args])
                        })
                        print(f"[{number}] {process.pid}", file=streams["stdout"])
                    else:
                        subprocess.run(
                            [exe_name,*args],
                            executable=full_path,
                            stdout=streams["stdout"],
                            stderr=streams["stderr"]
                        )
                else:
                    print(f"{exe_name}: command not found", file=streams["stderr"])

            case []:
                pass

        for out_type, stream in streams.items():
            if stream is not getattr(sys, out_type):
                stream.close()

    if histfile:
        save_history(histfile, history, "w")


if __name__ == "__main__":
    main()
