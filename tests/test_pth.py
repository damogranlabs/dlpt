import os
import pathlib
import stat
import time
from unittest import mock
from unittest.mock import call

import pytest

import dlpt

this_file = str(pathlib.Path(__file__).resolve())
this_dir = os.path.dirname(this_file)

url_path = "https://xkcd.com/"
unc_path = r"\\root\rootFolder\dir1\folder2\folder3\folder4"


@pytest.mark.parametrize("is_file", [False, True])
def test_change_dir(is_file):
    cwd = os.getcwd()
    if is_file:
        path = __file__
        new_cwd = os.path.dirname(path)
    else:
        path = os.path.dirname(__file__)
        new_cwd = path

    with mock.patch("dlpt.pth.check"):
        with mock.patch("dlpt.pth.resolve") as resolve_func:
            resolve_func.return_value = path

            with mock.patch("os.chdir") as os_chdir_func:

                with dlpt.pth.ChangeDir(path):
                    pass  # do whatever here

    assert os_chdir_func.call_count == 2
    assert os_chdir_func.call_args_list == [call(new_cwd), call(cwd)]
    assert cwd == os.getcwd()


def test_validate_path():
    assert dlpt.pth._validate_path(__file__) == __file__

    with pytest.raises(Exception):
        dlpt.pth._validate_path(None)

    with pytest.raises(Exception):
        dlpt.pth._validate_path(" ")


@pytest.mark.parametrize("valid_path", [False, True])
def test_check(valid_path):
    if valid_path:
        path = __file__
    else:
        path = __file__ + "asd"

    with mock.patch("dlpt.pth._validate_path") as check_func:
        check_func.return_value = path

        with mock.patch("os.path.exists") as exists_func:
            exists_func.return_value = valid_path

        if valid_path:
            assert dlpt.pth.check(path) == path
        else:
            with pytest.raises(Exception):
                dlpt.pth.check(path)


def test_resolve():
    path = dlpt.pth.resolve(__file__)
    assert isinstance(path, str)
    assert path.lower() == __file__.lower()
    assert os.path.samefile(path, __file__)


@pytest.mark.parametrize("succes", [False, True])
def test_set_w_permissions(tmp_path, succes):
    file_path = os.path.join(tmp_path, "testFile.txt")

    with mock.patch("os.chmod") as mod_func:
        with mock.patch("os.access") as access_func:
            if succes:
                access_func.return_value = True
                dlpt.pth._set_w_permissions(file_path)
            else:
                access_func.return_value = False

                with pytest.raises(Exception):
                    dlpt.pth._set_w_permissions(file_path)

            assert mod_func.call_count == 1
            assert mod_func.call_args[0][0] == file_path
            assert mod_func.call_args[0][1] == stat.S_IWRITE

            assert access_func.call_count == 1
            assert access_func.call_args[0][0] == file_path
            assert access_func.call_args[0][1] == os.W_OK


def test_copy_file_checks():
    with pytest.raises(Exception):
        dlpt.pth.copy_file(__file__, __file__)  # non-existing path (dst_dir_path == __file__)

    with mock.patch("dlpt.pth.check"):
        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.copy_file(__file__, __file__)  # folder, not file


@pytest.mark.parametrize("dst_file_name", [None, "newFileName.txt"])
def test_copy_file(tmp_path, dst_file_name):
    FILE_NAME = "testFile.txt"
    src_file_path = os.path.join(tmp_path, FILE_NAME)
    dst_dir_path = os.path.join(tmp_path, "dst")
    if dst_file_name:
        dst_file_path = os.path.join(tmp_path, "dst", dst_file_name)
    else:
        dst_file_path = os.path.join(tmp_path, "dst", FILE_NAME)

    with mock.patch("dlpt.pth.check") as check_func:
        check_func.return_value = src_file_path
        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.return_value = True

            with mock.patch("dlpt.pth.get_name") as name_func:
                if dst_file_name is None:
                    name_func.return_value = FILE_NAME

                with mock.patch("dlpt.pth.create_dir") as create_func:
                    with mock.patch("dlpt.pth.remove_file") as rm_file_func:
                        with mock.patch("shutil.copyfile") as copy_func:

                            path = dlpt.pth.copy_file(src_file_path, dst_dir_path, dst_file_name)
                            assert path == dst_file_path

                            if dst_file_name is None:
                                assert name_func.call_count == 1
                                assert name_func.call_args[0][0] == src_file_path
                            else:
                                assert name_func.call_count == 0

                            assert create_func.call_count == 1
                            assert create_func.call_args[0][0] == dst_dir_path

                            assert rm_file_func.call_count == 1
                            assert rm_file_func.call_args[0][0] == dst_file_path

                            assert copy_func.call_count == 1
                            assert copy_func.call_args[0][0] == src_file_path
                            assert copy_func.call_args[0][1] == dst_file_path


