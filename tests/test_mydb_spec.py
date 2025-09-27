import os, sys 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import types
import pytest
from mydb import MyDB

class _DummyFile:
    def __init__(self, name): self.name = name
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

@pytest.fixture
def fs_stubs(mocker):
    import mydb
    memdb = {}
    open_calls = []

    def fake_open(name, mode='r', *args, **kwargs):
        open_calls.append((name, mode))
        return _DummyFile(name)

    load_mock = mocker.patch("mydb.pickle.load",
                             side_effect=lambda f: memdb[f.name])
    dump_mock = mocker.patch("mydb.pickle.dump",
                             side_effect=lambda arr, f: memdb.__setitem__(f.name, list(arr)))
    mocker.patch("builtins.open", side_effect=fake_open)

    return types.SimpleNamespace(
        memdb=memdb, open_calls=open_calls,
        load_mock=load_mock, dump_mock=dump_mock
    )

def describe_MyDB():

    def describe___init__():
        def it_sets_fname_and_does_not_initialize_when_file_exists(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            db = MyDB("data.db")
            assert db.fname == "data.db"
            save_mock.assert_not_called()

        def it_initializes_new_file_with_empty_list_when_missing(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=False)
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            _ = MyDB("new.db")
            save_mock.assert_called_once_with([])

    def describe_loadStrings():
        def it_reads_using_open_and_pickle(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "in.db"
            fs_stubs.memdb[fname] = ["a", "b"]
            db = MyDB(fname)
            assert db.loadStrings() == ["a", "b"]
            assert fs_stubs.open_calls == [(fname, "rb")]
            assert fs_stubs.load_mock.call_count == 1

    def describe_saveStrings():
        def it_writes_using_open_and_pickle(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "out.db"
            db = MyDB(fname)
            db.saveStrings(["x", "y"])
            assert fs_stubs.memdb[fname] == ["x", "y"]
            assert fs_stubs.open_calls == [(fname, "wb")]
            fs_stubs.dump_mock.assert_called_once()
            arr_arg, file_arg = fs_stubs.dump_mock.call_args[0]
            assert arr_arg == ["x", "y"]
            assert getattr(file_arg, "name") == fname

    def describe_saveString():
        def it_loads_appends_and_saves(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            db = MyDB("combo.db")
            load_mock = mocker.patch.object(MyDB, "loadStrings", return_value=["a"])
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            db.saveString("b")
            load_mock.assert_called_once_with()
            save_mock.assert_called_once_with(["a", "b"])
