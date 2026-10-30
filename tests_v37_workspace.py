"""v3.7 compatibility and isolation smoke tests."""
import sqlite3
import unittest
from fastapi import HTTPException
from app.v37 import _validate_preferences, _validate_reminders, project_board, save_user_setup, read_user_setup

class WorkspaceV37Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
        CREATE TABLE users(id INTEGER PRIMARY KEY);
        INSERT INTO users(id) VALUES(1),(2);
        CREATE TABLE life_appearance(user_id INTEGER PRIMARY KEY,theme TEXT,palette TEXT,palette_style TEXT,updated_at TEXT);
        CREATE TABLE life_tasks(id INTEGER PRIMARY KEY,owner_id INTEGER,project_id INTEGER,parent_id INTEGER,
          title TEXT,status TEXT,position INTEGER,due_on TEXT,priority TEXT);
        INSERT INTO life_tasks VALUES(1,1,9,NULL,'Parent','todo',0,NULL,'high');
        INSERT INTO life_tasks VALUES(2,1,9,1,'Child','done',0,NULL,'normal');
        INSERT INTO life_tasks VALUES(3,1,9,1,'Child 2','doing',0,NULL,'normal');
        """)
        self.db.executescript("""
        CREATE TABLE v37_workspace_preferences (user_id INTEGER PRIMARY KEY, selected_modules TEXT,
          timezone TEXT,quiet_start TEXT,quiet_end TEXT,preferred_view TEXT,density TEXT,
          onboarding_completed INTEGER,updated_at TEXT);
        CREATE TABLE v37_reminder_rules (user_id INTEGER, kind TEXT,offset_minutes INTEGER,PRIMARY KEY(user_id,kind,offset_minutes));
        """)
        self.db.execute("ALTER TABLE life_tasks ADD COLUMN updated_at TEXT NOT NULL DEFAULT 'fixture-revision'")
    def tearDown(self):self.db.close()
    def test_nested_subtasks_hidden_from_top_level(self):
        b=project_board(self.db,9);self.assertEqual(len(b["columns"]["todo"]),1)
        t=b["columns"]["todo"][0];self.assertEqual(t["subtask_total"],2);self.assertEqual(t["subtask_done"],1)
        self.assertEqual(b["total"],3)
    def test_preference_owner_separation(self):
        prefs={"selected_modules":["tasks","study"],"reminders":{"task":[60,1440]},
               "theme":"dark","accent_color":"blue","onboarding_completed":True}
        save_user_setup(self.db,1,prefs);self.db.commit()
        self.assertEqual(read_user_setup(self.db,1)["reminders"]["task"],[1440,60])
        self.assertEqual(read_user_setup(self.db,2)["reminders"]["task"],[])
        self.assertFalse(read_user_setup(self.db,2)["onboarding_completed"])
    def test_duplicate_invalid_offsets_rejected(self):
        with self.assertRaises(HTTPException):_validate_reminders({"task":[60,60]})
        with self.assertRaises(HTTPException):_validate_reminders({"task":[999]})
    def test_modules_validated(self):
        with self.assertRaises(HTTPException):_validate_preferences({"selected_modules":["unknown"]})

if __name__=="__main__":unittest.main()