def test_copy_dir_checks():
    with pytest.raises(Exception):
        dlpt.pth.copy_file(__file__, __file__)  # non-existing path

    with mock.patch("dlpt.pth.check"):
        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.copy_dir(__file__, __file__)  # file, not folder


def test_copy_dir(tmp_path):
    dst_dir_path = os.path.join(tmp_path, "dst")

    with mock.patch("dlpt.pth.check") as check_func:
        check_func.return_value = tmp_path
        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.return_value = True

            with mock.patch("dlpt.pth._validate_path"):

                with mock.patch("dlpt.pth.remove_dir_tree") as rm_dir_func:
                    with mock.patch("shutil.copytree") as copy_func:

                        path = dlpt.pth.copy_dir(tmp_path, dst_dir_path)
                        assert path == dst_dir_path

                        assert rm_dir_func.call_count == 1
                        assert rm_dir_func.call_args[0][0] == dst_dir_path

                        assert copy_func.call_count == 1
                        assert copy_func.call_args[0][0] == tmp_path
                        assert copy_func.call_args[0][1] == dst_dir_path


def test_remove_file_checks(tmp_path):
    with pytest.raises(Exception):
        dlpt.pth.remove_file(tmp_path)  # non-existing path

    with mock.patch("os.path.isfile") as is_file_func:
        is_file_func.return_value = False

        with pytest.raises(ValueError):
            dlpt.pth.remove_file(tmp_path)  # folder, not file


@pytest.mark.parametrize("force_write_permissions", [False, True])
def test_remove_file(force_write_permissions):
    with mock.patch("os.path.exists") as is_file_func:
        is_file_func.return_value = True
        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.return_value = True

            with mock.patch("dlpt.pth._set_w_permissions") as fwp_func:
                with mock.patch("os.unlink") as rm_func:

                    dlpt.pth.remove_file(__file__, force_write_permissions)

                    assert rm_func.call_count == 1
                    assert rm_func.call_args[0][0] == __file__

                    if force_write_permissions:
                        assert fwp_func.call_count == 1
                        assert fwp_func.call_args[0][0] == __file__
                    else:
                        assert fwp_func.call_count == 0


@pytest.mark.parametrize("success", [False, True])
def test_remove_file_retry(success):
    with mock.patch("os.path.exists") as is_file_func:
        is_file_func.return_value = True
        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.return_value = True

            with mock.patch("dlpt.pth._set_w_permissions"):
                with mock.patch("os.unlink") as rm_func:
                    rm_func.side_effect = [Exception("1"), Exception("2"), None]

                    if success:
                        dlpt.pth.remove_file(__file__)

                        assert rm_func.call_count == 3
                        assert rm_func.call_args_list == [call(__file__)] * 3
                    else:
                        with pytest.raises(Exception):
                            dlpt.pth.remove_file(__file__, retry=1)


def test_remove_dir_tree_checks():
    with mock.patch("os.path.exists") as exists_func:
        exists_func.return_value = True
        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.remove_dir_tree(__file__)


@pytest.mark.parametrize("force_write_permissions", [False, True])
def test_remove_dir_tree(force_write_permissions):
    with mock.patch("os.path.exists") as exists_func:
        exists_func.return_value = True
        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.return_value = True

            with mock.patch("shutil.rmtree") as rm_func:

                dlpt.pth.remove_dir_tree(__file__)

                assert rm_func.call_count == 1
                assert rm_func.call_args[0][0] == __file__
                if force_write_permissions:
                    # keyword args
                    kwArgs = {"ignore_errors": False, "onerror": dlpt.pth._on_remove_dir_err}
                    assert rm_func.call_args[1] == kwArgs


