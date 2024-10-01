import subprocess

def cli():
    while True:
        command = input("~ ")
        if command == "exit":
            break
        else:
            subprocess.Popen(command, shell=True, start=True)

if __name__ == "__main__":
    cli()


    #the code works it just don't open itself in another window and i have to figure out how to do that to make it run
    #but in the meantime if i want to make update into this thing and use it it will be in the c#