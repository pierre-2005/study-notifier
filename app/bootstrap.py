"""One database initialization path for application startup and staging rehearsals."""


def initialize_database(username='', password='', *, backup=True):
    from app.backup import pre_v3_backup, pre_consolidation_backup, pre_v34_backup, pre_v36_backup, pre_v37_backup
    from app.db import init_db
    from app.auth import init_auth_schema, ensure_bootstrap_admin
    from app.account_security import init_account_security_schema
    from app.auth_delivery import init_delivery_schema
    from app.legacy_access import init_legacy_owner
    from app.finance.db import init_finance_schema
    from app.workspace import init_workspace_schema
    from app.timers import init_timer_schema
    from app.lifeos import init_life_schema
    from app.personalize import init_layout_schema
    from app.v37 import init_v37_schema
    from app.calendar_links import init_calendar_links_schema
    from app.consolidation import consolidate_todos
    from app.phones import init_phone_schema
    from app.life_import import init_import_schema
    from app.life_files import init_file_schema
    from app.course_import import init_course_schema
    from app.study_planner import init_study_schema
    if backup:
        for create in (pre_v37_backup, pre_v3_backup, pre_consolidation_backup, pre_v34_backup, pre_v36_backup):
            create()
    init_db()
    init_auth_schema()
    init_account_security_schema()
    init_delivery_schema()
    ensure_bootstrap_admin(username, password)
    init_legacy_owner()
    init_finance_schema()
    init_workspace_schema()
    init_timer_schema()
    init_life_schema()
    init_layout_schema()
    init_phone_schema()
    init_v37_schema()
    init_calendar_links_schema()
    consolidate_todos()
    init_import_schema()
    init_file_schema()
    init_course_schema()
    init_study_schema()
