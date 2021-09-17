import sys

from grapetree.module import MSTrees

if len(sys.argv) == 1:
    print("Type 'grapetree --help' to learn how to run this command. " \
        + "Note that with this CLI utility, all arguments must be in the long form.")
    sys.exit()

arg_list = sys.argv[1:]
mapping = dict()

while True:
    try: 
        mapping[arg_list.pop()[2:]] = arg_list.pop()
    except IndexError:
        break

print(mapping)
print(MSTrees.backend(**mapping))