@pytest.mark.parametrize("success, force_write_permissions", [(False, True), (True, True), (True, False)])
def test_remove_dir_tree_retry(success, force_write_permissions):
    with mock.patch("os.path.exists") as exists_func:
        exists_func.return_value = True
        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.return_value = True
            with mock.patch("time.sleep") as sleep_func:

                with mock.patch("shutil.rmtree") as rm_func:
                    if success:
                        rm_func.side_effect = [Exception("1"), Exception("2"), None]
                        dlpt.pth.remove_dir_tree(__file__, force_write_permissions)
                        assert rm_func.call_count == 3
                        assert sleep_func.call_count == 2

                    else:
                        rm_func.side_effect = [Exception("1"), Exception("2"), None]
                        with pytest.raises(Exception):
                            dlpt.pth.remove_dir_tree(__file__, force_write_permissions, retry=1)

                        assert rm_func.call_count == 1
                        assert sleep_func.call_count == 0


def test_clean_dir(tmp_path):
    items = ["file1", "dir1", "file2", "file3"]
    is_file = [True, False, True, True]

    with mock.patch("os.listdir") as list_func:
        list_func.return_value = items
        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.side_effect = is_file

            with mock.patch("dlpt.pth.remove_file") as rm_file_func:
                with mock.patch("dlpt.pth.remove_dir_tree") as rm_dir_func:

                    dlpt.pth.clean_dir(tmp_path)

                    assert rm_file_func.call_count == 3
                    assert rm_dir_func.call_count == 1


def test_create_dir(tmp_path):
    with mock.patch("os.makedirs") as mk_func:
        dlpt.pth.create_dir(tmp_path)
        assert mk_func.call_count == 1
        assert os.path.samefile(mk_func.call_args[0][0], tmp_path)


@pytest.mark.parametrize("is_existing", [False, True])
def test_create_clean_dir(tmp_path, is_existing):

    with mock.patch("os.path.exists") as exists_func:
        exists_func.return_value = is_existing

        with mock.patch("dlpt.pth.clean_dir") as clean_func:
            with mock.patch("dlpt.pth.create_dir") as create_func:

                dlpt.pth.create_clean_dir(tmp_path)

                if is_existing:
                    assert clean_func.call_count == 1
                    assert create_func.call_count == 0
                else:
                    assert clean_func.call_count == 0
                    assert create_func.call_count == 1


def test_remove_old_items(tmp_path):
    DAY_IN_SEC = 24 * 60 * 60
    current_time = time.time()

    items = ["now.txt", "dayOld.txt", "dayOldFolder", "sameAsDaysArgument.txt", "oldFile.txt", "oldFolder"]
    mod_time = [
        current_time - 0,
        current_time - 1 * DAY_IN_SEC,
        current_time - 1 * DAY_IN_SEC,
        current_time - 3 * DAY_IN_SEC,
        current_time - 10 * DAY_IN_SEC,
        current_time - 10 * DAY_IN_SEC,
    ]
    is_file = [
        # True, True, False,  # not called
        # True,               # not called
        True,
        False,
    ]

    with mock.patch("time.time") as time_func:
        time_func.return_value = current_time
        with mock.patch("os.listdir") as list_func:
            list_func.return_value = items
            with mock.patch("os.path.getmtime") as m_time_func:
                m_time_func.side_effect = mod_time
                with mock.patch("os.path.isfile") as is_file_func:
                    is_file_func.side_effect = is_file

                    with mock.patch("dlpt.pth.remove_file") as rm_file_func:
                        with mock.patch("dlpt.pth.remove_dir_tree") as rm_dir_func:

                            removed_items = dlpt.pth.remove_old_items(tmp_path, 3)
                            assert len(removed_items) == 2
                            assert os.path.join(tmp_path, items[-1]) in removed_items
                            assert os.path.join(tmp_path, items[-2]) in removed_items

                            assert rm_file_func.call_count == 1
                            assert rm_dir_func.call_count == 1


def test_with_fw_slashes():
    pth = r"My/path\with\\slashes"
    assert dlpt.pth.with_fw_slashes(pth) == r"My/path/with//slashes"


def test_with_double_bw_slashes():
    pth = r"My/path\with\\slashes"
    assert dlpt.pth.with_double_bw_slashes(pth) == r"My/path\\with\\\\slashes"


def test_get_name():
    pth = r"some/path/with/file_name.txt"
    assert dlpt.pth.get_name(pth) == "file_name.txt"
    assert dlpt.pth.get_name(pth, False) == "file_name"

    pth = r"some/path/with/file_name"
    assert dlpt.pth.get_name(pth) == "file_name"
    assert dlpt.pth.get_name(pth, False) == "file_name"


