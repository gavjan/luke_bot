import subprocess
import os
from cons import ADMIN_IDS as allowed_users

terminals = {}
passwords = {}


def handle(command, user):
    if user in terminals:
        return (True, handle_command(command, user))
    if user not in allowed_users or not command.strip().startswith("bash") and not command.strip().startswith("sudo bash"):
        return (False, None)
    
    if "sudo" in command:
        password = command.strip().replace("sudo bash", "")
        if not password:
            return True, "usage: sudo bash [password]\n"
        passwords[user] = password.strip()
    
    bash_process = subprocess.Popen(
        "bash",
        preexec_fn=os.setsid,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    terminals[user] = bash_process
    
    return True, "$ "


def exit_terminal(user):
    terminals[user].stdin.close()
    terminals[user].wait()
    del terminals[user]
    if user in passwords:
        del passwords[user]


def handle_command(command, user):
    if command.strip() == "clear":
        return "$ "
    if command.strip() == "exit":
        exit_terminal(user)
        return "exit\n"
    

    if command.startswith("sudo "):
        if user not in passwords:
            exit_terminal(user)
            return 'Can\'t use sudo, start terminal with: "sudo bash [password]"\nexit\n'
        command = command.replace("sudo ",f"echo {passwords[user]} | sudo -S ")

    terminals[user].stdin.write(command.strip() + "\n")
    terminals[user].stdin.write("echo >&2 mtvvcbe && echo mtvvcb\n")
    terminals[user].stdin.write("echo >&2 mtvvcbe\n")
    terminals[user].stdin.flush()

    buffer = ""
    while True:
        line = terminals[user].stdout.readline()
        if line.strip() == "mtvvcb":
            break
        else:
            buffer+=line
    err_buffer = ""
    while True:
        line = terminals[user].stderr.readline()
        if line.strip() == "mtvvcbe":
            break
        else:
            err_buffer+=line
    
    return buffer + err_buffer + '$ '
        

if __name__ == "__main__":
    while True:
        ret, lines = handle(input(), 213341816324489217)
        if ret:
            print(lines, end="")
