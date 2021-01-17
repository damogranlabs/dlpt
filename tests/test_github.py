import os

import pytest


def createFileInFunc(path: str):
    folder = os.path.dirname(path)
    assert os.path.exists(folder)

    p4 = os.path.join(folder, "hello4.txt")
    with open(p4, "w+") as writer:
        writer.write("CONTENT")
    assert os.path.exists(p4)


def test_create_file(tmp_path):
    CONTENT = "content"

    d = tmp_path / "sub"
    d.mkdir()
    p = d / "hello.txt"
    p.write_text(CONTENT)

    p2 = os.path.join(d, "hello2.txt")
    with open(p2, "w+") as writer:
        writer.write(CONTENT)
    assert os.path.exists(p2)

    p3 = os.path.join(d, "dir1", "dir1")
    os.makedirs(p3)
    assert os.path.exists(p3)

    p3_2 = os.path.join(p3, "hello3.txt")
    with open(p3_2, "w+") as writer:
        writer.write(CONTENT)
    assert os.path.exists(p3_2)

    p4 = os.path.join(p3, "hello4.txt")
    createFileInFunc(p4)