def test_get_ext():
    pth = r"some/path/with/file_name.txt"
    assert dlpt.pth.get_ext(pth) == ".txt"

    pth = r"some/path/with/file_name"
    assert dlpt.pth.get_ext(pth) == ""


def test_get_files_in_dir(tmp_path):
    items = ["file1.txt", "dir1", "file3.png", "folder2", "file4.jpg"]
    is_file = [True, False, True, False, True]

    with mock.patch("os.listdir") as list_func:
        list_func.return_value = items

        with mock.patch("os.path.isfile") as is_file_func:
            is_file_func.side_effect = is_file
            files = dlpt.pth.get_files_in_dir(tmp_path)
            assert len(files) == 3
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[2]) in files
            assert os.path.join(tmp_path, items[4]) in files

            is_file_func.side_effect = is_file
            files = dlpt.pth.get_files_in_dir(tmp_path, [".txt"])
            assert len(files) == 1

            is_file_func.side_effect = is_file
            assert os.path.join(tmp_path, items[0]) in files
            files = dlpt.pth.get_files_in_dir(tmp_path, include_ext=[".txt", ".jpg"])
            assert len(files) == 2
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[4]) in files

            is_file_func.side_effect = is_file
            files = dlpt.pth.get_files_in_dir(tmp_path, exclude_ext=[".png"])
            assert len(files) == 2
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[4]) in files

            with pytest.raises(Exception):
                dlpt.pth.get_files_in_dir(tmp_path, [".jpg"], [".png"])


def test_get_files_in_dir_tree(tmp_path):
    txt1 = dlpt.pth.copy_file(__file__, tmp_path, "file1.txt")
    png1 = dlpt.pth.copy_file(__file__, tmp_path, "file2.png")
    jpg1 = dlpt.pth.copy_file(__file__, tmp_path, "file3.jpg")
    dir1 = os.path.join(tmp_path, "dir1")
    dlpt.pth.create_dir(dir1)
    txt2 = dlpt.pth.copy_file(__file__, dir1, "file11.txt")
    png2 = dlpt.pth.copy_file(__file__, dir1, "file12.png")
    subdir = os.path.join(dir1, "subfolder")
    txt3 = dlpt.pth.copy_file(__file__, subdir, "file21.txt")
    jpg3 = dlpt.pth.copy_file(__file__, subdir, "file22.jpg")

    files = dlpt.pth.get_files_in_dir_tree(tmp_path)
    assert len(files) == 7

    files = dlpt.pth.get_files_in_dir_tree(tmp_path, include_ext=[".txt"])
    assert len(files) == 3
    assert txt1 in files
    assert txt2 in files
    assert txt3 in files

    files = dlpt.pth.get_files_in_dir_tree(tmp_path, exclude_ext=[".txt"])
    assert len(files) == 4
    assert png1 in files
    assert jpg1 in files
    assert png2 in files
    assert jpg3 in files

    with pytest.raises(Exception):
        dlpt.pth.get_files_in_dir_tree(tmp_path, [".jpg"], [".png"])


def test_get_dirs_in_dir(tmp_path):
    items = ["file1.txt", "folder", "file3.png", "Folder", "file4.jpg"]
    is_dir = [False, True, False, True, False]

    with mock.patch("os.listdir") as list_func:
        list_func.return_value = items

        with mock.patch("os.path.isdir") as is_dir_func:
            is_dir_func.side_effect = is_dir
            files = dlpt.pth.get_dirs_in_dir(tmp_path)
            assert len(files) == 2
            assert os.path.join(tmp_path, items[1]) in files
            assert os.path.join(tmp_path, items[3]) in files

            is_dir_func.side_effect = is_dir
            files = dlpt.pth.get_dirs_in_dir(tmp_path, "older")
            assert len(files) == 2

            is_dir_func.side_effect = is_dir
            files = dlpt.pth.get_dirs_in_dir(tmp_path, "folder", True)  # compare lower case
            assert len(files) == 2
            assert os.path.join(tmp_path, items[1]) in files
            assert os.path.join(tmp_path, items[3]) in files

            is_dir_func.side_effect = is_dir
            files = dlpt.pth.get_dirs_in_dir(tmp_path, "folder", False)
            assert len(files) == 1
            assert os.path.join(tmp_path, items[1]) in files

            is_dir_func.side_effect = is_dir
            files = dlpt.pth.get_dirs_in_dir(tmp_path, "asd")
            assert len(files) == 0
