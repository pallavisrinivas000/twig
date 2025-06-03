import argparse
import configparser
from datetime import datetime
import os
import grp, pwd
from fnmatch import fnmatch
import hashlib
import re
import sys
import zlib

def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Yet another twig clone")
    commands = parser.add_subparsers(dest='command')

    # Add the 'init' command
    # This command initializes a new twig repository
    # It creates a .twig directory with the necessary structure
    init_command = commands.add_parser('init', help='Initialize a new twig repository')

    # Add the cat-file command
    # This command is used to display the contents of an object in the repository
    cat_file_command = commands.add_parser('cat-file', help='Display the contents of an object in the repository')

    cat_file_command.add_argument('object', help='The object to display (e.g., a commit, tree, or blob)')

    # Add the 'hash-object' command
    # This command computes the object ID for a file and stores it in the repository
    hash_object_command = commands.add_parser('hash-object', help='Compute the object ID for a file and store it in the repository')
    hash_object_command.add_argument("-w", "--write", action="store_true", help='to write the object to the repository')
    hash_object_command.add_argument("path", nargs='?', help='The path to the file to hash')

    # Add the 'write-tree' command
    write_tree_command = commands.add_parser('write-tree', help='Create a tree object from the working directory')


    # Add the 'hash-object' command
    args = parser.parse_args(argv)
    if args.command == 'init':
        repo_create(os.getcwd())
    elif args.command == 'cat-file':
        obj = object_read(args.object)
        sys.stdout.buffer.write(obj["data"])
    elif args.command == 'hash-object':
        if args.path:
            with open(args.path, 'rb') as f:
                data = f.read()
        else:
            data = sys.stdin.buffer.read()
        obj = object_hash(data, "blob", write=args.write)
        print(obj)
    elif args.command == 'write-tree':
        print(write_tree())

def object_hash(data, fmt, write=False):
    header = f"{fmt} {len((data))}\0".encode()
    full_data = header + data

    sha = hashlib.sha1(full_data).hexdigest()

    if write:
        path = os.path.join('.twig', 'objects', sha[:2])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        full_path = os.path.join(path, sha[2:])
        if not os.path.exists(full_path):
            compressed_data = zlib.compress(full_data)
            with open(full_path, 'wb') as f:
                f.write(compressed_data)
    return sha

def object_read(sha):
    path = os.path.join('.twig', 'objects', sha[:2], sha[2:])
    with open(path, 'rb') as f:
        compressed_data = f.read()
    raw = zlib.decompress(compressed_data)

    x = raw.find(b' ')
    fmt = raw[0:x]  # e.g., b"blob"

    y = raw.find(b'\x00', x)
    size = int(raw[x+1:y])  # parse size, e.g., 12

    data = raw[y+1:]  # everything after the null byte is the file content

    # Sanity check: make sure size matches the actual length of data
    assert size == len(data), f"Malformed object {sha}: bad length"

    return {
        "type": fmt.decode(),   # e.g., "blob"
        "size": size,           # e.g., 12
        "data": data            # raw content, e.g., b"hello world\n"
    }

    


def repo_create(path):
    git_dir = os.path.join(path, '.twig')

    if os.path.exists(git_dir):
        print(f"Error: {git_dir} already exists.")
        return
    
    os.makedirs(os.path.join(git_dir, 'objects'))
    os.makedirs(os.path.join(git_dir, 'refs'))

    with open(os.path.join(git_dir, "HEAD"), 'w') as f:
        f.write("ref: refs/heads/master\n")
    print(f"Initialized empty twig repository in {git_dir}")


def write_tree(directory="."):
    entries = []

    for entry in sorted(os.listdir(directory)):
        print(entry)
        if entry == ".twig":
            continue

        full_path = os.path.join(directory, entry)

        if os.path.isdir(full_path):
            sha = write_tree(full_path)
            mode = "40000"  # Tree mode
        else:
            with open(full_path, "rb") as f:
                data = f.read()
            sha = object_hash(data, "blob", write=True)
            mode = "100644"  # Regular file mode

        entry_line = f"{mode} {entry}".encode() + b"\x00" + bytes.fromhex(sha)
        entries.append(entry_line)

    tree_data = b"".join(entries)
    return object_hash(tree_data, "tree", write=True)



