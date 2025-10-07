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
        # verifies ctor stores the provided filename verbatim
        def it_preserves_filename_verbatim(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            db = MyDB("weird name.db")
            assert db.fname == "weird name.db"

        # verifies initialization happens only once: missing→init, existing→no init
        def it_initializes_once_then_skips_after_file_exists(mocker):
            mocker.patch("mydb.os.path.isfile", side_effect=[False, True])
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            _ = MyDB("db.db")   # should initialize []
            _ = MyDB("db.db")   # should NOT initialize again
            save_mock.assert_called_once_with([])

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
        # verifies loadStrings returns whatever payload was pickled (e.g., list of dicts)
        def it_returns_arbitrary_pickled_payloads(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "payload.db"
            payload = [{"id": 1}, {"id": 2}]
            fs_stubs.memdb[fname] = payload
            db = MyDB(fname)
            assert db.loadStrings() == payload
            assert fs_stubs.open_calls == [(fname, "rb")]

        def it_reads_using_open_and_pickle(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "in.db"
            fs_stubs.memdb[fname] = ["a", "b"]
            db = MyDB(fname)
            assert db.loadStrings() == ["a", "b"]
            assert fs_stubs.open_calls == [(fname, "rb")]
            assert fs_stubs.load_mock.call_count == 1

    def describe_saveStrings():
        # verifies saveStrings overwrites previous contents rather than appending
        def it_overwrites_previous_contents_on_subsequent_writes(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "swap.db"
            db = MyDB(fname)
            db.saveStrings(["old"])
            db.saveStrings(["new"])
            assert fs_stubs.memdb[fname] == ["new"]
            assert fs_stubs.open_calls == [(fname, "wb"), (fname, "wb")]

        # verifies saveStrings can write an empty list
        def it_handles_empty_list_write(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "empty.db"
            db = MyDB(fname)
            db.saveStrings([])
            assert fs_stubs.memdb[fname] == []
            assert fs_stubs.open_calls == [(fname, "wb")]

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
        # verifies saveString appends when the DB is empty
        def it_appends_when_db_is_empty(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            db = MyDB("combo-empty.db")
            mocker.patch.object(MyDB, "loadStrings", return_value=[])
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            db.saveString("x")
            save_mock.assert_called_once_with(["x"])

        # verifies multiple saveString calls accumulate and persist via our in-memory store
        def it_accumulates_across_multiple_calls_using_in_memory_store(fs_stubs, mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            fname = "multi.db"
            fs_stubs.memdb[fname] = []  # start "file" as empty
            db = MyDB(fname)

            # Wire MyDB.loadStrings/saveStrings to the in-memory store for this test
            def _load():
                return list(fs_stubs.memdb[fname])
            def _save(arr):
                fs_stubs.memdb[fname] = list(arr)

            mocker.patch.object(MyDB, "loadStrings", side_effect=_load)
            mocker.patch.object(MyDB, "saveStrings", side_effect=_save)

            db.saveString("x")
            db.saveString("y")

            assert fs_stubs.memdb[fname] == ["x", "y"]

        def it_loads_appends_and_saves(mocker):
            mocker.patch("mydb.os.path.isfile", return_value=True)
            db = MyDB("combo.db")
            load_mock = mocker.patch.object(MyDB, "loadStrings", return_value=["a"])
            save_mock = mocker.patch.object(MyDB, "saveStrings")
            db.saveString("b")
            load_mock.assert_called_once_with()
            save_mock.assert_called_once_with(["a", "b"])
